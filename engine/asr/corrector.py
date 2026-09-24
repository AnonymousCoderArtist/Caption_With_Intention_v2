"""Transcript correction — rule-based cleaning of machine transcription.

M6 "Transcript correction": cleans ASR output artifacts while preserving
the exact spoken meaning. No ML involved — deterministic rules only.

Every change is recorded (original value, proposed value, reason, rule id)
so every AI decision stays reviewable (spec §2.2). Nothing is silently
reworded: the only edits are dropping ASR artifacts (duplicated / empty
words) and flagging low-confidence words for human review.

Rules:
    1. repeat-collapse — collapse consecutive duplicate words that ASR
       stutters on ("the the the" → "the"). Comparison is
       case/punctuation-insensitive, so "No, no!" collapses too. Only
       applies when the duplicate is close in time (default: gap of
       max_repeat_gap seconds or less) — widely spaced repeats
       ("no ... no") are likely intentional and are kept.
    2. empty-drop      — drop words with no visible text.
    3. low-confidence  — flag words whose confidence is below the
       threshold (no text change; surfaced in the review queue).

Usage:
    from engine.asr.corrector import TranscriptCorrector

    report = TranscriptCorrector().correct(words)
    clean_words = report.words
    for c in report.corrections:
        print(c.rule_id, c.original, "->", c.corrected, c.reason)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from engine.asr.models import Word

__all__ = ["Correction", "CorrectionReport", "TranscriptCorrector"]

DEFAULT_MIN_CONFIDENCE = 0.5
DEFAULT_MAX_REPEAT_GAP = 0.25  # seconds; larger gaps are not stutter

_RULE_REPEAT = "repeat-collapse"
_RULE_EMPTY = "empty-drop"
_RULE_LOW_CONF = "low-confidence"


@dataclass(slots=True)
class Correction:
    """A single reviewable transcript correction."""

    word_index: int  # index in the original word list
    action: str  # "remove" | "flag"
    original: str
    corrected: str
    reason: str
    rule_id: str

    def to_dict(self) -> dict:
        return {
            "word_index": self.word_index,
            "action": self.action,
            "original": self.original,
            "corrected": self.corrected,
            "reason": self.reason,
            "rule_id": self.rule_id,
        }


@dataclass(slots=True)
class CorrectionReport:
    """Result of correcting a word list: cleaned words + audit log."""

    words: list[Word]  # cleaned words, in original order
    corrections: list[Correction] = field(default_factory=list)

    @property
    def word_count(self) -> int:
        return len(self.words)

    @property
    def correction_count(self) -> int:
        return len(self.corrections)

    @property
    def changed(self) -> bool:
        return any(c.action == "remove" for c in self.corrections)

    @property
    def low_confidence_indices(self) -> list[int]:
        """Indices (in the original list) of flagged words."""
        return [c.word_index for c in self.corrections if c.action == "flag"]

    @property
    def text(self) -> str:
        return " ".join(w.text for w in self.words)

    def to_dict(self) -> dict:
        return {
            "word_count": self.word_count,
            "correction_count": self.correction_count,
            "changed": self.changed,
            "low_confidence_indices": self.low_confidence_indices,
            "corrections": [c.to_dict() for c in self.corrections],
            "words": [w.to_dict() for w in self.words],
            "summary": {
                "removed": sum(1 for c in self.corrections if c.action == "remove"),
                "flagged": sum(1 for c in self.corrections if c.action == "flag"),
            },
        }


class TranscriptCorrector:
    """Rule-based transcript cleaner (M6).

    Args:
        min_confidence: Words with 0 < confidence < this value are flagged
            for review. Words with confidence 0 are treated as
            "no confidence data" and are NOT flagged.
        remove_repeats: Collapse consecutive duplicate words.
        remove_empty: Drop words with no visible text.
        max_repeat_gap: Maximum gap (seconds) between two duplicate
            words for the second to be treated as an ASR stutter.
    """

    def __init__(
        self,
        min_confidence: float = DEFAULT_MIN_CONFIDENCE,
        remove_repeats: bool = True,
        remove_empty: bool = True,
        max_repeat_gap: float = DEFAULT_MAX_REPEAT_GAP,
    ) -> None:
        self.min_confidence = min_confidence
        self.remove_repeats = remove_repeats
        self.remove_empty = remove_empty
        self.max_repeat_gap = max_repeat_gap

    def correct(self, words: list[Word]) -> CorrectionReport:
        """Apply correction rules, preserving spoken meaning.

        Args:
            words: ASR word list (order preserved in the output).

        Returns:
            CorrectionReport with the cleaned word list and a full
            audit log of every decision made.
        """
        cleaned: list[Word] = []
        corrections: list[Correction] = []
        prev_key: str | None = None
        prev_end: float | None = None

        for index, word in enumerate(words):
            key = self._word_key(word.text)

            # Rule 2 — empty words carry no spoken content
            if key == "" and self.remove_empty:
                corrections.append(
                    Correction(
                        word_index=index,
                        action="remove",
                        original=word.text,
                        corrected="",
                        reason="word has no text",
                        rule_id=_RULE_EMPTY,
                    )
                )
                continue

            # Rule 1 — ASR stutter: consecutive duplicate words that are
            # close in time. Widely spaced repeats are likely intentional
            # and are kept.
            is_repeat = False
            if self.remove_repeats and prev_key is not None and key == prev_key:
                gap = 0.0 if prev_end is None else word.start - prev_end
                is_repeat = gap <= self.max_repeat_gap
            if is_repeat:
                corrections.append(
                    Correction(
                        word_index=index,
                        action="remove",
                        original=word.text,
                        corrected="",
                        reason=(
                            f"consecutive repeat of {prev_key!r} "
                            f"(gap {gap:.2f}s <= {self.max_repeat_gap:.2f}s)"
                        ),
                        rule_id=_RULE_REPEAT,
                    )
                )
                # Keep tracking the end of the run so the gap is measured
                # from the last (collapsed) occurrence, not the first
                prev_end = word.end
                continue

            # Rule 3 — low confidence: flag, do not alter
            if 0.0 < word.confidence < self.min_confidence:
                corrections.append(
                    Correction(
                        word_index=index,
                        action="flag",
                        original=word.text,
                        corrected=word.text,
                        reason=(
                            f"confidence {word.confidence:.2f} below "
                            f"threshold {self.min_confidence:.2f}"
                        ),
                        rule_id=_RULE_LOW_CONF,
                    )
                )

            cleaned.append(word)
            prev_key = key
            prev_end = word.end

        return CorrectionReport(words=cleaned, corrections=corrections)

    @staticmethod
    def _word_key(text: str) -> str:
        """Normalized comparison key: lowercase alphanumerics only."""
        return re.sub(r"[^a-z0-9]", "", text.lower())
