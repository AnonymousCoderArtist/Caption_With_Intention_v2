"""ASR Parakeet backend — NVIDIA Parakeet TDT via onnx-asr (CPU-first).

NVIDIA Parakeet TDT 0.6B transcribes at roughly 40x realtime on a
desktop CPU and emits token-level timestamps (see docs/ASR_BACKENDS.md
for the benchmark sources), so it is the recommended backend for
low-resource machines. faster-whisper stays available for GPU or
maximum-accuracy runs.

Model options (onnx-asr model names):
    nemo-parakeet-tdt-0.6b-v3  (default; 25 European languages,
                                punctuation + capitalization)
    nemo-parakeet-tdt-0.6b-v2  (English-only; slightly better English
                                accuracy than v3 on VoxPopuli)
    nemo-parakeet-rnnt-0.6b    (English; older generation)
    nemo-canary-1b-v2          (multilingual; much slower on CPU)

Whisper-only options (beam_size, vad_filter, compute_type) are accepted
and ignored so backends are interchangeable through the factory.
"""

from __future__ import annotations

import logging
import math
import time
from collections.abc import Sequence
from pathlib import Path
from typing import Optional

from engine.asr.models import Segment, TranscriptionResult, Word

logger = logging.getLogger("caption_with_intention")

DEFAULT_PARAKEET_MODEL = "nemo-parakeet-tdt-0.6b-v3"
ENGLISH_ONLY_MODELS = ("nemo-parakeet-tdt-0.6b-v2", "nemo-parakeet-rnnt-0.6b")
DEFAULT_LANGUAGE = "en"

# onnx-asr normalizes the SentencePiece word-start marker to a plain
# space, so a token starting with " " starts a new word.
WORD_PREFIX = " "
# A pause longer than this (seconds) starts a new caption segment.
SEGMENT_PAUSE = 1.5
# onnx-asr emits one timestamp per 10 ms output window; used to give the
# final token of the final word a small positive duration.
TOKEN_WINDOW = 0.01
# Sentence-final punctuation also closes a segment even without a pause.
SENTENCE_END = (".", "!", "?")


def tokens_to_words(
    tokens: Sequence[str],
    timestamps: Sequence[float],
    logprobs: Optional[Sequence[float]] = None,
) -> list[Word]:
    """Group Parakeet tokens into words with timing and confidence.

    A token starting with WORD_PREFIX (a space) begins a new word. Each
    word runs from its first token's timestamp to the next word's first
    token timestamp. Word confidence is the geometric mean of the token
    probabilities (exp of mean logprob); 0.0 when logprobs are absent.
    """
    words: list[Word] = []
    buf: list[str] = []
    buf_start = 0.0
    buf_logprobs: list[float] = []

    def flush(end: float) -> None:
        nonlocal buf, buf_start, buf_logprobs
        text = "".join(buf).strip()
        if text:
            confidence = (
                math.exp(sum(buf_logprobs) / len(buf_logprobs))
                if buf_logprobs
                else 0.0
            )
            words.append(
                Word(
                    text=text,
                    start=buf_start,
                    end=max(end, buf_start),
                    confidence=min(confidence, 1.0),
                )
            )
        buf, buf_logprobs = [], []

    for i, token in enumerate(tokens):
        ts = (
            float(timestamps[i])
            if i < len(timestamps)
            else (words[-1].end if words else 0.0)
        )
        if token.startswith(WORD_PREFIX) and buf:
            flush(ts)
        if not buf:
            buf_start = ts
        buf.append(token)
        if logprobs is not None and i < len(logprobs):
            buf_logprobs.append(float(logprobs[i]))

    end = float(timestamps[-1]) + TOKEN_WINDOW if timestamps else 0.0
    flush(end)
    return words


def _make_segment(words: list[Word]) -> Segment:
    """Build a Segment from a contiguous run of words."""
    text = " ".join(w.text for w in words)
    confidences = [w.confidence for w in words if w.confidence > 0]
    return Segment(
        text=text,
        start=words[0].start,
        end=words[-1].end,
        confidence=(
            sum(confidences) / len(confidences) if confidences else 0.0
        ),
        words=list(words),
    )


def words_to_segments(
    words: Sequence[Word],
    max_pause: float = SEGMENT_PAUSE,
) -> list[Segment]:
    """Split a word list into caption segments.

    A new segment starts after a pause longer than max_pause or after
    sentence-final punctuation, whichever comes first. This mirrors the
    captioning convention of one utterance per caption event.
    """
    segments: list[Segment] = []
    current: list[Word] = []
    for word in words:
        if current:
            prev = current[-1]
            if (
                word.start - prev.end > max_pause
                or prev.text.endswith(SENTENCE_END)
            ):
                segments.append(_make_segment(current))
                current = []
        current.append(word)
    if current:
        segments.append(_make_segment(current))
    return segments


class ParakeetTranscriber:
    """Speech-to-text transcriber using NVIDIA Parakeet via onnx-asr.

    Interface-compatible with engine.asr.transcriber.Transcriber so the
    speech pipeline can swap backends without code changes.

    Args:
        model: onnx-asr model name (see module docstring).
        quantization: None for the full-precision ONNX export, or "int8"
            for the quantized variant (roughly half the memory).
        device: "cpu" (default) or "cuda" (uses onnxruntime's CUDA
            execution provider when onnxruntime-gpu is installed).
        language: ISO code; v2/RNN-T models are English-only and raise
            ValueError for other languages at transcribe() time.
        **kwargs: Extra options passed to onnx_asr.load_model()
            (e.g. providers). Whisper-only options are ignored.
    """

    def __init__(
        self,
        model: str = DEFAULT_PARAKEET_MODEL,
        quantization: Optional[str] = None,
        device: str = "cpu",
        language: str = DEFAULT_LANGUAGE,
        **kwargs: object,
    ) -> None:
        ignored = [
            k for k in ("compute_type", "beam_size", "vad_filter") if k in kwargs
        ]
        for key in ignored:
            kwargs.pop(key)
        if ignored:
            logger.debug(
                "Parakeet backend ignoring Whisper-only options: %s",
                ", ".join(ignored),
            )
        self.model_name = model
        self.quantization = quantization
        self.device = device
        self.language = language
        self._kwargs = kwargs
        self._model: object = None
        self._ts_model: object = None
        self._initialized = False

    def _load(self) -> None:
        """Lazy-load the ONNX model on first use."""
        if self._initialized:
            return

        try:
            import onnx_asr
        except ImportError:
            raise ImportError(
                "onnx-asr is not installed. "
                "Install it with: pip install onnx-asr "
                "(or: uv sync --extra parakeet)"
            )

        options: dict = dict(self._kwargs)
        if self.quantization:
            options["quantization"] = self.quantization
        if self.device == "cuda":
            options["providers"] = [
                "CUDAExecutionProvider",
                "CPUExecutionProvider",
            ]

        logger.info(
            "Loading Parakeet model: %s on %s (quantization=%s)",
            self.model_name,
            self.device,
            self.quantization or "none",
        )
        t0 = time.monotonic()
        self._model = onnx_asr.load_model(self.model_name, **options)
        self._initialized = True
        logger.info("Parakeet model loaded in %.2fs", time.monotonic() - t0)

    def _timestamped_model(self) -> object:
        """Return the timestamped wrapper, loading the model if needed."""
        self._load()
        if self._ts_model is None:
            self._ts_model = self._model.with_timestamps()  # type: ignore[union-attr]
        return self._ts_model

    def transcribe(
        self,
        source_path: str | Path,
        language: Optional[str] = None,
        word_timestamps: bool = True,
        **_ignored: object,
    ) -> TranscriptionResult:
        """Transcribe an audio or video file.

        Args:
            source_path: Path to a WAV file (PCM_U8/16/24/32). For video
                or other containers, use transcribe_stream() or extract
                audio with ffmpeg first.
            language: Override ISO language code. None uses self.language.
                English-only models raise ValueError for other languages.
            word_timestamps: Include word-level timing data (uses the
                onnx-asr timestamped wrapper).

        Returns:
            TranscriptionResult with segments, words, and metadata.
        """
        lang = language or self.language
        if (
            self.model_name in ENGLISH_ONLY_MODELS
            and lang not in ("en", "auto")
        ):
            raise ValueError(
                f"{self.model_name} is English-only; got language={lang!r}. "
                "Use nemo-parakeet-tdt-0.6b-v3 for multilingual audio."
            )

        model = (
            self._timestamped_model() if word_timestamps else self._load_model_plain()
        )

        source = Path(source_path)
        logger.info("Transcribing %s with %s", source, self.model_name)
        t0 = time.monotonic()
        raw = model.recognize(str(source))
        elapsed = time.monotonic() - t0

        tokens = list(getattr(raw, "tokens", None) or [])
        timestamps = [float(t) for t in (getattr(raw, "timestamps", None) or [])]
        logprobs = getattr(raw, "logprobs", None)

        words = tokens_to_words(tokens, timestamps, logprobs) if tokens else []
        text = (getattr(raw, "text", "") or "").strip()
        if not words and text:
            # Backend returned plain text only: no timing data available.
            words = [Word(text=text, start=0.0, end=0.0)]
        segments = words_to_segments(words)
        duration = words[-1].end if words else 0.0

        logger.info(
            "Transcription complete: %d words in %.2fs (%.1fx realtime)",
            len(words),
            elapsed,
            duration / elapsed if elapsed > 0 else 0,
        )

        return TranscriptionResult(
            text=text or " ".join(w.text for w in words),
            segments=segments,
            words=words,
            language="en" if self.model_name in ENGLISH_ONLY_MODELS else lang,
            model=self.model_name,
            source_path=str(source),
            duration=duration,
        )

    def _load_model_plain(self) -> object:
        """Load (if needed) and return the non-timestamped model."""
        self._load()
        return self._model

    def transcribe_stream(
        self,
        source_path: str | Path,
        chunk_duration: float = 30.0,
        overlap: float = 2.0,
        **kwargs: object,
    ) -> list[TranscriptionResult]:
        """Transcribe long audio in chunks for memory-bounded processing.

        Chunks are extracted to16kHz mono WAV. Both recognition backends
        return source-timeline word and segment times. Overlap words are
        retained for later reconciliation, not safe to concatenate blindly.

        Args:
            source_path: Path to audio or video file.
            chunk_duration: Duration of each chunk in seconds.
            overlap: Overlap between chunks in seconds.
            **kwargs: Passed to transcribe().

        Returns:
            List of TranscriptionResult per chunk (source-timeline times).
        """
        from engine.asr.longform import transcribe_chunks

        return transcribe_chunks(self, source_path, chunk_duration, overlap, **kwargs)

    def get_model_info(self) -> dict:
        """Return current configuration as a dict."""
        return {
            "backend": "parakeet",
            "model": self.model_name,
            "quantization": self.quantization,
            "device": self.device,
            "language": self.language,
            "initialized": self._initialized,
        }
