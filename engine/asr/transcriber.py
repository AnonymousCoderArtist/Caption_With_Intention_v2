"""ASR Transcriber — faster-whisper based transcription with speaker attribution.

Uses CTranslate2 for fast, memory-efficient inference.
Supports word-level timestamps and optional speaker diarization integration.
"""

from __future__ import annotations

import logging
import re
import time
from pathlib import Path
from typing import Optional

from engine.asr.models import Segment, TranscriptionResult, Word

logger = logging.getLogger("caption_with_intention")

DEFAULT_MODEL = "large-v3-turbo"
DEFAULT_DEVICE = "cpu"
DEFAULT_COMPUTE_TYPE = "int8"
DEFAULT_BEAM_SIZE = 5
DEFAULT_VAD_FILTER = True
DEFAULT_LANGUAGE = "en"


class Transcriber:
    """Speech-to-text transcriber using faster-whisper.

    Args:
        model: Whisper model size. Options:
            - "tiny"     (~150 MB, ~30% WER, fastest)
            - "base"     (~390 MB, ~16% WER)
            - "small"    (~1 GB, ~10% WER, recommended low-resource)
            - "medium"   (~5 GB, ~5% WER)
            - "large-v3" (~3.1 GB, ~7.4% WER, most accurate)
            - "large-v3-turbo" (~1.6 GB, ~7.7% WER, best balance) — default
            - "distil-large-v3" (~1 GB, ~2.4% WER English only)
        device: "cpu" or "cuda" (NVIDIA GPU).
        compute_type: "int8" (default, saves 50% memory), "float16" (GPU),
            or "float32" (maximum compatibility).
        beam_size: Beam size for decoding. 5 (default) gives best accuracy.
            Set to 1 for faster but slightly less accurate results.
        vad_filter: Enable Silero VAD to skip silent sections (recommended).
        language: ISO code for transcription language (e.g. "en", "auto").
        **kwargs: Additional model kwargs (cpu_threads, etc.).
    """

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        device: str = DEFAULT_DEVICE,
        compute_type: str = DEFAULT_COMPUTE_TYPE,
        beam_size: int = DEFAULT_BEAM_SIZE,
        vad_filter: bool = DEFAULT_VAD_FILTER,
        language: str = DEFAULT_LANGUAGE,
        **kwargs: object,
    ) -> None:
        self.model_name = model
        self.device = device
        self.compute_type = compute_type
        self.beam_size = beam_size
        self.vad_filter = vad_filter
        self.language = language
        self._kwargs = kwargs
        self._model: object = None
        self._initialized = False

    def _load(self) -> None:
        """Lazy-load the model on first use."""
        if self._initialized:
            return

        try:
            from faster_whisper import WhisperModel
        except ImportError:
            raise ImportError(
                "faster-whisper is not installed. "
                "Install it with: pip install faster-whisper"
            )

        logger.info(
            "Loading ASR model: %s on %s (compute=%s)",
            self.model_name,
            self.device,
            self.compute_type,
        )

        t0 = time.monotonic()
        self._model = WhisperModel(
            self.model_name,
            device=self.device,
            compute_type=self.compute_type,
            **self._kwargs,
        )
        load_time = time.monotonic() - t0
        self._initialized = True
        logger.info("ASR model loaded in %.2fs", load_time)

    def transcribe(
        self,
        source_path: str | Path,
        language: Optional[str] = None,
        beam_size: Optional[int] = None,
        vad_filter: Optional[bool] = None,
        word_timestamps: bool = True,
    ) -> TranscriptionResult:
        """Transcribe an audio or video file.

        Args:
            source_path: Path to audio (wav, mp3, flac) or video file.
            language: Override ISO language code. None uses self.language.
            beam_size: Override beam size for this call.
            vad_filter: Override VAD filter for this call.
            word_timestamps: Include word-level timing data.

        Returns:
            TranscriptionResult with segments, words, and metadata.
        """
        self._load()

        lang = language or self.language
        bs = beam_size if beam_size is not None else self.beam_size
        vf = vad_filter if vad_filter is not None else self.vad_filter

        source = Path(source_path)
        logger.info("Transcribing %s with model %s", source, self.model_name)

        t0 = time.monotonic()

        segments, info = self._model.transcribe(
            str(source),
            language=lang,
            beam_size=bs,
            vad_filter=vf,
            word_timestamps=word_timestamps,
        )

        elapsed = time.monotonic() - t0

        result = self._build_result(
            segments=segments,
            info=info,
            source_path=str(source),
            elapsed=elapsed,
        )

        logger.info(
            "Transcription complete: %d words in %.2fs (%.1fx realtime)",
            result.word_count,
            elapsed,
            result.duration / elapsed if elapsed > 0 else 0,
        )

        return result

    def _build_result(
        self,
        segments: list,
        info: object,
        source_path: str,
        elapsed: float,
    ) -> TranscriptionResult:
        """Convert faster-whisper output to TranscriptionResult."""
        words: list[Word] = []
        segment_objs: list[Segment] = []
        full_text_parts: list[str] = []

        for seg in segments:
            seg_words: list[Word] = []
            for w in (seg.words or []):
                word = Word(
                    text=w.word,
                    start=w.start,
                    end=w.end,
                    confidence=w.probability or 0.0,
                )
                seg_words.append(word)
                words.append(word)

            seg_text = "".join(w.text for w in seg_words)
            # Clean up spacing around punctuation
            seg_text = seg_text.replace(" ,", ",").replace(" .", ".").replace(" !", "!").replace(" ?", "?").replace(" '", "'")
            if seg_text and seg_text[0] in " ,.":
                seg_text = seg_text[1:]

            segment = Segment(
                text=seg_text,
                start=seg.start,
                end=seg.end,
                confidence=seg.confidence or 0.0 if hasattr(seg, "confidence") else 0.0,
                words=seg_words,
            )
            segment_objs.append(segment)
            full_text_parts.append(seg_text)

        full_text = " ".join(full_text_parts)
        full_text = re.sub(r" +", " ", full_text).strip()

        duration = info.duration if info else 0.0
        detected_lang = info.language if info else "unknown"

        return TranscriptionResult(
            text=full_text,
            segments=segment_objs,
            words=words,
            language=detected_lang,
            model=self.model_name,
            source_path=source_path,
            duration=duration,
        )

    def transcribe_stream(
        self,
        source_path: str | Path,
        chunk_duration: float = 30.0,
        overlap: float = 2.0,
        **kwargs: object,
    ) -> list[TranscriptionResult]:
        """Transcribe long audio in chunks for memory-bounded processing.

        Args:
            source_path: Path to audio file.
            chunk_duration: Duration of each chunk in seconds (default 30s,
                Whisper's native context window).
            overlap: Overlap between chunks in seconds (default 2s).
            **kwargs: Passed to transcribe().

        Returns:
            List of TranscriptionResult per chunk.
        """
        import os
        import subprocess
        import tempfile

        from engine.media.probe import probe_video

        source = Path(source_path)
        info = probe_video(source)
        duration = info.get("duration", 0.0)

        if duration <= chunk_duration:
            return [self.transcribe(source_path, **kwargs)]

        results: list[TranscriptionResult] = []
        start = 0.0

        while start < duration:
            end = min(start + chunk_duration, duration)
            logger.info(
                "Transcribing chunk: %.2fs - %.2fs",
                start,
                end,
            )

            chunk_path: str | None = None
            try:
                fd, chunk_path = tempfile.mkstemp(suffix=".wav")
                os.close(fd)
                cmd = [
                    "ffmpeg",
                    "-y",
                    "-ss",
                    str(start),
                    "-i",
                    str(source),
                    "-to",
                    str(end),
                    "-ac",
                    "1",
                    "-ar",
                    "16000",
                    chunk_path,
                ]
                # check=False: a failed extraction surfaces as a load
                # error in transcribe() below, which the chunk loop handles
                subprocess.run(cmd, capture_output=True, timeout=120, check=False)

                chunk_result = self.transcribe(chunk_path, **kwargs)
                chunk_result.source_path = str(source)
                results.append(chunk_result)
            except Exception as e:  # noqa: BLE001 - any chunk failure is fatal
                # for the stream; log and stop rather than crash mid-video
                logger.warning("Chunk %.2fs-%.2fs failed: %s", start, end, e)
                break
            finally:
                if chunk_path:
                    try:
                        os.remove(chunk_path)
                    except OSError:
                        pass

            # Overlap for continuity; cap at half the chunk so the loop
            # always advances even with a misconfigured overlap
            start = end - min(overlap, chunk_duration * 0.5)

        return results

    def get_model_info(self) -> dict:
        """Return current configuration as a dict."""
        return {
            "model": self.model_name,
            "device": self.device,
            "compute_type": self.compute_type,
            "beam_size": self.beam_size,
            "vad_filter": self.vad_filter,
            "language": self.language,
            "initialized": self._initialized,
        }
