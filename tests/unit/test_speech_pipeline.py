"""Speech pipeline tests."""

from __future__ import annotations

import pytest

from engine.asr.models import Segment, TranscriptionResult, Word
from engine.diarization.models import SpeakerSegment
from engine.speech.pipeline import SpeechPipeline


class TestSpeechPipeline:
    def test_default_config(self):
        pipeline = SpeechPipeline()
        assert pipeline.asr_model == "large-v3-turbo"
        assert pipeline.asr_device == "cpu"
        assert pipeline.diarize_backend == "nemotron"
        assert pipeline.align_mode == "vad_refinement"
        assert pipeline.language == "en"

    def test_custom_config(self):
        pipeline = SpeechPipeline(
            asr_model="small",
            asr_device="cuda",
            diarize_backend="pyannote",
            align_mode="forced",
            language="auto",
        )
        assert pipeline.asr_model == "small"
        assert pipeline.asr_device == "cuda"
        assert pipeline.diarize_backend == "pyannote"
        assert pipeline.align_mode == "forced"
        assert pipeline.language == "auto"

    def test_speaker_matching(self):
        """Test that words are correctly matched to speakers."""
        pipeline = SpeechPipeline()

        words = [
            Word("hello", 0.0, 0.5, confidence=0.9),
            Word("world", 0.5, 1.0, confidence=0.85),
            Word("test", 1.0, 1.5, confidence=0.9),
        ]

        segments = [
            SpeakerSegment(
                speaker_id="spk_1",
                start=0.0,
                end=0.7,
                confidence=0.9,
            ),
            SpeakerSegment(
                speaker_id="spk_2",
                start=0.8,
                end=1.5,
                confidence=0.8,
            ),
        ]

        result = pipeline._match_speakers(words, segments)

        # hello (0.0-0.5) overlaps with spk_1 (0.0-0.7)
        assert result[0].speaker_id == "spk_1"
        # world (0.5-1.0) overlaps with both spk_1 (0.0-0.7) and spk_2 (0.8-1.5)
        # overlap with spk_1 = 0.2, overlap with spk_2 = 0.2 → tie, first match
        assert result[1].speaker_id in ["spk_1", "spk_2"]
        # test (1.0-1.5) overlaps with spk_2 (0.8-1.5)
        assert result[2].speaker_id == "spk_2"

    def test_speaker_matching_no_overlap(self):
        """Words with no speaker coverage get None."""
        pipeline = SpeechPipeline()

        words = [
            Word("hello", 0.0, 0.5),
        ]

        segments = [
            SpeakerSegment(
                speaker_id="spk_1",
                start=1.0,  # After the word
                end=2.0,
                confidence=0.9,
            ),
        ]

        result = pipeline._match_speakers(words, segments)
        assert result[0].speaker_id is None

    def test_speaker_matching_empty_segments(self):
        """No speakers = all words unmatched."""
        pipeline = SpeechPipeline()
        words = [Word("hello", 0.0, 0.5)]
        result = pipeline._match_speakers(words, [])
        assert result[0].speaker_id is None

    def test_get_status(self):
        pipeline = SpeechPipeline()
        status = pipeline.get_status()
        assert status["asr_model"] == "large-v3-turbo"
        assert status["diarize_backend"] == "nemotron"
        assert status["asr_loaded"] is False
        assert "aligner_loaded" in status

    def test_speaker_matching_exact(self):
        """Perfect overlap should match."""
        pipeline = SpeechPipeline()
        words = [Word("test", 0.0, 1.0)]
        segments = [SpeakerSegment("spk_A", 0.0, 1.0, confidence=0.95)]
        result = pipeline._match_speakers(words, segments)
        assert result[0].speaker_id == "spk_A"


def _fake_pipeline_result() -> dict:
    """A realistic run() result without needing whisper."""
    w1 = Word("hello", 0.0, 0.4, confidence=0.9, speaker_id="spk_1")
    w2 = Word("world", 0.4, 0.9, confidence=0.85, speaker_id="spk_1")
    w3 = Word("goodbye", 1.0, 1.8, confidence=0.95, speaker_id="spk_2")
    transcription = TranscriptionResult(
        text="hello world. goodbye.",
        segments=[
            Segment("hello world.", 0.0, 1.0, confidence=0.9, words=[w1, w2]),
            Segment("goodbye.", 1.0, 2.0, confidence=0.8, words=[w3]),
        ],
        words=[w1, w2, w3],
        language="en",
        model="large-v3-turbo",
        source_path="audio.wav",
        duration=2.0,
    )
    return {
        "transcription": transcription,
        "diarization_segments": [
            {"speaker_id": "spk_1", "start": 0.0, "end": 1.0},
            {"speaker_id": "spk_2", "start": 1.0, "end": 2.0},
        ],
        "speaker_count": 2,
        "asr_model": "large-v3-turbo",
        "diarize_backend": "nemotron",
        "words_attributed": 3,
        "corrections": None,
    }


class TestBuildEditorPayload:
    def test_payload_shape(self):
        pipeline = SpeechPipeline()
        payload = pipeline.build_editor_payload(_fake_pipeline_result())
        assert len(payload["transcript"]) == 2
        assert [s["id"] for s in payload["speakers"]] == ["spk_1", "spk_2"]

    def test_precise_word_timing_preserved(self):
        pipeline = SpeechPipeline()
        payload = pipeline.build_editor_payload(_fake_pipeline_result())
        entry = payload["transcript"][0]
        words = entry["words"]
        assert [(w["text"], w["start"], w["end"]) for w in words] == [
            ("hello", 0.0, 0.4),
            ("world", 0.4, 0.9),
        ]
        # Provenance on every word (spec §2.2)
        for w in words:
            assert w["source_model"] == "large-v3-turbo"
            assert w["source_timestamp"] == w["start"]
            assert w["confidence"] is not None

    def test_event_metadata(self):
        pipeline = SpeechPipeline()
        payload = pipeline.build_editor_payload(_fake_pipeline_result())
        entry = payload["transcript"][0]
        assert entry["text"] == "hello world."
        assert entry["start"] == 0.0
        assert entry["end"] == 1.0
        assert entry["speaker_id"] == "spk_1"
        assert entry["source_model"] == "large-v3-turbo"
        assert entry["confidence"] == pytest.approx(0.875)  # mean(0.9, 0.85)

    def test_unknown_speaker_backfilled(self):
        """Event speaker ids not in diarization get a speaker entry."""
        pipeline = SpeechPipeline()
        result = _fake_pipeline_result()
        del result["diarization_segments"]
        payload = pipeline.build_editor_payload(result)
        assert [s["id"] for s in payload["speakers"]] == ["spk_1", "spk_2"]

    def test_empty_result(self):
        pipeline = SpeechPipeline()
        payload = pipeline.build_editor_payload(
            {
                "transcription": TranscriptionResult(text=""),
                "diarization_segments": [],
            }
        )
        assert payload["transcript"] == []
        assert payload["speakers"] == []


class TestCorrectionInRun:
    def test_run_applies_correction(self, monkeypatch):
        """run() collapses ASR stutter and reports corrections."""
        pipeline = SpeechPipeline()
        asr_result = TranscriptionResult(
            text="the the the",
            segments=[
                Segment(
                    "the the the",
                    0.0,
                    1.0,
                    words=[
                        Word("the", 0.0, 0.3, confidence=0.9),
                        Word("the", 0.3, 0.6, confidence=0.9),
                        Word("the", 0.6, 0.9, confidence=0.9),
                    ],
                )
            ],
            words=[
                Word("the", 0.0, 0.3, confidence=0.9),
                Word("the", 0.3, 0.6, confidence=0.9),
                Word("the", 0.6, 0.9, confidence=0.9),
            ],
            language="en",
            model="tiny",
            source_path="audio.wav",
            duration=1.0,
        )
        monkeypatch.setattr(pipeline, "_run_asr", lambda source: asr_result)
        monkeypatch.setattr(
            pipeline,
            "_run_diarization",
            lambda source, min_speaker_duration: [],
        )

        result = pipeline.run("audio.wav")

        assert [w.text for w in result["transcription"].words] == ["the"]
        assert result["corrections"] is not None
        assert result["corrections"]["summary"]["removed"] == 2
        assert result["transcription"].text == "the"

    def test_correction_disabled(self, monkeypatch):
        pipeline = SpeechPipeline(correct_transcript=False)
        words = [
            Word("the", 0.0, 0.3, confidence=0.9),
            Word("the", 0.3, 0.6, confidence=0.9),
        ]
        asr_result = TranscriptionResult(
            text="the the",
            segments=[],
            words=words,
            language="en",
            model="tiny",
            source_path="audio.wav",
            duration=0.6,
        )
        monkeypatch.setattr(pipeline, "_run_asr", lambda source: asr_result)
        monkeypatch.setattr(
            pipeline,
            "_run_diarization",
            lambda source, min_speaker_duration: [],
        )

        result = pipeline.run("audio.wav")
        assert [w.text for w in result["transcription"].words] == ["the", "the"]
        assert result["corrections"] is None

    def test_correction_config(self):
        pipeline = SpeechPipeline(min_confidence=0.7)
        assert pipeline.correct_transcript is True
        assert pipeline.min_confidence == 0.7
        status = pipeline.get_status()
        assert status["correct_transcript"] is True
        assert status["min_confidence"] == 0.7

    def test_speaker_matching_matches_bruteforce(self, monkeypatch):
        """The O(n+m) two-pointer sweep must match the naive O(n*m)
        reference (max overlap; ties go to the earliest segment)."""
        import random

        from engine.asr.models import Word as W

        rng = random.Random(42)
        words = [
            W(f"w{i}", round(rng.uniform(0, 30), 3), 0, confidence=0.9)
            for i in range(200)
        ]
        for w in words:
            w.end = w.start + rng.uniform(0.1, 0.9)
        words.sort(key=lambda w: w.start)

        segments = [
            SpeakerSegment(
                speaker_id=f"spk_{rng.randint(1, 5)}",
                start=round(rng.uniform(0, 28), 3),
                end=0,
                confidence=0.9,
            )
            for _ in range(40)
        ]
        for s in segments:
            s.end = s.start + rng.uniform(0.5, 4.0)

        # Naive O(n*m) reference
        expected = []
        for word in words:
            best, best_overlap, best_i = None, 0.0, len(segments)
            for i, seg in enumerate(segments):
                overlap = min(word.end, seg.end) - max(word.start, seg.start)
                if overlap > 0 and (
                    overlap > best_overlap + 1e-9
                    or (abs(overlap - best_overlap) <= 1e-9 and i < best_i)
                ):
                    best, best_overlap, best_i = seg.speaker_id, overlap, i
            expected.append(best)

        pipeline = SpeechPipeline()
        result = pipeline._match_speakers(words, segments)
        assert [w.speaker_id for w in result] == expected
        assert all(isinstance(w, W) for w in result)
