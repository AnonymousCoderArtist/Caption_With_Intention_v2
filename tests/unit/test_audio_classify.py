"""Tests for audio classification (speech vs music vs sfx)."""

from __future__ import annotations

import numpy as np
import pytest

from engine.audio_analysis.classify import (
    HeuristicClassifier,
    detect_sound_regions,
    estimate_region_loudness,
    harmonicity,
    spectral_flux,
    zero_crossing_rate,
)

SR = 16000


def _sine(freq: float, dur: float, amp: float = 0.5) -> np.ndarray:
    t = np.arange(int(dur * SR)) / SR
    return (amp * np.sin(2 * np.pi * freq * t)).astype(np.float32)


def _chord(dur: float, amp: float = 0.4) -> np.ndarray:
    t = np.arange(int(dur * SR)) / SR
    sig = sum(np.sin(2 * np.pi * f * t) for f in (220.0, 277.2, 329.6))
    return (amp * sig / 3).astype(np.float32)


def _noise(dur: float, amp: float = 0.5) -> np.ndarray:
    rng = np.random.default_rng(42)
    return (amp * rng.standard_normal(int(dur * SR))).astype(np.float32)


def _burst(dur: float = 0.5) -> np.ndarray:
    """Short broadband transient burst: decaying noise."""
    rng = np.random.default_rng(7)
    n = int(dur * SR)
    env = np.exp(-np.linspace(0, 6, n))
    return (0.7 * env * rng.standard_normal(n)).astype(np.float32)


class TestFeatureFunctions:
    def test_sine_high_harmonicity(self):
        assert harmonicity(_sine(220.0, 1.0), SR) > 0.9

    def test_noise_low_harmonicity(self):
        assert harmonicity(_noise(1.0), SR) < 0.2

    def test_burst_higher_flux_than_sine(self):
        assert spectral_flux(_burst(), SR) > spectral_flux(_sine(220.0, 0.5), SR)

    def test_noise_higher_zcr_than_sine(self):
        assert zero_crossing_rate(_noise(0.5)) > zero_crossing_rate(_sine(220.0, 0.5))

    def test_loudness_normalized(self):
        assert estimate_region_loudness(_sine(220.0, 0.5, amp=0.5)) == pytest.approx(0.5, abs=0.02)
        assert estimate_region_loudness(np.zeros(SR)) == 0.0


class TestHeuristicClassifier:
    def setup_method(self):
        self.clf = HeuristicClassifier()

    def test_silence(self):
        assert self.clf.classify(np.zeros(SR), SR) == "silence"
        assert self.clf.classify(np.array([]), SR) == "silence"

    def test_music(self):
        # sustained chord: strong periodicity, low flux
        assert self.clf.classify(_chord(1.5), SR) == "music"

    def test_sfx_noise_burst(self):
        assert self.clf.classify(_burst(), SR) == "sfx"

    def test_sfx_white_noise(self):
        assert self.clf.classify(_noise(1.0), SR) == "sfx"

    def test_pure_tone_is_music(self):
        assert self.clf.classify(_sine(220.0, 1.0), SR) == "music"


class TestDetectSoundRegions:
    def test_music_and_sfx_between_speech(self):
        speech = _sine(150.0, 1.0)  # placeholder "speech" audio
        music = _chord(1.0)
        sfx = _burst(0.6)
        audio = np.concatenate([speech, music, sfx, speech])
        speech_spans = [(0.0, 1.0), (2.6, 3.6)]
        regions = detect_sound_regions(audio, SR, speech_spans)
        labels = [r.label for r in regions]
        assert "music" in labels
        assert "sfx" in labels
        # music region sits inside 1.0-2.0s, sfx inside 2.0-2.6s
        music_r = next(r for r in regions if r.label == "music")
        sfx_r = next(r for r in regions if r.label == "sfx")
        assert music_r.start < 1.5 < music_r.end or music_r.start >= 0.9
        assert sfx_r.start >= 1.9
        assert all(r.end > r.start for r in regions)
        assert all(0.0 < r.loudness <= 1.0 for r in regions)

    def test_all_speech_no_regions(self):
        audio = _sine(150.0, 2.0)
        regions = detect_sound_regions(audio, SR, [(0.0, 2.0)])
        assert regions == []

    def test_silence_produces_no_regions(self):
        regions = detect_sound_regions(np.zeros(SR * 2), SR, [])
        assert regions == []

    def test_short_regions_dropped(self):
        audio = np.concatenate([_sine(150.0, 1.0), _burst(0.2), _sine(150.0, 1.0)])
        regions = detect_sound_regions(audio, SR, [(0.0, 1.0), (1.2, 2.2)], min_region_s=0.3)
        assert regions == []


class TestYamnetClassifier:
    """YAMNet integration; skipped without onnxruntime + model files."""

    @pytest.fixture
    def clf(self):
        pytest.importorskip("onnxruntime")
        import os

        from engine.audio_analysis.classify import YamnetClassifier

        model = os.path.expanduser("~/.cache/cwi/yamnet.onnx")
        cmap = os.path.expanduser("~/.cache/cwi/yamnet_class_map.csv")
        if not (os.path.exists(model) and os.path.exists(cmap)):
            pytest.skip("YAMNet model files not cached")
        return YamnetClassifier(model, cmap)

    def test_music_chord(self, clf):
        from tests.unit.test_audio_classify import _chord

        label, detail = clf.classify_detail(_chord(2.0), SR)
        assert label == "music"
        assert detail is None or isinstance(detail, str)

    def test_sfx_noise(self, clf):
        from tests.unit.test_audio_classify import _noise

        label, detail = clf.classify_detail(_noise(1.5), SR)
        assert label == "sfx"
        assert isinstance(detail, str) and detail

    def test_silence(self, clf):
        assert clf.classify(np.zeros(SR), SR) == "silence"
