"""Speaker diarization engine — PRIMARY speaker identification method.

Supports multiple backends (pluggable):
1. ``diarize`` (recommended) — ~4.8% DER, CPU-only, no API key, Apache 2.0.
   Install: ``pip install diarize``
2. ``pyannote.audio`` — SOTA open-source (~11% DER), needs HuggingFace token.
   Install: ``pip install pyannote.audio``
3. ``ffmpeg_vad`` (default fallback) — always available, no extra dependencies.

Per the Speaker Design Decision, audio diarization is PRIMARY.
Face tracking is used only as a fallback when confidence is low.

Usage:
    from engine.diarization.diarizer import Diarizer

    # Lightweight backend (recommended — user downloads model separately)
    diarizer = Diarizer(backend="diarize")

    # Pyannote backend (requires HF token)
    diarizer = Diarizer(backend="pyannote", token="hf_xxx")

    # Fallback (always works, lower accuracy)
    diarizer = Diarizer(backend="ffmpeg_vad")

    segments = diarizer.run("audio.wav")
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from engine.core.ffmpeg import run_ffmpeg
from engine.diarization.models import SpeakerSegment

logger = logging.getLogger("caption_with_intention")

DEFAULT_MIN_SPEAKER_DURATION = 0.5
DEFAULT_SPEAKER_CONFIDENCE = 0.5


class Diarizer:
    """Audio-based speaker diarization engine with pluggable backends.

    Args:
        backend: Diarization backend to use. Options:
            - ``"diarize"`` — Lightweight, CPU-only, ~4.8% DER (recommended)
            - ``"pyannote"`` — SOTA open-source, needs HuggingFace token
            - ``"ffmpeg_vad"`` — Fallback, always available (default)
        min_speaker_duration: Minimum duration for a speaker segment (seconds).
        min_confidence: Minimum confidence threshold for segments.
        token: HuggingFace access token (required for ``pyannote`` backend).
        **kwargs: Backend-specific configuration options.
    """

    def __init__(
        self,
        backend: str = "ffmpeg_vad",
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
        if self.backend == "diarize":
            return self._run_diarize(source_path, **kwargs)
        elif self.backend == "pyannote":
            return self._run_pyannote(source_path, **kwargs)
        else:
            return self._run_ffmpeg_vad(source_path, **kwargs)

    def _run_diarize(self, source_path: str, **kwargs: Any) -> list[SpeakerSegment]:
        """Run diarize backend (~4.8% DER, CPU-only, Apache 2.0).

        Requires: ``pip install diarize`` (user downloads model separately).
        Pipeline: Silero VAD → WeSpeaker embeddings → GMM BIC → Spectral Clustering.

        Args:
            source_path: Path to audio file (wav, mp3, flac supported).
            **kwargs: Passed to diarize.pipeline (num_speakers, etc.).

        Returns:
            List of SpeakerSegment objects.
        """
        try:
            from diarize import diarize as _diarize
            from diarize.pipeline import DiarizeResult
        except ImportError:
            logger.warning(
                "diarize not installed. Falling back to FFmpeg VAD. "
                "Install with: pip install diarize"
            )
            return self._run_ffmpeg_vad(source_path, **kwargs)

        result: DiarizeResult = _diarize(source_path, **kwargs)
        segments: list[SpeakerSegment] = []
        for seg in result.segments:
            segments.append(
                SpeakerSegment(
                    speaker_id=seg.speaker,
                    start=seg.start,
                    end=seg.end,
                    confidence=1.0,  # diarize doesn't expose per-segment confidence
                    source="diarize",
                )
            )
        return segments

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
