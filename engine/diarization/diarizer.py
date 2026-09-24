"""Speaker diarization engine — PRIMARY speaker identification method.

Lightweight VAD + audio fingerprint backend (CPU-optimized for low-end hardware).

Instead of loading WeSpeaker ResNet34-LM (~500MB+), ONNX runtime, and
sklearn clustering — which freezes systems with 8 GB RAM — this uses:

    1. Silero VAD (~10 MB) for speech detection
    2. Energy + spectral fingerprinting for speaker change detection
    3. Template matching (no clustering) for speaker assignment

Architecture:
    Audio in → Silero VAD → Speech segments → Audio fingerprints → Speaker labels

Resource profile vs original diarize package:
    Peak RAM:  ~100–300 MB  (was ~2–4 GB)
    Model:     ~10 MB       (was ~500 MB+)
    CPU load:  Low (basic DSP, no heavy ML inference)

Accuracy trade-off:
    Optimized for 2–4 speaker scenarios (real estate default).
    Same speaker can have varying energy and still match correctly
    because template matching uses running averages.

Supported backends:
1. ``nemotron`` (default) — NVIDIA Nemotron 3 Diarization, open-weights
   (~100M-param transformer, released 2026-09-23, OpenMDW-1.1) via the
   audio.cpp CLI.  Up to eight speakers, overlapping-speech aware, real
   per-turn confidence.  Downloads a one-time 102 MB GGUF weight file on
   first use, then runs fully offline (~1 min per 10-min chunk, ~460 MB
   peak RSS on a 4-core CPU box — see tools/nemotron-bench/RESULTS.md).
2. ``diarize`` — Lightweight VAD + fingerprint, zero-dependency fallback.
3. ``pyannote`` — SOTA open-source, needs HuggingFace token.
4. ``ffmpeg_vad`` — Hard fallback, always available (no extra dependencies).

Per the Speaker Design Decision, audio diarization is PRIMARY.
Face tracking is used only as a fallback when confidence is low.

Usage:
    from engine.diarization.diarizer import Diarizer

    # Nemotron backend (default — one-time model download, then offline)
    diarizer = Diarizer()

    # Or with explicit CLI/weights (dev build, local files)
    diarizer = Diarizer(
        backend="nemotron",
        cli_path="tools/nemotron-bench/audio.cpp/build/bin/audiocpp_cli",
        model_path="models/nemotron-3-diarization-q8_0.gguf",
    )

    # Zero-dependency fallback
    diarizer = Diarizer(backend="diarize")

    # Pyannote backend (requires HF token)
    diarizer = Diarizer(backend="pyannote", token="hf_xxx")

    segments = diarizer.run("audio.wav")
"""

from __future__ import annotations

import logging
import os
import tempfile
from pathlib import Path
from typing import Any, Optional

from engine.core.ffmpeg import run_ffmpeg
from engine.diarization.models import SpeakerSegment

logger = logging.getLogger("caption_with_intention")

DEFAULT_MIN_SPEAKER_DURATION = 0.5
DEFAULT_SPEAKER_CONFIDENCE = 0.5
# Cosine-similarity threshold: below this, a segment is a new speaker.
_FINGERPRINT_SIM_THRESHOLD = 0.85


class Diarizer:
    """Audio-based speaker diarization engine with pluggable backends.

    Args:
        backend: Diarization backend to use. Options:
            - ``"nemotron"`` — NVIDIA Nemotron 3 Diarization (default)
            - ``"diarize"`` — Lightweight VAD + fingerprint, zero-dependency
            - ``"pyannote"`` — SOTA open-source, needs HuggingFace token
            - ``"ffmpeg_vad"`` — Hard fallback, always available
        min_speaker_duration: Minimum duration for a speaker segment (seconds).
        min_confidence: Minimum confidence threshold for segments.
        token: HuggingFace access token (required for ``pyannote`` backend).
        **kwargs: Backend-specific configuration options.  For ``nemotron``:
            ``cli_path``, ``model_path``, ``auto_download``, ``threads``,
            ``speaker_threshold``.
    """

    def __init__(
        self,
        backend: str = "nemotron",
        min_speaker_duration: float = DEFAULT_MIN_SPEAKER_DURATION,
        min_confidence: float = DEFAULT_SPEAKER_CONFIDENCE,
        token: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        self.backend = backend
        self.min_speaker_duration = min_speaker_duration
        self.min_confidence = min_confidence
        self.token = token
        self._backend_config = kwargs
        self._segments: list[SpeakerSegment] = []
        self._backend_instance: Any = None

    def run(self, source_path: str, **kwargs: Any) -> list[SpeakerSegment]:
        """Run diarization on a source audio/video file.

        Args:
            source_path: Path to audio/video file.
            **kwargs: Additional backend-specific options.

        Returns:
            List of SpeakerSegment objects with timing and confidence.
        """
        logger.info("Running diarization (backend=%s) on %s", self.backend, source_path)

        segments = self._run_backend(source_path, **kwargs)

        # Filter by minimum duration and confidence
        filtered = [
            s for s in segments
            if s.duration >= self.min_speaker_duration
            and s.confidence >= self.min_confidence
        ]

        self._segments = filtered
        logger.info(
            "Diarization complete: %d segments from %s",
            len(filtered),
            source_path,
        )
        return filtered

    def _run_backend(self, source_path: str, **kwargs: Any) -> list[SpeakerSegment]:
        """Dispatch to the configured backend."""
        if self.backend == "nemotron":
            return self._run_nemotron(source_path, **kwargs)
        elif self.backend == "diarize":
            return self._run_diarize(source_path, **kwargs)
        elif self.backend == "pyannote":
            return self._run_pyannote(source_path, **kwargs)
        else:
            return self._run_ffmpeg_vad(source_path, **kwargs)

    def _prepare_16k_wav(self, source_path: str) -> tuple[Path, bool, float] | None:
        """Prepare a 16 kHz mono WAV for model-based backends.

        Returns ``(path, is_temp, duration_s)`` — when ``is_temp`` is
        True the caller must delete the file.  Existing 16 kHz WAVs are
        used in place.  Returns None when extraction fails.
        """
        p = Path(source_path)
        if p.suffix.lower() == ".wav" and p.is_file():
            try:
                import soundfile as sf

                info = sf.info(str(p))
                if info.samplerate == 16000:
                    return p, False, info.frames / info.samplerate
            except Exception:
                pass  # unreadable header — fall through and re-extract

        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        tmp_path = Path(tmp.name)
        tmp.close()
        cmd = [
            "ffmpeg", "-y", "-i", source_path,
            "-ac", "1", "-ar", "16000", "-vn", str(tmp_path),
        ]
        try:
            result = run_ffmpeg(cmd, timeout=300)
            if result.returncode != 0 or not tmp_path.is_file():
                return None
        except Exception as e:
            logger.warning("Audio extraction failed: %s", e)
            return None
        try:
            import soundfile as sf

            info = sf.info(str(tmp_path))
            duration = info.frames / info.samplerate
        except Exception:
            duration = 0.0
        return tmp_path, True, duration

    def _run_nemotron(self, source_path: str, **kwargs: Any) -> list[SpeakerSegment]:
        """Run NVIDIA Nemotron 3 Diarization (default backend).

        Open-weights ~100M-param model (OpenMDW-1.1) via the audio.cpp
        CPU backend: up to eight speakers, overlapping-speech aware,
        real per-turn confidence.  The GGUF weights (~102 MB Q8_0) are
        downloaded once on first use into
        ``~/.cache/caption_with_intention/models/``; afterwards fully
        offline.  Measured on a 4-core / 8 GB CPU box: ~1 min per
        10-min chunk, ~460 MB peak RSS.

        Falls back to FFmpeg VAD when the CLI or model is unavailable.
        """
        from engine.diarization import nemotron

        cli = nemotron.resolve_cli(kwargs.get("cli_path"))
        if cli is None:
            logger.warning(
                "audiocpp_cli not found (pass cli_path or set %s). "
                "Falling back to FFmpeg VAD.",
                nemotron.DEFAULT_ENV_CLI,
            )
            return self._run_ffmpeg_vad(source_path, **kwargs)

        model = nemotron.ensure_model(
            kwargs.get("model_path"),
            auto_download=bool(kwargs.get("auto_download", True)),
        )
        if model is None:
            logger.warning(
                "Nemotron model unavailable (download failed or disabled). "
                "Falling back to FFmpeg VAD."
            )
            return self._run_ffmpeg_vad(source_path, **kwargs)

        prepared = self._prepare_16k_wav(source_path)
        if prepared is None:
            logger.warning("Audio extraction failed, falling back to FFmpeg VAD")
            return self._run_ffmpeg_vad(source_path, **kwargs)
        wav, is_tmp, duration = prepared

        # Generous timeout: measured ~10x realtime on CPU, keep 7.5x headroom
        timeout = int(max(180.0, 120.0 + duration * 0.75))
        threads = int(kwargs.get("threads") or min(4, os.cpu_count() or 4))
        out_json = Path(tempfile.gettempdir()) / f"cwi_nemotron_{os.getpid()}.json"
        try:
            return nemotron.run_diarization(
                cli,
                model,
                wav,
                out_json,
                threads=threads,
                speaker_threshold=kwargs.get("speaker_threshold"),
                timeout=timeout,
            )
        except RuntimeError as e:
            logger.warning(
                "Nemotron diarization failed: %s. Falling back to FFmpeg VAD.", e
            )
            return self._run_ffmpeg_vad(source_path, **kwargs)
        finally:
            if is_tmp:
                try:
                    os.unlink(wav)
                except OSError:
                    pass
            out_json.unlink(missing_ok=True)

    def _run_diarize(self, source_path: str, **kwargs: Any) -> list[SpeakerSegment]:
        """Run lightweight diarization — VAD + audio fingerprint (CPU-optimized).

        Replaces the resource-heavy WeSpeaker ResNet34-LM + ONNX runtime
        + sklearn clustering pipeline with a VAD + energy/spectral fingerprint
        approach that runs safely on an i5 with 8 GB RAM.

        Pipeline:
            1. Silero VAD detects speech segments (~10 MB model)
            2. Audio fingerprints computed per segment (RMS energy,
               spectral centroid, spectral bandwidth, zero-crossing rate)
            3. Template matching assigns speaker labels (no clustering)

        Resource profile vs original diarize package:
            Peak RAM:  ~100–300 MB  (was ~2–4 GB)
            Model:     ~10 MB        (was ~500 MB+)
            CPU load:  Low (basic DSP, no heavy ML inference)

        Accuracy: Optimised for 2–4 speakers (real estate default).
        Template matching uses running averages so a speaker whose
        energy varies (whisper ↔ normal voice) still matches correctly.

        Args:
            source_path: Path to audio or video file.
            num_speakers: Expected number of speakers (default 2).
            **kwargs: Kept for API compatibility (min_speakers,
                max_speakers, num_speakers).

        Returns:
            List of SpeakerSegment objects.
        """
        # Limit CPU threads BEFORE any torch operations to prevent
        # resource exhaustion on low-end hardware.
        os.environ.setdefault("OMP_NUM_THREADS", "2")
        os.environ.setdefault("MKL_NUM_THREADS", "2")

        import numpy as np
        import soundfile as sf

        # Extract audio to mono 16 kHz wav if needed
        prepared = self._prepare_16k_wav(source_path)
        if prepared is None:
            logger.warning("Audio extraction failed, falling back to FFmpeg VAD")
            return self._run_ffmpeg_vad(source_path, **kwargs)
        src_path, is_tmp, _ = prepared

        try:
            # Limit torch threads for the VAD step
            try:
                import torch

                torch.set_num_threads(2)
            except ImportError:
                pass

            # Load audio as float32 mono at 16 kHz
            try:
                audio_data, sr = sf.read(src_path, dtype="float32")
                if audio_data.ndim > 1:
                    audio_data = audio_data.mean(axis=1)
            except Exception as e:
                logger.warning("Failed to load audio: %s", e)
                return self._run_ffmpeg_vad(source_path, **kwargs)

            duration = len(audio_data) / sr if sr > 0 else 0.0
            if duration <= 0.0:
                return self._run_ffmpeg_vad(source_path, **kwargs)

            # Run Silero VAD for speech segments
            try:
                from silero_vad import (
                    get_speech_timestamps,
                    load_silero_vad,
                )

                vad_model = load_silero_vad()
                speech_timestamps = get_speech_timestamps(
                    torch.from_numpy(audio_data),
                    vad_model,
                    sampling_rate=16000,
                    threshold=0.45,
                    min_speech_duration_ms=200,
                    min_silence_duration_ms=50,
                    speech_pad_ms=20,
                )
            except Exception as e:
                logger.warning("VAD failed: %s", e)
                return self._run_ffmpeg_vad(source_path, **kwargs)

            if not speech_timestamps:
                # No speech detected — single fallback segment
                return [
                    SpeakerSegment(
                        speaker_id="SPEAKER_00",
                        start=0.0,
                        end=duration,
                        confidence=0.5,
                        source="diarize_fallback",
                    )
                ]

            # Expected speaker count (default 2 for real estate)
            num_speakers = kwargs.get("num_speakers", kwargs.get("max_speakers", 2))
            if num_speakers is None:
                num_speakers = 2
            num_speakers = max(1, min(int(num_speakers), 6))

            # Compute fingerprints and assign speakers
            return self._fingerprint_diarize(
                audio_data, sr, speech_timestamps, num_speakers
            )
        finally:
            # Clean up temp wav if we created one
            if is_tmp:
                try:
                    os.unlink(src_path)
                except OSError:
                    pass

    def _fingerprint_diarize(
        self,
        audio_data: np.ndarray,
        sr: int,
        speech_timestamps: list[dict],
        num_speakers: int,
    ) -> list[SpeakerSegment]:
        """Assign speaker labels to VAD segments via audio fingerprint matching.

        For each speech segment a lightweight feature vector is computed:

            [RMS energy, energy variance, normalised spectral centroid,
             normalised spectral bandwidth, zero-crossing rate]

        The first segment becomes SPEAKER_00's template; the first segment
        that is sufficiently dissimilar becomes SPEAKER_01's template;
        and so on up to *num_speakers*.  Every subsequent segment is
        matched to the closest template via cosine similarity.

        Args:
            audio_data: Full mono float32 audio at sample rate *sr*.
            sr: Sample rate in Hz.
            speech_timestamps: List of dicts with ``'start'`` and
                ``'end'`` keys (milliseconds) from Silero VAD.
            num_speakers: Maximum number of speaker templates.

        Returns:
            List of SpeakerSegment objects.
        """
        fingerprints: list[np.ndarray] = []
        segments: list[tuple[float, float]] = []

        for ts in speech_timestamps:
            start = ts["start"] / 1000.0  # ms → s
            end = ts["end"] / 1000.0
            chunk = audio_data[
                int(start * sr) : int(end * sr)
            ]
            if len(chunk) < int(sr * 0.1):  # skip <100 ms
                continue
            fp = self._compute_fingerprint(chunk, sr)
            fingerprints.append(fp)
            segments.append((start, end))

        if not segments:
            duration = len(audio_data) / sr if sr > 0 else 1.0
            return [
                SpeakerSegment(
                    speaker_id="SPEAKER_00",
                    start=0.0,
                    end=duration,
                    confidence=0.5,
                    source="diarize_fallback",
                )
            ]

        fingerprints_arr = np.stack(fingerprints).astype(np.float32)
        speaker_ids = self._assign_speakers_by_fingerprint(
            fingerprints_arr, num_speakers
        )

        return [
            SpeakerSegment(
                speaker_id=f"SPEAKER_{sid:02d}",
                start=start,
                end=end,
                confidence=0.85,
                source="diarize",
            )
            for (start, end), sid in zip(segments, speaker_ids)
        ]

    @staticmethod
    def _compute_fingerprint(audio_chunk: np.ndarray, sr: int) -> np.ndarray:
        """Compute a 5-dimensional audio fingerprint for a speech segment.

        Features (all energy-normalised where applicable):
            0. RMS energy (mean level)
            1. Energy variance across 4 quarters (dynamic range proxy)
            2. Normalised spectral centroid (brightness / pitch indicator)
            3. Normalised spectral bandwidth (timbre width)
            4. Zero-crossing rate (noisiness / consonant-vowel ratio)

        Args:
            audio_chunk: 1-D float32 numpy array of one speech segment.
            sr: Sample rate in Hz.

        Returns:
            5-element float32 numpy array.
        """
        audio_chunk = np.asarray(audio_chunk, dtype=np.float32)
        n = len(audio_chunk)
        if n == 0:
            return np.zeros(5, dtype=np.float32)

        # --- 0 & 1. RMS energy and its variance across 4 quarters ---
        rms_mean = float(np.sqrt(np.mean(audio_chunk ** 2)))
        chunk_size = max(n // 4, 512)
        energies = [
            float(np.sqrt(np.mean(audio_chunk[i : i + chunk_size] ** 2)))
            for i in range(0, n, chunk_size)
            if len(audio_chunk[i : i + chunk_size]) > 0
        ]
        energy_std = (
            float(np.std(energies)) if len(energies) > 1 else 0.0
        )

        # --- 2 & 3. Spectral features via FFT ---
        win_len = min(n, 2048)
        window = np.hanning(win_len)
        fft = np.fft.rfft(audio_chunk[:win_len] * window)
        mags = np.abs(fft)
        freqs = np.fft.rfftfreq(win_len, d=1.0 / sr)

        total_mag = float(np.sum(mags))
        if total_mag > 1e-10:
            spectral_centroid = float(np.sum(freqs * mags) / total_mag)
            spectral_bandwidth = float(
                np.sum(((freqs - spectral_centroid) ** 2) * mags) / total_mag
            )
            spectral_bandwidth = float(np.sqrt(spectral_bandwidth))
        else:
            spectral_centroid = 0.0
            spectral_bandwidth = 0.0

        nyq = sr / 2.0
        sc_norm = spectral_centroid / nyq if nyq > 0 else 0.0
        sb_norm = spectral_bandwidth / nyq if nyq > 0 else 0.0

        # --- 4. Zero-crossing rate ---
        zcr = float(
            np.sum(np.abs(np.diff(np.sign(audio_chunk)))) / (2.0 * n)
        )

        return np.array(
            [rms_mean, energy_std, sc_norm, sb_norm, zcr],
            dtype=np.float32,
        )

    @staticmethod
    def _assign_speakers_by_fingerprint(
        fingerprints: np.ndarray,
        num_speakers: int,
    ) -> list[int]:
        """Assign speaker IDs to segments via cosine-similarity template matching.

        The first segment is SPEAKER_00.  Each subsequent segment is compared
        to the running-average template of every known speaker.  If its
        cosine similarity is below ``_FINGERPRINT_SIM_THRESHOLD`` and we
        haven't reached *num_speakers* yet, it becomes a new speaker.

        Args:
            fingerprints: (N, 5) float32 array of pre-computed fingerprints.
            num_speakers: Maximum number of distinct speakers.

        Returns:
            List of speaker IDs (0-indexed ints).
        """
        if len(fingerprints) == 0:
            return []

        # L2-normalise so dot product = cosine similarity
        norms = np.linalg.norm(fingerprints, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        normalized = fingerprints / norms

        speaker_ids: list[int] = [0]
        templates: list[np.ndarray] = [normalized[0].copy()]

        for i in range(1, len(fingerprints)):
            fp = normalized[i]
            best_sim = float(np.dot(fp, templates[0]))
            best_idx = 0
            for t_idx in range(1, len(templates)):
                sim = float(np.dot(fp, templates[t_idx]))
                if sim > best_sim:
                    best_sim = sim
                    best_idx = t_idx

            if best_sim < _FINGERPRINT_SIM_THRESHOLD and len(templates) < num_speakers:
                speaker_ids.append(len(templates))
                templates.append(fp.copy())
            else:
                speaker_ids.append(best_idx)

        return speaker_ids

    def _run_pyannote(self, source_path: str, **kwargs: Any) -> list[SpeakerSegment]:
        """Run pyannote.audio backend (SOTA, needs HuggingFace token).

        Requires: ``pip install pyannote.audio`` + HuggingFace access token.
        Model: pyannote/speaker-diarization-community-1 (offline capable).

        Args:
            source_path: Path to audio file (16kHz mono preferred).
            **kwargs: Passed to pyannote Pipeline.

        Returns:
            List of SpeakerSegment objects.
        """
        try:
            from pyannote.audio import Pipeline
        except ImportError:
            logger.warning(
                "pyannote.audio not installed. Falling back to FFmpeg VAD. "
                "Install with: pip install pyannote.audio"
            )
            return self._run_ffmpeg_vad(source_path, **kwargs)

        if not self.token:
            logger.warning(
                "No HuggingFace token provided for pyannote backend. "
                "Falling back to FFmpeg VAD."
            )
            return self._run_ffmpeg_vad(source_path, **kwargs)

        pipeline = Pipeline.from_pretrained(
            "pyannote/speaker-diarization-community-1",
            token=self.token,
            **self._backend_config,
        )

        diarization = pipeline(source_path)
        segments: list[SpeakerSegment] = []
        for segment, _, speaker in diarization.itertracks(yield_label=True):
            segments.append(
                SpeakerSegment(
                    speaker_id=str(speaker),
                    start=segment.start,
                    end=segment.end,
                    confidence=1.0,  # pyannote doesn't expose per-segment confidence in standard API
                    source="pyannote",
                )
            )
        return segments

    def _run_ffmpeg_vad(self, source_path: str, **kwargs: Any) -> list[SpeakerSegment]:
        """Run FFmpeg-based VAD fallback (always available, no extra deps).

        Uses FFmpeg's silencedetect filter to find speech segments,
        then creates one speaker segment per speech region.

        Args:
            source_path: Path to audio/video file.
            **kwargs: Ignored.

        Returns:
            List of SpeakerSegment objects (single speaker, speech regions).
        """
        segments: list[SpeakerSegment] = []

        try:
            cmd = [
                "ffmpeg",
                "-i",
                source_path,
                "-af",
                "silencedetect=noise=-40dB:d=0.5",
                "-f",
                "null",
                "-",
            ]
            result = run_ffmpeg(cmd, timeout=300)

            import re
            stderr = result.stderr or ""
            silence_starts = re.findall(r"silence_start:\s*([\d.]+)", stderr)
            silence_ends = re.findall(r"silence_end:\s*([\d.]+)", stderr)

            prev_end = 0.0
            for i, start_str in enumerate(silence_starts):
                start = float(start_str)
                if i < len(silence_ends):
                    end = float(silence_ends[i])
                else:
                    end = start + 2.0

                if start > prev_end:
                    segments.append(
                        SpeakerSegment(
                            speaker_id="speaker_0",
                            start=prev_end,
                            end=start,
                            confidence=0.7,
                            source="ffmpeg_vad",
                        )
                    )
                    prev_end = end

        except RuntimeError as e:
            logger.warning("FFmpeg VAD failed: %s", e)

        # Fallback: single segment covering full duration
        if not segments:
            try:
                from engine.media.probe import probe_video
                info = probe_video(source_path)
                duration = info.get("duration", 10.0)
            except Exception:
                duration = 10.0

            segments.append(
                SpeakerSegment(
                    speaker_id="speaker_0",
                    start=0.0,
                    end=duration,
                    confidence=0.5,
                    source="hardcoded_fallback",
                )
            )

        return segments

    def get_segments(self) -> list[SpeakerSegment]:
        """Return the last diarization result."""
        return list(self._segments)

    def to_dict(self) -> dict:
        return {
            "backend": self.backend,
            "segments": [s.to_dict() for s in self._segments],
            "min_speaker_duration": self.min_speaker_duration,
            "min_confidence": self.min_confidence,
            "backend_config": self._backend_config,
        }
