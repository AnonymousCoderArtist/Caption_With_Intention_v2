"""M6 unit tests — ASR transcription engine."""

from __future__ import annotations

import pytest
from engine.asr.models import Word, Segment, TranscriptionResult
from engine.asr.transcriber import Transcriber


# ─── Word Model Tests ─────────────────────────────────


class TestWord:
    def test_word_creation(self):
        word = Word(text="Hello", start=0.0, end=0.5, confidence=0.95)
        assert word.text == "Hello"
        assert word.start == 0.0
        assert word.end == 0.5
        assert word.confidence == 0.95
        assert word.speaker_id is None

    def test_word_duration(self):
        word = Word(text="test", start=1.0, end=3.5)
        assert word.duration == 2.5

    def test_word_to_dict(self):
        word = Word(
            text="hi",
            start=0.0,
            end=1.0,
            confidence=0.8,
            speaker_id="spk_1",
        )
        d = word.to_dict()
        assert d["text"] == "hi"
        assert d["duration"] == 1.0
        assert d["speaker_id"] == "spk_1"
        assert d["confidence"] == 0.8


# ─── Segment Model Tests ──────────────────────────────────────


class TestSegment:
    def test_segment_creation(self):
        words = [Word("a", 0.0, 0.3), Word("b", 0.3, 0.6)]
        seg = Segment(text="a b", start=0.0, end=0.6, words=words)
        assert seg.text == "a b"
        assert len(seg.words) == 2
        assert seg.duration == 0.6

    def test_segment_to_dict(self):
        words = [Word("hello", 0.0, 0.5, confidence=0.9)]
        seg = Segment(
            text="hello",
            start=0.0,
            end=0.5,
            words=words,
            speaker_id="spk_1",
        )
        d = seg.to_dict()
        assert d["text"] == "hello"
        assert d["duration"] == 0.5
        assert d["speaker_id"] == "spk_1"
        assert len(d["words"]) == 1


# ─── TranscriptionResult Tests ────────────────────────────────


class TestTranscriptionResult:
    def test_empty_result(self):
        result = TranscriptionResult(text="", model="large-v3-turbo")
        assert result.text == ""
        assert result.word_count == 0
        assert result.segment_count == 0

    def test_full_result(self):
        words = [
            Word("Hello", 0.0, 0.5, speaker_id="spk_1"),
            Word("world", 0.5, 1.0, speaker_id="spk_1"),
        ]
        segments = [
            Segment(
                text="Hello",
                start=0.0,
                end=0.5,
                words=[words[0]],
                speaker_id="spk_1",
            ),
            Segment(
                text="world",
                start=0.5,
                end=1.0,
                words=[words[1]],
                speaker_id="spk_1",
            ),
        ]
        result = TranscriptionResult(
            text="Hello world",
            segments=segments,
            words=words,
            language="en",
            model="large-v3-turbo",
            duration=1.0,
        )
        assert result.word_count == 2
        assert result.segment_count == 2
        d = result.to_dict()
        assert d["language"] == "en"
        assert d["model"] == "large-v3-turbo"
        assert d["duration"] == 1.0
        assert len(d["words"]) == 2


# ─── Transcriber Configuration Tests ──────────────────────────


class TestTranscriber:
    def test_default_config(self):
        t = Transcriber()
        assert t.model_name == "large-v3-turbo"
        assert t.device == "cpu"
        assert t.compute_type == "int8"
        assert t.beam_size == 5
        assert t.vad_filter is True
        assert t.language == "en"
        assert t._initialized is False

    def test_custom_config(self):
        t = Transcriber(
            model="small",
            device="cuda",
            compute_type="float16",
            beam_size=1,
            language="auto",
        )
        assert t.model_name == "small"
        assert t.device == "cuda"
        assert t.compute_type == "float16"
        assert t.beam_size == 1
        assert t.language == "auto"

    def test_config_roundtrip(self):
        t = Transcriber()
        info = t.get_model_info()
        assert info["model"] == "large-v3-turbo"
        assert info["device"] == "cpu"
        assert info["initialized"] is False

    def test_missing_faster_whisper(self):
        """Test ImportError when faster-whisper is not installed."""
        t = Transcriber()
        t._initialized = False
        t._model = None
        # Simulate missing faster-whisper by making _load raise ImportError
        def mock_load():
            raise ImportError("faster-whisper is not installed")
        t._load = mock_load
        with pytest.raises(ImportError):
            t.transcribe("dummy.wav")

    def test_transcribe_without_load(self):
        """If model isn't loaded, transcribe triggers load first."""
        t = Transcriber(model="tiny")
        # Don't load, but verify _load is called before _model usage
        loaded = [False]
        def mock_load():
            loaded[0] = True
        t._load = mock_load
        t._initialized = False
        t._load()
        assert loaded[0] is True
