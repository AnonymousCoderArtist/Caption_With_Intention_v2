"""Regression coverage for CPU analysis and opt-in sound suggestions."""
from __future__ import annotations

from unittest.mock import patch

import numpy as np
import pytest

from engine.asr.models import TranscriptionResult, Word
from engine.audio_analysis.basic import estimate_pitch, positive_autocorrelation
from engine.audio_analysis.classify import YamnetClassifier, detect_sound_regions
from engine.editor.editor import Editor
from engine.speech.pipeline import SpeechPipeline


@pytest.mark.parametrize("length", [0, 11, 255, 256, 1001, 4000])
def test_fft_autocorrelation_matches_direct_linear_reference(length):
    x = np.random.default_rng(8).normal(size=length)
    expected = np.correlate(x, x, "full")[length-1:] if length else np.array([])
    np.testing.assert_allclose(positive_autocorrelation(x), expected, atol=1e-10, rtol=1e-10)


@pytest.mark.parametrize("frequency", [85, 120, 180, 250, 440])
def test_fft_pitch_keeps_measured_frequency(frequency):
    x = np.sin(np.arange(16000) / 16000 * 2 * np.pi * frequency)
    assert estimate_pitch(x, 16000) == pytest.approx(frequency, rel=.01)


def test_yamnet_classify_delegates_without_optional_model():
    classifier = object.__new__(YamnetClassifier)
    classifier.classify_detail = lambda audio, rate: ("silence", None)
    assert classifier.classify(np.zeros(10), 16000) == "silence"


class MusicClassifier:
    def classify(self, audio, rate):
        return "music"


def test_regions_never_run_past_source_end_or_drift_with_fractional_frames():
    regions = detect_sound_regions(np.ones(1200), 1000, [], MusicClassifier(), frame_s=.3333)
    assert regions[-1].end == 1.2
    assert all(0 <= region.start < region.end <= 1.2 for region in regions)


def test_negative_speech_spans_do_not_mask_audio_tail():
    regions = detect_sound_regions(np.ones(1000), 1000, [(-2, -.5)], MusicClassifier())
    assert regions[0].start == 0
    assert regions[0].end == 1


@pytest.mark.parametrize("kwargs", [{"sample_rate": 0}, {"frame_s": 0}, {"min_region_s": -1}])
def test_sound_detection_rejects_invalid_configuration(kwargs):
    config = {"sample_rate": 16000, **kwargs}
    with pytest.raises(ValueError):
        detect_sound_regions(np.zeros(16000), speech_spans=[], **config)


def result():
    return {"transcription": TranscriptionResult(text="hello", words=[Word("hello", 0, .5)], duration=2)}


def test_run_full_decodes_analysis_audio_once_for_all_three_stages():
    pipe = SpeechPipeline()
    data = result()
    audio = (np.zeros(32000, dtype=np.float32), 16000)
    with patch.object(pipe, "run_with_alignment", return_value=data), patch(
        "engine.audio_analysis.io.load_analysis_audio", return_value=audio
    ) as load:
        pipe.run_full("not-a-source.mp4", detect_sounds=True)
    load.assert_called_once()
    assert data["sound_regions"] == []
    assert data["intonation"] is not None


def test_sound_suggestions_are_opt_in_and_never_get_invented_confidence():
    pipe = SpeechPipeline()
    data = result()
    audio = (np.ones(32000, dtype=np.float32) * .2, 16000)
    pipe.attach_sound_regions(data, "unused", classifier=MusicClassifier(), analysis_audio=audio)
    payload = pipe.build_editor_payload(data)
    music = next(entry for entry in payload["transcript"] if entry.get("type") == "music")
    assert music["confidence"] is None
    assert music["speaker_id"] is None
    assert music["start"] >= .5
    assert "Unverified" in music["notes"]
    project = Editor().build_from_transcript(payload["transcript"])
    sound = next(event for event in project.events if event.type.value == "music")
    assert "Unverified" in sound.notes
    assert sound.review_state.value == "pending"


def test_project_duration_uses_max_end_not_last_sorted_start():
    project = Editor().build_from_transcript([
        {"text": "music", "start": 0, "end": 10, "type": "music"},
        {"text": "hello", "start": 1, "end": 2},
    ])
    assert project.video.duration == 10


def test_sound_regions_never_bridge_short_speech_gaps():
    regions = detect_sound_regions(np.ones(2000), 1000, [(0.75, 1.0)], MusicClassifier())
    assert len(regions) == 2
    assert regions[0].end <= .75
    assert regions[1].start >= 1.0
