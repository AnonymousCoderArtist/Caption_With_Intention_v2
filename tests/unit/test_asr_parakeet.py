"""Parakeet ASR backend unit tests (model stubbed — no downloads)."""

from __future__ import annotations

import math
import sys
from types import SimpleNamespace

import pytest

from engine.asr.backends import (
    BACKEND_FASTER_WHISPER,
    BACKEND_PARAKEET,
    DEFAULT_MODELS,
    SUPPORTED_BACKENDS,
    create_asr_engine,
)
from engine.asr.models import Word
from engine.asr.parakeet import (
    DEFAULT_PARAKEET_MODEL,
    ParakeetTranscriber,
    tokens_to_words,
    words_to_segments,
)
from engine.asr.transcriber import Transcriber

# ─── Token → Word Grouping ─────────────────────────────────────


class TestTokensToWords:
    def test_basic_grouping(self):
        words = tokens_to_words(
            tokens=[" Hello", " world"],
            timestamps=[0.0, 0.5],
        )
        assert [w.text for w in words] == ["Hello", "world"]
        assert words[0].start == 0.0
        assert words[0].end == 0.5
        assert words[1].start == 0.5
        assert words[1].end == pytest.approx(0.51)

    def test_subword_tokens_merge(self):
        # "captioning" split into subwords; "?" continues the word.
        words = tokens_to_words(
            tokens=[" cap", "tion", "ing", "?"],
            timestamps=[0.0, 0.1, 0.2, 0.3],
        )
        assert len(words) == 1
        assert words[0].text == "captioning?"
        assert words[0].start == 0.0

    def test_confidence_from_logprobs(self):
        words = tokens_to_words(
            tokens=[" hi", " there"],
            timestamps=[0.0, 1.0],
            logprobs=[math.log(0.9), math.log(0.8)],
        )
        assert words[0].confidence == pytest.approx(0.9)
        assert words[1].confidence == pytest.approx(0.8)

    def test_no_logprobs_gives_zero_confidence(self):
        words = tokens_to_words([" hi"], [0.0])
        assert words[0].confidence == 0.0

    def test_empty_tokens(self):
        assert tokens_to_words([], []) == []

    def test_whitespace_only_tokens_dropped(self):
        words = tokens_to_words(["  ", " hello"], [0.0, 0.5])
        assert [w.text for w in words] == ["hello"]

    def test_word_end_never_before_start(self):
        # Degenerate duplicate timestamps still yield valid ranges.
        words = tokens_to_words([" a", " b"], [1.0, 1.0])
        assert all(w.end >= w.start for w in words)


# ─── Word → Segment Splitting ──────────────────────────────────


def _w(text: str, start: float, end: float) -> Word:
    return Word(text=text, start=start, end=end, confidence=0.9)


class TestWordsToSegments:
    def test_sentence_punctuation_splits(self):
        words = [_w("Hello.", 0.0, 0.4), _w("World", 0.5, 0.9)]
        segments = words_to_segments(words)
        assert len(segments) == 2
        assert segments[0].text == "Hello."
        assert segments[1].text == "World"

    def test_long_pause_splits(self):
        words = [_w("one", 0.0, 0.3), _w("two", 5.0, 5.3)]
        segments = words_to_segments(words)
        assert len(segments) == 2

    def test_short_pause_keeps_segment(self):
        words = [_w("one", 0.0, 0.3), _w("two", 0.6, 0.9)]
        segments = words_to_segments(words)
        assert len(segments) == 1
        assert segments[0].text == "one two"
        assert segments[0].start == 0.0
        assert segments[0].end == 0.9

    def test_empty(self):
        assert words_to_segments([]) == []


# ─── ParakeetTranscriber ───────────────────────────────────────


def _fake_onnx_asr():
    """A stub onnx_asr module with a scripted recognize() result."""

    class FakeModel:
        def __init__(self):
            self.load_args = None

        def with_timestamps(self):
            return self

        def recognize(self, path):
            return SimpleNamespace(
                text="Hello world.",
                tokens=[" Hello", " world", "."],
                timestamps=[0.0, 0.5, 0.8],
                logprobs=[-0.1, -0.2, -0.05],
            )

    fake = SimpleNamespace(load_model=lambda name, **kw: FakeModel())
    return fake


class TestParakeetTranscriber:
    def test_default_config(self):
        t = ParakeetTranscriber()
        assert t.model_name == DEFAULT_PARAKEET_MODEL
        assert t.device == "cpu"
        assert t.quantization is None
        assert t.language == "en"
        assert t._initialized is False

    def test_ignores_whisper_only_kwargs(self):
        t = ParakeetTranscriber(
            compute_type="int8", beam_size=5, vad_filter=True
        )
        assert "beam_size" not in t._kwargs
        assert "vad_filter" not in t._kwargs
        assert "compute_type" not in t._kwargs

    def test_get_model_info(self):
        info = ParakeetTranscriber().get_model_info()
        assert info["backend"] == "parakeet"
        assert info["model"] == DEFAULT_PARAKEET_MODEL
        assert info["initialized"] is False

    def test_missing_onnx_asr(self, monkeypatch):
        monkeypatch.setitem(sys.modules, "onnx_asr", None)
        t = ParakeetTranscriber()
        with pytest.raises(ImportError, match="onnx-asr"):
            t.transcribe("dummy.wav")

    def test_transcribe_with_stubbed_model(self, monkeypatch):
        monkeypatch.setitem(sys.modules, "onnx_asr", _fake_onnx_asr())
        t = ParakeetTranscriber()
        result = t.transcribe("dummy.wav")
        assert result.text == "Hello world."
        assert result.model == DEFAULT_PARAKEET_MODEL
        assert result.word_count == 2
        assert [w.text for w in result.words] == ["Hello", "world."]
        assert result.words[0].start == 0.0
        assert result.words[1].start == 0.5
        assert all(w.confidence > 0 for w in result.words)
        # Sentence-final "." keeps one segment here (single utterance)
        assert result.segment_count == 1
        assert result.duration > 0
        assert t._initialized is True

    def test_english_only_model_rejects_other_languages(self):
        t = ParakeetTranscriber(model="nemo-parakeet-tdt-0.6b-v2")
        with pytest.raises(ValueError, match="English-only"):
            t.transcribe("dummy.wav", language="hi")

    def test_load_passes_quantization_and_cuda(self, monkeypatch):
        captured = {}

        class FakeModel:
            def recognize(self, path):
                return SimpleNamespace(text="", tokens=[], timestamps=[])

            def with_timestamps(self):
                return self

        def fake_load(name, **kw):
            captured["name"] = name
            captured.update(kw)
            return FakeModel()

        monkeypatch.setitem(
            sys.modules, "onnx_asr", SimpleNamespace(load_model=fake_load)
        )
        t = ParakeetTranscriber(quantization="int8", device="cuda")
        t.transcribe("dummy.wav", word_timestamps=False)
        assert captured["name"] == DEFAULT_PARAKEET_MODEL
        assert captured["quantization"] == "int8"
        assert "CUDAExecutionProvider" in captured["providers"]


# ─── Backend Factory ───────────────────────────────────────────


class TestBackendFactory:
    def test_default_is_faster_whisper(self):
        engine = create_asr_engine()
        assert isinstance(engine, Transcriber)
        assert engine.model_name == "large-v3-turbo"

    def test_parakeet_backend(self):
        engine = create_asr_engine(backend=BACKEND_PARAKEET)
        assert isinstance(engine, ParakeetTranscriber)
        assert engine.model_name == DEFAULT_PARAKEET_MODEL

    def test_parakeet_int8_compute_type_maps_to_quantization(self):
        engine = create_asr_engine(
            backend=BACKEND_PARAKEET, compute_type="int8"
        )
        assert engine.quantization == "int8"

    def test_explicit_model_override(self):
        engine = create_asr_engine(
            backend=BACKEND_PARAKEET, model="nemo-parakeet-tdt-0.6b-v2"
        )
        assert engine.model_name == "nemo-parakeet-tdt-0.6b-v2"

    def test_unknown_backend_raises(self):
        with pytest.raises(ValueError, match="Unknown ASR backend"):
            create_asr_engine(backend="whisperx")

    def test_supported_backends_listed(self):
        assert BACKEND_FASTER_WHISPER in SUPPORTED_BACKENDS
        assert BACKEND_PARAKEET in SUPPORTED_BACKENDS
        assert set(DEFAULT_MODELS) == set(SUPPORTED_BACKENDS)


# ─── SpeechPipeline Wiring ─────────────────────────────────────


class TestSpeechPipelineBackend:
    def test_default_backend_unchanged(self):
        from engine.speech.pipeline import SpeechPipeline

        pipeline = SpeechPipeline()
        assert pipeline.asr_backend == BACKEND_FASTER_WHISPER
        assert isinstance(pipeline.transcriber, Transcriber)
        assert pipeline.transcriber.model_name == "large-v3-turbo"

    def test_parakeet_backend_selected(self):
        from engine.speech.pipeline import SpeechPipeline

        pipeline = SpeechPipeline(asr_backend="parakeet")
        assert isinstance(pipeline.transcriber, ParakeetTranscriber)
        # Whisper's default model must not leak into Parakeet
        assert pipeline.transcriber.model_name == DEFAULT_PARAKEET_MODEL
        # int8 default maps to the quantized ONNX variant
        assert pipeline.transcriber.quantization == "int8"

    def test_status_reports_backend(self):
        from engine.speech.pipeline import SpeechPipeline

        pipeline = SpeechPipeline(asr_backend="parakeet")
        assert pipeline.get_status()["asr_backend"] == "parakeet"
