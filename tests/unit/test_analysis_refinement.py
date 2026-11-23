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

