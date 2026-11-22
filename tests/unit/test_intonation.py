"""M9 unit tests — word-level intonation analysis on synthetic audio."""

from __future__ import annotations

import numpy as np
import pytest

from engine.asr.models import Word
from engine.audio_analysis.intonation import (
    DEFAULT_SAMPLE_RATE,
    IntonationAnalyzer,
    estimate_harmonic_energies,
)

SR = DEFAULT_SAMPLE_RATE


def _sine(freq: float, duration: float, amp: float = 0.5) -> np.ndarray:
    t = np.arange(int(SR * duration)) / SR
    return (amp * np.sin(2 * np.pi * freq * t)).astype(np.float32)


def _silence(duration: float) -> np.ndarray:
    return np.zeros(int(SR * duration), dtype=np.float32)


def _concat(*parts: np.ndarray) -> np.ndarray:
    return np.concatenate(parts) if parts else np.array([], dtype=np.float32)


# ─── Harmonic Energy Split ─────────────────────────────────────


class TestHarmonicEnergies:
    def test_low_tone_is_low_dominant(self):
        low, high = estimate_harmonic_energies(_sine(200, 0.5), SR)
        assert low > 0.9
        assert high < 0.1

    def test_high_tone_is_high_dominant(self):
        low, high = estimate_harmonic_energies(_sine(3000, 0.5), SR)
        assert high > 0.9
        assert low < 0.1

    def test_silence_is_zero(self):
        assert estimate_harmonic_energies(_silence(0.5), SR) == (0.0, 0.0)

    def test_empty(self):
        assert estimate_harmonic_energies(
            np.array([], dtype=np.float32), SR
        ) == (0.0, 0.0)


# ─── Word-Level Analysis ───────────────────────────────────────


class TestIntonationAnalyzer:
    def test_volume_maps_louder_to_bigger(self):
        # Two words: quiet 200 Hz then loud 200 Hz
        audio = _concat(_sine(200, 0.3, amp=0.01), _sine(200, 0.3, amp=0.8))
        words = [Word("soft", 0.0, 0.3), Word("LOUD", 0.3, 0.6)]
        a = IntonationAnalyzer(smooth_window=1)
        result = a.analyze(audio, SR, words)
        quiet, loud = result.words
        assert loud.loudness > quiet.loudness
        assert loud.typography["size_pct"] > quiet.typography["size_pct"]

    def test_hot_scene_calibrates_to_baseline(self):
        # Uniformly hot-mastered speech (all words loud in absolute dB)
        # must render at the 5% baseline, not blow up every word.
        audio = _concat(
            _sine(200, 0.3, amp=0.8),
            _sine(200, 0.3, amp=0.8),
            _sine(200, 0.3, amp=0.8),
        )
        words = [
            Word("even", 0.0, 0.3),
            Word("even", 0.3, 0.6),
            Word("even", 0.6, 0.9),
        ]
        result = IntonationAnalyzer(smooth_window=1).analyze(audio, SR, words)
        for w in result.words:
            assert w.typography["size_pct"] == pytest.approx(5.0, abs=0.3)
            # Raw measured loudness is preserved on the word.
            assert w.loudness > 0.5

    def test_hot_scene_preserves_emphasis_contrast(self):
        # In a hot scene, a word clearly louder than the rest still
        # grows above baseline.
        audio = _concat(
            _sine(200, 0.3, amp=0.8),
            _sine(200, 0.3, amp=0.8),
            _sine(200, 0.3, amp=1.0),
        )
        words = [
            Word("calm", 0.0, 0.3),
            Word("calm", 0.3, 0.6),
            Word("SHOUT", 0.6, 0.9),
        ]
        result = IntonationAnalyzer(smooth_window=1).analyze(audio, SR, words)
        calm, _, shout = result.words
        assert calm.typography["size_pct"] == pytest.approx(5.0, abs=0.3)
        assert shout.typography["size_pct"] > calm.typography["size_pct"]

    def test_low_pitch_heavier_weight(self):
        audio = _concat(_sine(120, 0.4), _sine(280, 0.4))
        words = [Word("deep", 0.0, 0.4), Word("high", 0.4, 0.8)]
        a = IntonationAnalyzer(smooth_window=1)
        result = a.analyze(audio, SR, words)
        deep, high = result.words
        assert deep.pitch_hz is not None
        assert deep.pitch_hz == pytest.approx(120, abs=15)
        assert deep.typography["weight"] > 400
        assert high.typography["weight"] < deep.typography["weight"]

    def test_baseline_pitch_neutral_weight(self):
        audio = _sine(180, 0.4)
        words = [Word("normal", 0.0, 0.4)]
        result = IntonationAnalyzer(smooth_window=1).analyze(audio, SR, words)
        w = result.words[0]
        assert w.pitch_hz == pytest.approx(180, abs=15)
        assert w.typography["weight"] == 400

    def test_low_harmonics_wider_type(self):
        audio = _concat(_sine(200, 0.4), _sine(3000, 0.4))
        words = [Word("boom", 0.0, 0.4), Word("hiss", 0.4, 0.8)]
        result = IntonationAnalyzer(smooth_window=1).analyze(audio, SR, words)
        deep, bright = result.words
        assert deep.typography["width"] > 100
        assert bright.typography["width"] < 100
        assert deep.typography["width"] > bright.typography["width"]

    def test_silent_word_unreliable(self):
        audio = _concat(_sine(200, 0.3), _silence(0.3))
        words = [Word("voiced", 0.0, 0.3), Word("gap", 0.3, 0.6)]
        result = IntonationAnalyzer(smooth_window=1).analyze(audio, SR, words)
        assert result.words[0].reliable is True
        assert result.words[1].reliable is False
        assert result.words[1].pitch_hz is None
        assert result.unreliable_count == 1

    def test_tiny_word_unreliable(self):
        audio = _sine(200, 0.5)
        words = [Word("a", 0.0, 0.01)]  # 10 ms — too short for pitch
        result = IntonationAnalyzer(smooth_window=1).analyze(audio, SR, words)
        assert result.words[0].reliable is False

    def test_smoothing_pulls_extremes_together(self):
        # alternating quiet/loud words
        parts = []
        words = []
        t = 0.0
        for i in range(6):
            amp = 0.01 if i % 2 == 0 else 0.8
            parts.append(_sine(200, 0.2, amp=amp))
            words.append(Word(f"w{i}", t, t + 0.2))
            t += 0.2
        audio = _concat(*parts)

        unsmoothed = IntonationAnalyzer(smooth_window=1).analyze(audio, SR, words)
        smoothed = IntonationAnalyzer(smooth_window=5).analyze(audio, SR, words)

        raw_range = (
            max(w.loudness for w in unsmoothed.words)
            - min(w.loudness for w in unsmoothed.words)
        )
        smooth_range = (
            max(w.loudness for w in smoothed.words)
            - min(w.loudness for w in smoothed.words)
        )
        assert smooth_range < raw_range

    def test_empty_words(self):
        result = IntonationAnalyzer().analyze(_sine(200, 0.3), SR, [])
        assert result.word_count == 0
        assert result.duration == pytest.approx(0.3, abs=0.01)

    def test_to_dict_shape(self):
        audio = _sine(200, 0.3)
        result = IntonationAnalyzer(smooth_window=1).analyze(
            audio, SR, [Word("hello", 0.0, 0.3)]
        )
        d = result.to_dict()
        assert d["word_count"] == 1
        w = d["words"][0]
        assert w["text"] == "hello"
        assert "size_pct" in w["typography"]
        assert "weight" in w["typography"]
        assert "width" in w["typography"]


# ─── File Loading ──────────────────────────────────────────────


class TestAnalyzeFile:
    def test_wav_file(self, tmp_path):
        import soundfile as sf

        audio = _sine(200, 0.3)
        wav = tmp_path / "tone.wav"
        sf.write(str(wav), audio, SR)
        result = IntonationAnalyzer(smooth_window=1).analyze_file(
            wav, [Word("tone", 0.0, 0.3)]
        )
        assert result.words[0].reliable is True
        assert result.words[0].pitch_hz == pytest.approx(200, abs=15)

    def test_stereo_wav_downmixed(self, tmp_path):
        import soundfile as sf

        mono = _sine(250, 0.3)
        stereo = np.stack([mono, mono], axis=1)
        wav = tmp_path / "stereo.wav"
        sf.write(str(wav), stereo, SR)
        result = IntonationAnalyzer(smooth_window=1).analyze_file(
            wav, [Word("stereo", 0.0, 0.3)]
        )
        assert result.words[0].pitch_hz == pytest.approx(250, abs=15)
