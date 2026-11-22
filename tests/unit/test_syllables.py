"""M10 unit tests — syllable splitting, timing, and animation decision."""

from __future__ import annotations

import numpy as np
import pytest

from engine.alignment.syllables import (
    MIN_SYLLABLE_CONFIDENCE,
    TEXT_ESTIMATE_CONFIDENCE,
    assign_syllable_timings,
    should_use_syllable_animation,
    split_syllables,
    syllabify_words,
)
from engine.asr.models import Word

SR = 16000


# ─── Rule-Based Splitting ──────────────────────────────────────


class TestSplitSyllables:
    @pytest.mark.parametrize(
        "word,expected",
        [
            ("caption", ["cap", "tion"]),
            ("intention", ["in", "ten", "tion"]),
            ("hello", ["hel", "lo"]),
            ("computer", ["com", "pu", "ter"]),
            ("table", ["ta", "ble"]),
            ("vision", ["vi", "sion"]),
            ("period", ["pe", "ri", "od"]),
            ("strong", ["strong"]),
            ("the", ["the"]),
            ("a", ["a"]),
            ("beautiful", ["beau", "ti", "ful"]),
        ],
    )
    def test_common_words(self, word, expected):
        assert split_syllables(word) == expected

    def test_short_words_unsplit(self):
        assert split_syllables("cat") == ["cat"]
        assert split_syllables("an") == ["an"]

    def test_non_letters_single_syllable(self):
        assert split_syllables("42") == ["42"]
        assert split_syllables("!!!") == ["!!!"]

    def test_empty(self):
        assert split_syllables("") == []

    def test_digraphs_stay_together(self):
        # "sh" must not split across syllables
        syllables = split_syllables("washing")
        assert not any(s.endswith("s") and syllables[i + 1].startswith("h")
                       for i, s in enumerate(syllables[:-1]))


# ─── Timing Assignment ─────────────────────────────────────────


class TestAssignTimings:
    def test_text_estimate_proportional(self):
        word = Word("caption", 1.0, 1.6)
        result = assign_syllable_timings(word, ["cap", "tion"])
        assert result.method == "text_estimate"
        assert result.confidence == TEXT_ESTIMATE_CONFIDENCE
        cap, tion = result.syllables
        assert cap["start"] == 1.0
        assert tion["end"] == 1.6
        # "tion" (4 chars) gets twice the time of "cap" (3 chars)? No:
        # 3/7 and 4/7 of 0.6s
        assert cap["end"] == pytest.approx(1.0 + 0.6 * 3 / 7, abs=1e-3)
        assert cap["end"] == tion["start"]

    def test_single_syllable_full_span(self):
        word = Word("strong", 2.0, 2.4)
        result = assign_syllable_timings(word, ["strong"])
        assert result.syllables == [
            {"text": "strong", "start": 2.0, "end": 2.4}
        ]

    def test_no_syllables(self):
        result = assign_syllable_timings(Word("", 0.0, 0.1), [])
        assert result.syllables == []

    def test_timings_are_monotonic(self):
        word = Word("intention", 0.0, 0.9)
        result = assign_syllable_timings(word, ["in", "ten", "tion"])
        ends = [(s["start"], s["end"]) for s in result.syllables]
        for (s, e) in ends:
            assert e > s
        for i in range(len(ends) - 1):
            assert ends[i][1] == ends[i + 1][0]

    def test_audio_refinement_raises_confidence(self):
        # Two-tone audio: loud syllable, quiet dip, loud syllable
        t = np.arange(int(SR * 0.6)) / SR
        envelope = np.ones_like(t)
        envelope[int(0.25 * SR):int(0.35 * SR)] = 0.05  # dip mid-word
        audio = (0.5 * envelope * np.sin(2 * np.pi * 200 * t)).astype(np.float32)
        word = Word("caption", 0.0, 0.6)
        result = assign_syllable_timings(
            word, ["cap", "tion"], audio=audio, sample_rate=SR
        )
        assert result.method == "audio_refined"
        assert result.confidence >= MIN_SYLLABLE_CONFIDENCE
        # Boundary snapped near the dip (0.25-0.35s), not at the
        # proportional 0.257s... both close; assert inside the dip window
        boundary = result.syllables[0]["end"]
        assert 0.2 < boundary < 0.4

    def test_silent_audio_falls_back_to_text_estimate(self):
        audio = np.zeros(int(SR * 0.5), dtype=np.float32)
        word = Word("caption", 0.0, 0.5)
        result = assign_syllable_timings(
            word, ["cap", "tion"], audio=audio, sample_rate=SR
        )
        assert result.method == "text_estimate"


# ─── Automatic Word/Syllable Decision ──────────────────────────


class TestAnimationDecision:
    def test_text_only_stays_word_level(self):
        word = Word("intention", 0.0, 0.9)
        result = assign_syllable_timings(word, ["in", "ten", "tion"])
        assert result.use_syllable_animation is False

    def test_audio_refined_enables_syllable_level(self):
        t = np.arange(int(SR * 0.6)) / SR
        envelope = np.ones_like(t)
        envelope[int(0.28 * SR):int(0.34 * SR)] = 0.02
        audio = (0.5 * envelope * np.sin(2 * np.pi * 200 * t)).astype(np.float32)
        word = Word("caption", 0.0, 0.6)
        result = assign_syllable_timings(
            word, ["cap", "tion"], audio=audio, sample_rate=SR
        )
        assert result.use_syllable_animation is True

    def test_short_word_stays_word_level(self):
        word = Word("caption", 0.0, 0.1)  # below 0.2s minimum
        result = assign_syllable_timings(word, ["cap", "tion"])
        result.confidence = 1.0  # even with perfect confidence
        assert should_use_syllable_animation(word, result) is False

    def test_single_syllable_stays_word_level(self):
        word = Word("strong", 0.0, 0.5)
        result = assign_syllable_timings(word, ["strong"])
        result.confidence = 1.0
        assert should_use_syllable_animation(word, result) is False


# ─── Batch ─────────────────────────────────────────────────────


class TestSyllabifyWords:
    def test_batch(self):
        words = [Word("hello", 0.0, 0.4), Word("world", 0.5, 0.9)]
        results = syllabify_words(words)
        assert len(results) == 2
        assert results[0].syllables[0]["text"] == "hel"
        assert all(r.method == "text_estimate" for r in results)

    def test_empty(self):
        assert syllabify_words([]) == []

    def test_to_dict_shape(self):
        results = syllabify_words([Word("caption", 0.0, 0.6)])
        d = results[0].to_dict()
        assert d["word_text"] == "caption"
        assert len(d["syllables"]) == 2
        assert d["use_syllable_animation"] is False
