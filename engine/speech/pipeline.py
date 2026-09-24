"""Speech pipeline — ASR + Diarization + Alignment in one pass.

Resource-optimized pipeline: ASR and diarization run concurrently,
word-to-speaker matching is O(n) time-based overlap.

Architecture timeline:

    Audio in ──┬──→ ASR (words w/ timestamps) ─────┐
               └──→ Diarization (speaker times) ────┤→ Match → Output

    Speaker segments: [0-5s: A][5-10s: B][10-15s: A]...
    Words:            "hi"(1s) "bye"(7s) "ok"(12s)...
    Result:           "hi"(A)  "bye"(B) "ok"(A)

Resource savings:
    - One audio load shared across both pipelines
    - No per-word speaker model — just time-based matching
    - ASR + diarization run in parallel wall-clock time
    - Cached diarization reusable across chunks for long videos
"""

from __future__ import annotations

import bisect
import logging
import re
from concurrent.futures import ThreadPoolExecutor
from itertools import pairwise
from pathlib import Path

from engine.alignment.aligner import Aligner
from engine.asr.corrector import CorrectionReport, TranscriptCorrector
from engine.asr.models import TranscriptionResult, Word
from engine.asr.transcriber import Transcriber
from engine.diarization.diarizer import Diarizer

logger = logging.getLogger("caption_with_intention")

DEFAULT_DIARIZE_BACKEND = "nemotron"
DEFAULT_DIARIZE_CONFIDENCE = 0.5
MAX_CONCURRENT_WORKERS = 2


class SpeechPipeline:
    """Full speech processing pipeline — concurrent ASR + diarization.

    Args:
        asr_model: Whisper model size for ASR.
        asr_device: "cpu" or "cuda".
        asr_compute_type: "int8" or "float16".
        diarize_backend: Diarization backend ("nemotron", "diarize",
            "pyannote", "ffmpeg_vad").
        diarize_confidence: Minimum confidence for diarization segments.
        align_mode: "forced" or "vad_refinement".
        language: ISO language code for ASR.
        max_workers: Max concurrent pipeline stages (default 2: ASR + diarization).
        correct_transcript: Apply rule-based transcript correction (M6)
            to the ASR word list.
        min_confidence: Words below this confidence are flagged for review
            during correction.
    """

    def __init__(
        self,
        asr_model: str = "large-v3-turbo",
        asr_device: str = "cpu",
        asr_compute_type: str = "int8",
        diarize_backend: str = DEFAULT_DIARIZE_BACKEND,
        diarize_confidence: float = DEFAULT_DIARIZE_CONFIDENCE,
        align_mode: str = "vad_refinement",
        language: str = "en",
        max_workers: int = MAX_CONCURRENT_WORKERS,
        correct_transcript: bool = True,
        min_confidence: float = 0.5,
    ) -> None:
        self.asr_model = asr_model
        self.asr_device = asr_device
        self.asr_compute_type = asr_compute_type
        self.diarize_backend = diarize_backend
        self.diarize_confidence = diarize_confidence
        self.align_mode = align_mode
        self.language = language
        self.max_workers = max_workers
        self.correct_transcript = correct_transcript
        self.min_confidence = min_confidence

        self._transcriber: Transcriber | None = None
        self._diarizer: Diarizer | None = None
        self._aligner: Aligner | None = None
        self._corrector = TranscriptCorrector(min_confidence=min_confidence)

    @property
    def transcriber(self) -> Transcriber:
        if self._transcriber is None:
            self._transcriber = Transcriber(
                model=self.asr_model,
                device=self.asr_device,
                compute_type=self.asr_compute_type,
            )
        return self._transcriber

    @property
    def diarizer(self) -> Diarizer:
        if self._diarizer is None:
            self._diarizer = Diarizer(
                backend=self.diarize_backend,
                min_confidence=self.diarize_confidence,
            )
        return self._diarizer

    def run(
        self,
        source_path: str | Path,
        min_speaker_duration: float = 0.5,
    ) -> dict:
        """Run the full speech pipeline concurrently.

        ASR and diarization run in parallel on the same audio source.
        Word-to-speaker matching happens after both complete.

        Args:
            source_path: Path to audio/video file.
            min_speaker_duration: Minimum speaker segment duration.

        Returns:
            Dict with transcription, speakers, and metadata.
        """
        source = Path(source_path)
        logger.info("=== Speech Pipeline Start: %s ===", source.name)

        # --- Run ASR + Diarization concurrently ---
        logger.info("Running ASR + diarization in parallel...")
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            asr_future = executor.submit(self._run_asr, source)
            diarization_future = executor.submit(
                self._run_diarization, source, min_speaker_duration
            )
            asr_result = asr_future.result()
            diarization_segments = diarization_future.result()

        # --- Speaker Matching ---
        logger.info("Matching speakers to words...")
        words_with_speakers = self._match_speakers(
            asr_result.words,
            diarization_segments,
        )
        logger.info(
            "Speaker matching complete: %d/%d words attributed",
            sum(1 for w in words_with_speakers if w.speaker_id),
            len(words_with_speakers),
        )

        # --- Transcript Correction (M6) ---
        corrections: CorrectionReport | None = None
        if self.correct_transcript and words_with_speakers:
            corrections = self._corrector.correct(words_with_speakers)
            words_with_speakers = corrections.words
            logger.info(
                "Transcript correction: %d words out, %d removed, %d flagged",
                corrections.word_count,
                corrections.to_dict()["summary"]["removed"],
                corrections.to_dict()["summary"]["flagged"],
            )

        # Build attributed transcription
        attributed_text = " ".join(w.text for w in words_with_speakers)
        attributed_text = re.sub(r" +", " ", attributed_text).strip()

        attributed_result = TranscriptionResult(
            text=attributed_text,
            segments=asr_result.segments,
            words=words_with_speakers,
            language=asr_result.language,
            model=asr_result.model,
            source_path=str(source),
            duration=asr_result.duration,
        )

        return {
            "transcription": attributed_result,
            "diarization_segments": [
                seg.to_dict() for seg in diarization_segments
            ],
            "speaker_count": len(
                {seg.speaker_id for seg in diarization_segments}
            ),
            "asr_model": asr_result.model,
            "diarize_backend": self.diarize_backend,
            "words_attributed": sum(
                1 for w in words_with_speakers if w.speaker_id
            ),
            "corrections": corrections.to_dict() if corrections else None,
        }

    def run_with_alignment(
        self,
        source_path: str | Path,
        min_speaker_duration: float = 0.5,
    ) -> dict:
        """Run pipeline with alignment refinement.

        Same as run() but adds alignment pass for precise boundaries.
        Alignment uses the already-computed word timings from ASR —
        no need to re-run transcription.
        """
        result = self.run(
            source_path=source_path,
            min_speaker_duration=min_speaker_duration,
        )

        words = result["transcription"].words
        if not words:
            return result

        logger.info("Running alignment refinement...")
        aligner = Aligner(
            audio_path=str(source_path),
            mode=self.align_mode,
        )
        aligned = aligner.align(asr_words=words)

        result["transcription"] = TranscriptionResult(
            text=result["transcription"].text,
            segments=result["transcription"].segments,
            words=aligned.words,
            language=result["transcription"].language,
            model=result["transcription"].model,
            source_path=result["transcription"].source_path,
            duration=aligned.total_duration,
        )
        result["alignment"] = aligned.to_dict()
        result["alignment_method"] = aligned.method

        return result

    # ─── Editor Integration (M6) ───────────────────────────────────

    def build_editor_payload(self, result: dict) -> dict:
        """Convert a pipeline result into editor build input.

        Groups words into caption events per ASR segment, keeping precise
        word timing and AI provenance so the auto-generated word timeline
        is editable and reviewable in the editor (M6 exit criteria).

        Args:
            result: Output of run() or run_with_alignment().

        Returns:
            {"transcript": [...], "speakers": [...]} ready to pass to
            EditorApi.build_from_transcript().
        """
        transcription: TranscriptionResult = result["transcription"]
        model = transcription.model or "unknown"
        words = transcription.words

        # Collect speakers from diarization segments (stable order)
        speakers: list[dict] = []
        seen_speakers: set[str] = set()
        for seg in result.get("diarization_segments", []):
            spk_id = seg.get("speaker_id")
            if spk_id and spk_id not in seen_speakers:
                seen_speakers.add(spk_id)
                speakers.append(
                    {
                        "id": spk_id,
                        "name": f"Speaker {len(speakers) + 1}",
                        "category": "main",
                    }
                )

        entries: list[dict] = []
        segments = transcription.segments or []
        word_starts = [w.start for w in words]

        if segments:
            for seg in segments:
                # Words belong to the segment whose range contains their
                # onset — O(log W) lookup instead of O(W) per segment
                lo = bisect.bisect_left(word_starts, seg.start)
                hi = bisect.bisect_left(word_starts, seg.end)
                seg_words = words[lo:hi]
                if not seg_words and seg.words:
                    seg_words = list(seg.words)
                if not seg_words:
                    continue

                entry_words: list[dict] = []
                speaker_votes: dict[str, int] = {}
                for w in seg_words:
                    entry_words.append(
                        {
                            "text": w.text,
                            "start": round(w.start, 4),
                            "end": round(w.end, 4),
                            "confidence": w.confidence if w.confidence > 0 else None,
                            "source_model": model,
                            "source_timestamp": round(w.start, 4),
                        }
                    )
                    if w.speaker_id:
                        speaker_votes[w.speaker_id] = (
                            speaker_votes.get(w.speaker_id, 0) + 1
                        )

                confs = [w.confidence for w in seg_words if w.confidence > 0]
                entries.append(
                    {
                        "text": seg.text or " ".join(w.text for w in seg_words),
                        "start": round(seg.start, 4),
                        "end": round(seg.end, 4),
                        "words": entry_words,
                        "confidence": (
                            round(sum(confs) / len(confs), 4) if confs else None
                        ),
                        "source_model": model,
                        "source_timestamp": round(seg.start, 4),
                        "speaker_id": (
                            max(speaker_votes, key=speaker_votes.get)
                            if speaker_votes
                            else None
                        ),
                    }
                )
        elif words:
            # No segments — one event from the full word list
            confs = [w.confidence for w in words if w.confidence > 0]
            speaker_votes: dict[str, int] = {}
            for w in words:
                if w.speaker_id:
                    speaker_votes[w.speaker_id] = (
                        speaker_votes.get(w.speaker_id, 0) + 1
                    )
            entries.append(
                {
                    "text": transcription.text,
                    "start": round(min(w.start for w in words), 4),
                    "end": round(max(w.end for w in words), 4),
                    "words": [
                        {
                            "text": w.text,
                            "start": round(w.start, 4),
                            "end": round(w.end, 4),
                            "confidence": w.confidence if w.confidence > 0 else None,
                            "source_model": model,
                            "source_timestamp": round(w.start, 4),
                        }
                        for w in words
                    ],
                    "confidence": (
                        round(sum(confs) / len(confs), 4) if confs else None
                    ),
                    "source_model": model,
                    "speaker_id": (
                        max(speaker_votes, key=speaker_votes.get)
                        if speaker_votes
                        else None
                    ),
                }
            )

        # Ensure every referenced speaker id exists in the speaker list
        for entry in entries:
            spk_id = entry.get("speaker_id")
            if spk_id and spk_id not in seen_speakers:
                seen_speakers.add(spk_id)
                speakers.append(
                    {
                        "id": spk_id,
                        "name": f"Speaker {len(speakers) + 1}",
                        "category": "main",
                    }
                )

        logger.info(
            "Editor payload built: %d events, %d speakers",
            len(entries),
            len(speakers),
        )

        return {"transcript": entries, "speakers": speakers}

    # ─── Private Pipeline Steps ───────────────────────────────────

    def _run_asr(self, source: Path) -> TranscriptionResult:
        """Run ASR transcription."""
        logger.info("Stage 1: ASR transcription...")
        result = self.transcriber.transcribe(
            str(source),
            language=self.language,
            word_timestamps=True,
        )
        logger.info(
            "ASR complete: %d words in %.2fs",
            result.word_count,
            result.duration,
        )
        return result

    def _run_diarization(
        self,
        source: Path,
        min_speaker_duration: float,
    ) -> list:
        """Run speaker diarization."""
        logger.info("Stage 2: Speaker diarization (%s)...", self.diarize_backend)
        segments = self.diarizer.run(
            str(source),
            min_speaker_duration=min_speaker_duration,
        )
        speaker_count = len({seg.speaker_id for seg in segments})
        logger.info(
            "Diarization complete: %d segments, %d speakers",
            len(segments),
            speaker_count,
        )
        return segments

    def _match_speakers(
        self,
        words: list[Word],
        speaker_segments: list,
    ) -> list[Word]:
        """Match each word to the speaker segment with maximum overlap.

        Two-pointer sweep: words arrive in time order and segments are
        walked by start time, so each segment enters and leaves the
        candidate window at most once — O(n + m + k) overall (k = total
        candidate window size) instead of the naive O(n*m).

        Ties (equal overlap) go to the segment that appeared first in
        the input list. Words outside any speaker segment get
        speaker_id=None.
        """
        from engine.diarization.models import SpeakerSegment

        # (original_index, start, end, speaker_id), ordered by start
        intervals: list[tuple[int, float, float, str]] = [
            (i, seg.start, seg.end, seg.speaker_id)
            for i, seg in enumerate(speaker_segments)
            if isinstance(seg, SpeakerSegment)
        ]
        intervals.sort(key=lambda t: (t[1], t[0]))

        if not intervals:
            for word in words:
                word.speaker_id = None
            return words

        monotonic = all(a.start <= b.start for a, b in pairwise(words))

        def pick(candidates: list[tuple[int, float, float, str]], word: Word):
            best_speaker: str | None = None
            best_overlap = 0.0
            best_orig = len(intervals)
            for orig, s_start, s_end, speaker_id in candidates:
                overlap = min(word.end, s_end) - max(word.start, s_start)
                if overlap <= 0.0:
                    continue
                if overlap > best_overlap + 1e-9:
                    best_overlap = overlap
                    best_speaker = speaker_id
                    best_orig = orig
                elif abs(overlap - best_overlap) <= 1e-9 and orig < best_orig:
                    best_speaker = speaker_id
                    best_orig = orig
            return best_speaker

        attributed_words: list[Word] = []
        unmatched = 0
        left = 0   # first segment with end > current word.start
        right = 0  # first segment with start >= current word.end

        for word in words:
            if monotonic:
                while left < len(intervals) and intervals[left][2] <= word.start:
                    left += 1
                right = max(right, left)
                while (
                    right < len(intervals)
                    and intervals[right][1] < word.end
                ):
                    right += 1
                match = pick(intervals[left:right], word)
            else:
                # Out-of-order input: fall back to a full scan
                match = pick(intervals, word)

            word.speaker_id = match
            if match is None:
                unmatched += 1
            attributed_words.append(word)

        logger.info(
            "Speaker match: %d/%d attributed, %d unmatched",
            len(words) - unmatched,
            len(words),
            unmatched,
        )

        return attributed_words

    def get_status(self) -> dict:
        """Return pipeline configuration and load status."""
        return {
            "asr_model": self.asr_model,
            "asr_device": self.asr_device,
            "asr_compute_type": self.asr_compute_type,
            "diarize_backend": self.diarize_backend,
            "align_mode": self.align_mode,
            "language": self.language,
            "max_workers": self.max_workers,
            "correct_transcript": self.correct_transcript,
            "min_confidence": self.min_confidence,
            "asr_loaded": self._transcriber is not None and self._transcriber._initialized,
            "diarizer_loaded": self._diarizer is not None,
            "aligner_loaded": self._aligner is not None,
        }
