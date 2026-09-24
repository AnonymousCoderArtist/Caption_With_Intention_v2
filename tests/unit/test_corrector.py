"""Transcript corrector tests (M6 — transcript correction)."""

from __future__ import annotations

from engine.asr.corrector import TranscriptCorrector
from engine.asr.models import Word


def _words(*items):
    """items: (text, start, end, confidence) tuples."""
    return [Word(t, s, e, confidence=c) for t, s, e, c in items]


class TestRepeatCollapse:
    def test_consecutive_duplicates_collapsed(self):
        words = _words(
            ("the", 0.0, 0.2, 0.9),
            ("the", 0.2, 0.4, 0.9),
            ("the", 0.4, 0.6, 0.9),
            ("dog", 0.6, 0.9, 0.95),
        )
        report = TranscriptCorrector().correct(words)
        assert [w.text for w in report.words] == ["the", "dog"]
        assert report.correction_count == 2
        assert all(c.rule_id == "repeat-collapse" for c in report.corrections)
        assert all(c.action == "remove" for c in report.corrections)

    def test_repeat_case_punctuation_insensitive(self):
        words = _words(
            ("No,", 0.0, 0.2, 0.9),
            ("no", 0.2, 0.4, 0.9),
            ("NO!", 0.4, 0.6, 0.9),
        )
        report = TranscriptCorrector().correct(words)
        assert [w.text for w in report.words] == ["No,"]

    def test_non_consecutive_duplicates_kept(self):
        words = _words(
            ("no", 0.0, 0.2, 0.9),
            ("yes", 0.2, 0.4, 0.9),
            ("no", 0.4, 0.6, 0.9),
        )
        report = TranscriptCorrector().correct(words)
        assert [w.text for w in report.words] == ["no", "yes", "no"]
        assert not report.changed

    def test_repeats_disabled(self):
        words = _words(
            ("the", 0.0, 0.2, 0.9),
            ("the", 0.2, 0.4, 0.9),
        )
        report = TranscriptCorrector(remove_repeats=False).correct(words)
        assert len(report.words) == 2
        assert not report.changed

    def test_widely_spaced_repetition_kept(self):
        """'no ... no' with a long gap is intentional, not ASR stutter."""
        words = _words(
            ("no", 0.0, 0.3, 0.9),
            ("yes", 0.3, 0.6, 0.9),
            ("no", 1.8, 2.1, 0.9),  # 1.2s after the first 'no'
        )
        report = TranscriptCorrector().correct(words)
        assert [w.text for w in report.words] == ["no", "yes", "no"]

    def test_back_to_back_repetition_collapsed(self):
        words = _words(
            ("no", 0.0, 0.3, 0.9),
            ("no", 0.31, 0.6, 0.9),  # 0.01s gap
        )
        report = TranscriptCorrector().correct(words)
        assert [w.text for w in report.words] == ["no"]

    def test_max_repeat_gap_config(self):
        words = _words(
            ("the", 0.0, 0.3, 0.9),
            ("the", 0.33, 0.63, 0.9),  # 0.03s gap
        )
        assert TranscriptCorrector(max_repeat_gap=0.05).correct(words).changed
        assert not TranscriptCorrector(max_repeat_gap=0.02).correct(words).changed


class TestEmptyDrop:
    def test_empty_word_dropped(self):
        words = _words(
            ("", 0.0, 0.1, 0.9),
            ("hello", 0.1, 0.4, 0.9),
        )
        report = TranscriptCorrector().correct(words)
        assert [w.text for w in report.words] == ["hello"]
        assert report.corrections[0].rule_id == "empty-drop"

    def test_whitespace_only_dropped(self):
        words = _words(("   ", 0.0, 0.1, 0.9), ("ok", 0.1, 0.3, 0.9))
        report = TranscriptCorrector().correct(words)
        assert len(report.words) == 1


class TestLowConfidenceFlag:
    def test_low_confidence_flagged_not_altered(self):
        words = _words(
            ("maybe", 0.0, 0.3, 0.3),
            ("word", 0.3, 0.6, 0.95),
        )
        report = TranscriptCorrector(min_confidence=0.5).correct(words)
        # Text preserved — only flagged
        assert [w.text for w in report.words] == ["maybe", "word"]
        flagged = [c for c in report.corrections if c.action == "flag"]
        assert len(flagged) == 1
        assert flagged[0].rule_id == "low-confidence"
        assert flagged[0].word_index == 0
        assert report.low_confidence_indices == [0]

    def test_zero_confidence_not_flagged(self):
        """confidence=0 means 'no data', must not spam the review queue."""
        words = _words(("word", 0.0, 0.3, 0.0))
        report = TranscriptCorrector(min_confidence=0.5).correct(words)
        assert report.corrections == []
        assert len(report.words) == 1

    def test_boundary_confidence_flagged(self):
        words = _words(("word", 0.0, 0.3, 0.49))
        report = TranscriptCorrector(min_confidence=0.5).correct(words)
        assert len(report.low_confidence_indices) == 1


class TestReport:
    def test_to_dict_structure(self):
        words = _words(
            ("the", 0.0, 0.2, 0.9),
            ("the", 0.2, 0.4, 0.3),
        )
        report = TranscriptCorrector().correct(words)
        d = report.to_dict()
        assert d["word_count"] == 1
        assert d["correction_count"] == 1
        assert d["changed"] is True
        assert d["summary"]["removed"] == 1
        assert d["words"][0]["text"] == "the"
        assert isinstance(d["corrections"][0], dict)
        assert d["corrections"][0]["word_index"] == 1

    def test_text_property(self):
        words = _words(
            ("hello", 0.0, 0.3, 0.9),
            ("world", 0.3, 0.6, 0.9),
        )
        report = TranscriptCorrector().correct(words)
        assert report.text == "hello world"

    def test_clean_transcript_no_corrections(self):
        words = _words(
            ("hello", 0.0, 0.3, 0.9),
            ("world", 0.3, 0.6, 0.8),
        )
        report = TranscriptCorrector().correct(words)
        assert report.corrections == []
        assert report.changed is False
        assert report.word_count == 2

    def test_original_value_preserved_in_log(self):
        """Every correction records the original value (spec §2.2)."""
        words = _words(
            ("the", 0.0, 0.2, 0.9),
            ("the", 0.2, 0.4, 0.9),
        )
        report = TranscriptCorrector().correct(words)
        c = report.corrections[0]
        assert c.original == "the"
        assert c.corrected == ""
        assert "reason" in c.to_dict()
