"""Forced Aligner — refines Whisper word timestamps using acoustic analysis.

Two modes:
    1. Forced (wav2vec2) — CTC posterior span refinement, sub-50ms
       (feature-frame) precision.
       Requires: uv sync --extra gpu (torch + transformers)
    2. VAD Refinement — adaptive-threshold silence detection with
       short-silence merging and vectorized per-frame RMS energy,
       sub-150ms precision. Always available, no extra dependencies.

Audio handling:
    WAV files are read directly with soundfile; other containers
    (mp4, mp3, ...) are extracted to a temporary 16 kHz mono WAV via
    ffmpeg. Non-16 kHz audio is resampled with linear interpolation.

Usage:
    from engine.alignment.aligner import Aligner

    # VAD refinement mode (default, always works)
    aligner = Aligner(audio_path="speech.wav")
    result = aligner.align(asr_words=words)

    # Forced alignment mode (if wav2vec2 available)
    aligner = Aligner(audio_path="speech.wav", mode="forced")
    result = aligner.align(asr_words=words)
"""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import soundfile as sf

from engine.alignment.models import AlignedWord, AlignmentResult
from engine.asr.models import Word
from engine.core.ffmpeg import run_ffmpeg

logger = logging.getLogger("caption_with_intention")

DEFAULT_MODE = "vad_refinement"
DEFAULT_PHONEME_MODEL = "facebook/wav2vec2-large-960h-lv60-self"
DEFAULT_SAMPLE_RATE = 16000
DEFAULT_MIN_SILENCE_DURATION = 0.15  # 150ms silence = word boundary
DEFAULT_HOP_LENGTH = 10  # ms between analysis frames

# VAD threshold: fraction of the 95th-percentile frame energy that a
# frame must exceed to count as speech. Relative to loud frames, so
# both quiet and loud recordings get sensible boundaries.
SPEECH_THRESHOLD_RATIO = 0.1
ABSOLUTE_ENERGY_FLOOR = 1e-4


def ctc_word_boundaries(
    labels: np.ndarray,
    blank_index: int,
    start_sec: float,
    end_sec: float,
) -> tuple[float, float]:
    """Refine a word window from CTC argmax posteriors (pure numpy).

    Args:
        labels: Per-feature-frame token ids (argmax of CTC logits).
        blank_index: Id of the CTC blank token.
        start_sec / end_sec: The word window in seconds.

    Returns:
        (refined_start, refined_end). Consecutive duplicate labels are
        collapsed (CTC property); the first and last non-blank frames
        mark where the word's acoustic content actually lies. Falls
        back to the input window when nothing but blanks is present.
    """
    window = end_sec - start_sec
    if window <= 0 or labels.size == 0:
        return start_sec, end_sec

    frames_per_sec = labels.size / window
    # Positions where the label changes (first frame included)
    change = np.concatenate(([True], labels[1:] != labels[:-1]))
    collapsed = np.flatnonzero(change)
    active = collapsed[labels[collapsed] != blank_index]
    if active.size == 0:
        return start_sec, end_sec

    lo = start_sec + active[0] / frames_per_sec
    hi = start_sec + (active[-1] + 1) / frames_per_sec
    lo = max(start_sec, min(lo, end_sec))
    hi = min(end_sec, max(hi, lo))
    if hi <= lo:
        return start_sec, end_sec
    return lo, hi


class Aligner:
    """Refines ASR word timestamps using acoustic analysis.

    Args:
        audio_path: Path to audio file (WAV preferred, 16kHz mono).
        mode: "forced" for wav2vec2 alignment, "vad_refinement" for
            silence-based boundary detection.
        min_silence_duration: Minimum silence (seconds) to detect a boundary.
        hop_length: Analysis hop length in ms.
        sample_rate: Target sample rate for analysis.
    """

    def __init__(
        self,
        audio_path: str,
        mode: str = DEFAULT_MODE,
        min_silence_duration: float = DEFAULT_MIN_SILENCE_DURATION,
        hop_length: int = DEFAULT_HOP_LENGTH,
        sample_rate: int = DEFAULT_SAMPLE_RATE,
    ) -> None:
        self.audio_path = str(audio_path)
        self.mode = mode
        self.min_silence_duration = min_silence_duration
        self.hop_length = hop_length
        self.sample_rate = sample_rate
        self._waveform: np.ndarray | None = None
        self._forced_model: object | None = None
        self._forced_processor: object | None = None
        self._temp_audio: str | None = None
        self._loaded = False

    def cleanup(self) -> None:
        """Remove any temporary audio file created for container formats."""
        self._cleanup_temp()

    def _load_audio(self) -> np.ndarray:
        """Load audio as mono float32 at the target sample rate.

        WAV-family files are read directly with soundfile; other
        containers (mp4, mp3, ...) are first extracted to a temporary
        16 kHz mono WAV via ffmpeg. Resampling uses linear interpolation,
        which is adequate for energy-based VAD.
        """
        if self._loaded:
            return self._waveform

        self._cleanup_temp()

        try:
            if self.audio_path.lower().endswith(".wav"):
                data, sr = sf.read(
                    self.audio_path, dtype="float32", always_2d=True
                )
            else:
                data, sr = self._extract_wav()
            if len(data) == 0:
                raise RuntimeError("audio file is empty")
            if sr != self.sample_rate:
                n_out = max(1, round(len(data) * self.sample_rate / sr))
                x_old = np.linspace(0.0, 1.0, num=len(data), endpoint=False)
                x_new = np.linspace(0.0, 1.0, num=n_out, endpoint=False)
                data = np.interp(x_new, x_old, data)
            # Mono: average channels if stereo
            if data.shape[1] > 1:
                data = data.mean(axis=1)
            self._waveform = data.astype(np.float32)
            self._loaded = True
            logger.info(
                "Loaded audio: %s (%.1fs, %dHz)",
                self.audio_path,
                len(self._waveform) / self.sample_rate,
                self.sample_rate,
            )
        except (OSError, sf.LibsndfileError, RuntimeError) as e:
            # RuntimeError includes our "audio file is empty" / ffmpeg failures
            logger.error("Failed to load audio %s: %s", self.audio_path, e)
            raise RuntimeError(f"Cannot load audio: {e}")

        return self._waveform

    def _extract_wav(self) -> tuple[np.ndarray, int]:
        """Extract audio from a non-WAV container to a temp 16 kHz mono WAV."""
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            self._temp_audio = tmp.name
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            self.audio_path,
            "-ac",
            "1",
            "-ar",
            str(self.sample_rate),
            "-vn",
            self._temp_audio,
        ]
        result = run_ffmpeg(cmd, timeout=300)
        if getattr(result, "returncode", 0) != 0:
            raise RuntimeError(
                "ffmpeg audio extraction failed: "
                f"{getattr(result, 'stderr', b'').decode(errors='replace')[:300]}"
            )
        return sf.read(self._temp_audio, dtype="float32", always_2d=True)

    def _cleanup_temp(self) -> None:
        if self._temp_audio and Path(self._temp_audio).exists():
            try:
                Path(self._temp_audio).unlink()
            except OSError:
                pass
            self._temp_audio = None

    def _load_forced_model(self) -> None:
        """Load wav2vec2 forced alignment model (optional)."""
        if self._forced_model is not None:
            return

        try:
            from transformers import (
                Wav2Vec2ForCTC,
                Wav2Vec2Processor,
            )
        except ImportError:
            raise ImportError(
                "transformers is not installed. "
                "For forced alignment, install with: uv sync --extra gpu"
            )

        logger.info("Loading forced alignment model: %s", DEFAULT_PHONEME_MODEL)
        self._forced_processor = Wav2Vec2Processor.from_pretrained(DEFAULT_PHONEME_MODEL)
        self._forced_model = Wav2Vec2ForCTC.from_pretrained(DEFAULT_PHONEME_MODEL)
        self._forced_model.eval()
        logger.info("Forced alignment model loaded")

    def align(
        self,
        asr_words: list[Word],
        asr_text: str | None = None,
    ) -> AlignmentResult:
        """Align ASR words to audio using selected mode.

        Args:
            asr_words: List of Word objects from ASR with approximate timing.
            asr_text: Optional full transcription text.

        Returns:
            AlignmentResult with precisely timed words.
        """
        self._load_audio()

        if self.mode == "forced" and self._forced_model is None:
            try:
                self._load_forced_model()
            except ImportError:
                logger.warning(
                    "Forced alignment model unavailable, falling back to VAD refinement"
                )
                self.mode = "vad_refinement"

        if self.mode == "forced":
            return self._align_forced(asr_words)
        else:
            return self._align_vad_refinement(asr_words, asr_text)

    def _align_vad_refinement(
        self,
        asr_words: list[Word],
        asr_text: str | None = None,
    ) -> AlignmentResult:
        """Refine boundaries using VAD silence detection.

        This method:
        1. Computes per-frame RMS energy (vectorized)
        2. Thresholds against an adaptive noise floor (relative to the
           loudest 5% of frames, so quiet and loud recordings both work)
        3. Merges silences shorter than min_silence_duration — a brief
           dip is a breath/pause inside a word, not a boundary
        4. Snaps each word boundary to the nearest true transition
        5. Detects overlaps between consecutive words

        Precision: sub-150ms (depends on min_silence_duration)
        """
        waveform = self._waveform
        sr = self.sample_rate
        hop_samples = int(self.hop_length / 1000.0 * sr)

        # Vectorized per-frame RMS energy
        n_frames = len(waveform) // hop_samples
        if n_frames > 0:
            frames = waveform[: n_frames * hop_samples].reshape(
                n_frames, hop_samples
            )
            energies = np.sqrt(np.mean(frames.astype(np.float32) ** 2, axis=1))
            # Adaptive threshold: relative to the loudest 5% of frames
            energy_threshold = max(
                ABSOLUTE_ENERGY_FLOOR,
                SPEECH_THRESHOLD_RATIO * float(np.percentile(energies, 95)),
            )
            silence_frames = energies < energy_threshold

            # Merge silences shorter than min_silence_duration
            min_silence_frames = max(
                1, int(self.min_silence_duration * sr / hop_samples)
            )
            silence_frames = self._merge_short_silence(
                silence_frames, min_silence_frames
            )
        else:
            silence_frames = np.zeros(0, dtype=bool)

        aligned_words: list[AlignedWord] = []
        boundary_counts: dict[str, int] = {"speech": 0, "silence": 0, "overlap": 0, "filler": 0}

        for i, word in enumerate(asr_words):
            start_sec = word.start
            end_sec = word.end

            # Convert to frame indices
            start_frame = max(0, int(start_sec * sr / hop_samples))
            end_frame = min(n_frames, int(end_sec * sr / hop_samples))

            # Check if boundaries are on silence
            start_on_silence = start_frame > 0 and silence_frames[start_frame - 1]
            end_on_silence = end_frame < n_frames and silence_frames[end_frame]

            # Refine boundaries
            refined_start = start_sec
            refined_end = end_sec

            if start_on_silence:
                # The word starts inside a silence run: snap forward to
                # the next speech onset (ASR undershoot). If speech does
                # not resume nearby, leave the ASR timing unchanged.
                for f in range(start_frame, min(n_frames, start_frame + 50)):
                    if not silence_frames[f]:
                        refined_start = f * hop_samples / sr
                        break
                boundary_counts["silence"] += 1
            else:
                boundary_counts["speech"] += 1

            if end_on_silence:
                # The word ends inside a silence run: snap back to the
                # run's onset — the word ends where the speech did, not
                # somewhere in the silence.
                f = end_frame
                while f > 0 and silence_frames[f]:
                    f -= 1
                refined_end = (f + 1) * hop_samples / sr
                boundary_counts["silence"] += 1
            else:
                boundary_counts["speech"] += 1

            # Detect overlap with next word
            boundary_type = "speech"
            if i < len(asr_words) - 1:
                next_word = asr_words[i + 1]
                gap = next_word.start - end_sec
                if gap < 0:
                    boundary_type = "overlap"
                    boundary_counts["overlap"] += 1
                elif gap < 0.08:
                    boundary_type = "filler"
                    boundary_counts["filler"] += 1
                else:
                    boundary_counts["speech"] += 1
            else:
                boundary_counts["speech"] += 1

            aligned = AlignedWord(
                text=word.text,
                start=round(refined_start, 4),
                end=round(refined_end, 4),
                confidence=word.confidence,
                speaker_id=word.speaker_id,
                boundary_type=boundary_type,
            )
            aligned_words.append(aligned)

        # Calculate confidence stats
        confidences = [w.confidence for w in aligned_words] if aligned_words else [0.0]
        result = AlignmentResult(
            words=aligned_words,
            total_duration=len(waveform) / sr,
            method="vad_refinement",
            audio_path=self.audio_path,
            confidence_mean=float(np.mean(confidences)),
            confidence_min=float(np.min(confidences)),
            confidence_max=float(np.max(confidences)),
            boundary_counts=boundary_counts,
        )

        logger.info(
            "VAD alignment complete: %d words, %.2fs, method=%s",
            result.word_count,
            result.total_duration,
            result.method,
        )

        return result

    @staticmethod
    def _merge_short_silence(silence: np.ndarray, min_run: int) -> np.ndarray:
        """Treat silence runs shorter than min_run frames as speech.

        Brief dips (breaths, plosive onsets) must not become word
        boundaries; only silences of min_silence_duration or longer do.
        """
        out = silence.copy()
        n = len(out)
        i = 0
        while i < n:
            if out[i]:
                j = i + 1
                while j < n and out[j]:
                    j += 1
                if j - i < min_run:
                    out[i:j] = False
                i = j
            else:
                i += 1
        return out

    def _align_forced(self, asr_words: list[Word]) -> AlignmentResult:
        """Align words with a wav2vec2 CTC model.

        For each word, the model's per-frame posteriors are inspected:
        the first and last non-blank feature frames (after CTC
        duplicate collapse) mark where the word's acoustic content
        actually starts and ends. Words that produce only blanks keep
        their ASR boundaries.

        Precision: feature-frame resolution (~20-50ms)
        """
        try:
            import torch
        except ImportError as exc:
            raise ImportError(
                "torch is required for forced alignment. "
                "Install with: uv sync --extra gpu"
            ) from exc

        self._load_forced_model()
        waveform = self._load_audio()
        sr = self.sample_rate

        processor = self._forced_processor
        model = self._forced_model
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        model = model.to(device)
        blank_index = int(getattr(model.config, "blank_index", 0))

        aligned_words: list[AlignedWord] = []
        boundary_counts: dict[str, int] = {"speech": 0, "silence": 0, "overlap": 0, "filler": 0}

        for word in asr_words:
            start_sec = word.start
            end_sec = word.end

            # Extract word segment audio
            start_samples = int(start_sec * sr)
            end_samples = int(end_sec * sr) + 100  # small padding
            end_samples = min(end_samples, len(waveform))

            if start_samples >= end_samples:
                # Skip empty/silent words
                continue

            word_audio = waveform[start_samples:end_samples]
            word_audio = torch.tensor(word_audio).unsqueeze(0).to(device)

            # Run wav2vec2 inference
            with torch.no_grad():
                inputs = processor(
                    word_audio.squeeze(),
                    sampling_rate=sr,
                    return_tensors="pt",
                ).to(device)
                logits = model(**inputs).logits

            # Get predicted phoneme IDs
            labels = torch.argmax(logits, dim=-1)
            transcription = processor.decode(labels[0])

            # Extract phonemes (simplified — wav2vec2 outputs phoneme tokens)
            phonemes = [p for p in transcription.strip().split() if p]

            # Confidence: mean of the max posterior per frame
            max_probs = torch.softmax(logits, dim=-1).max(dim=-1).values
            confidence = float(max_probs.mean().item())

            # Refine boundaries from the CTC posterior span
            refined_start, refined_end = ctc_word_boundaries(
                labels.cpu().numpy(),
                blank_index=blank_index,
                start_sec=start_sec,
                end_sec=end_sec,
            )

            aligned = AlignedWord(
                text=word.text,
                start=round(refined_start, 4),
                end=round(refined_end, 4),
                confidence=confidence,
                speaker_id=word.speaker_id,
                phonemes=phonemes[:20],  # Limit phoneme list size
                alignment_confidence=confidence,
                boundary_type="speech",
            )
            aligned_words.append(aligned)
            boundary_counts["speech"] += 1

        # Calculate stats
        confidences = [w.alignment_confidence for w in aligned_words] if aligned_words else [0.0]
        result = AlignmentResult(
            words=aligned_words,
            total_duration=len(waveform) / sr,
            method="forced",
            audio_path=self.audio_path,
            confidence_mean=float(np.mean(confidences)),
            confidence_min=float(np.min(confidences)),
            confidence_max=float(np.max(confidences)),
            boundary_counts=boundary_counts,
        )

        logger.info(
            "Forced alignment complete: %d words, method=%s",
            result.word_count,
            result.method,
        )

        return result
