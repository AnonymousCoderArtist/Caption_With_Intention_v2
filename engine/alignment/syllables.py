"""Syllable splitting and timing (M10).

The CWI design system animates captions at syllable level when alignment
confidence is high enough (spec §M10). This module:

1. Splits English words into syllables (rule-based, no dictionary).
2. Assigns syllable timings inside a word's ASR time span — proportional
   by letter count, optionally snapped to acoustic energy dips.
3. Decides per word whether syllable-level or word-level animation
   should be used (the spec's "automatic decision").

Output shape matches what the editor and renderer already consume:
``{"text", "start", "end"}`` dicts per syllable.

Usage:
    from engine.alignment.syllables import syllabify_words

    results = syllabify_words(words, audio=waveform, sample_rate=16000)
    for wr in results:
        if wr.use_syllable_animation:
            ...  # pass wr.syllables to the renderer/editor
"""

from __future__ import annotations

import logging
import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from itertools import pairwise
from typing import Optional

import numpy as np

from engine.asr.models import Word

logger = logging.getLogger("caption_with_intention")

VOWELS = set("aeiou")
# Consonant digraphs that stay together when splitting a cluster.
DIGRAPHS = ("ch", "sh", "th", "ph", "wh", "ck", "ng", "qu", "gh")
# Consonants after which "i+vowel" glides into one syllable ("-tion").
GLIDE_PRECEDERS = set("tscx")
# Fraction of a syllable's duration a boundary may move when snapping
# to an acoustic energy dip.
MAX_SNAP_RATIO = 0.30
# Confidence of a text-only syllabification (no audio evidence).
TEXT_ESTIMATE_CONFIDENCE = 0.4
# Minimum confidence for the automatic syllable-animation decision.
MIN_SYLLABLE_CONFIDENCE = 0.6
# Minimum word duration (s) for syllable-level animation to make sense.
MIN_SYLLABLE_WORD_DURATION = 0.2
# RMS frame size for energy-dip snapping (s).
FRAME_HOP = 0.01

_WORD_CHARS = re.compile(r"[a-z']+")


@dataclass(slots=True)
class WordSyllables:
    """Syllabification result for one word."""

    word_text: str
    start: float
    end: float
    syllables: list[dict] = field(default_factory=list)
    method: str = "text_estimate"  # "audio_refined" | "text_estimate"
    confidence: float = TEXT_ESTIMATE_CONFIDENCE
    use_syllable_animation: bool = False

    def to_dict(self) -> dict:
        return {
            "word_text": self.word_text,
            "start": self.start,
            "end": self.end,
            "syllables": [dict(s) for s in self.syllables],
            "method": self.method,
            "confidence": round(self.confidence, 4),
            "use_syllable_animation": self.use_syllable_animation,
        }


def _vowel_groups(word: str) -> list[tuple[int, int]]:
    """Vowel-group spans [start, end) in a lowercase letters-only word.

    'y' counts as a vowel when preceded by a consonant. An "i" group
    directly followed by a vowel merges into one group when the 'i' is
    preceded by a glide consonant (the "-tion"/"-sion" pattern).
    """
    groups: list[tuple[int, int]] = []
    i = 0
    n = len(word)

    def is_vowel(idx: int) -> bool:
        ch = word[idx]
        if ch in VOWELS:
            return True
        return ch == "y" and idx > 0 and word[idx - 1] not in VOWELS | {"y"}

    while i < n:
        if is_vowel(i):
            j = i
            # Extend over adjacent vowels, but never FROM an 'i': an
            # 'i'+vowel pair is left as two groups so the glide pass
            # below can decide (-tion merges, pe-ri-od stays split).
            while j + 1 < n and is_vowel(j + 1) and word[j] != "i":
                j += 1
            groups.append((i, j + 1))
            i = j + 1
        else:
            i += 1

    # Merge "i" + following vowel group after a glide consonant
    merged: list[tuple[int, int]] = []
    skip_next = False
    for gi, (s, e) in enumerate(groups):
        if skip_next:
            skip_next = False
            continue
        if (
            e - s == 1
            and word[s] == "i"
            and gi + 1 < len(groups)
            and groups[gi + 1][0] == e  # directly adjacent vowel group
            and s > 0
            and word[s - 1] in GLIDE_PRECEDERS
        ):
            merged.append((s, groups[gi + 1][1]))
            skip_next = True
        else:
            merged.append((s, e))
    return merged


def split_syllables(text: str) -> list[str]:
    """Split an English word into syllables (rule-based estimate).

    Handles the common cases: consonant clusters split V-CV / VC-CV,
    digraphs stay together, final silent 'e' is dropped unless it forms
    a "-le" syllable, "-tion"/"-sion" glides merge. Non-letter content
    (numbers, punctuation) is returned as a single syllable.
    """
    cleaned = "".join(_WORD_CHARS.findall(text.lower())).replace("'", "")
    if len(cleaned) <= 3:
        return [text] if text else []

    groups = _vowel_groups(cleaned)
    if not groups:
        return [text]

    # Final silent 'e': drop unless it forms a "-le" syllable.
    s, e = groups[-1]
    if (
        cleaned[s:e] == "e"
        and e == len(cleaned)
        and len(groups) > 1
        and s >= 2
    ):
        if cleaned[s - 1] == "l" and cleaned[s - 2] not in VOWELS:
            pass  # "-le" keeps its own syllable (e.g. "ta-ble")
        else:
            groups = groups[:-1]

    if len(groups) <= 1:
        return [text]

    # Boundary indices between consecutive vowel groups.
    boundaries: list[int] = []
    for (s1, e1), (s2, e2) in pairwise(groups):
        cluster = cleaned[e1:s2]
        if (
            cleaned[s2:e2] == "e"
            and e2 == len(cleaned)
            and s2 >= 2
            and cleaned[s2 - 1] == "l"
            and cleaned[s2 - 2] not in VOWELS
        ):
            # Final "-le" syllable pulls its onset consonant ("ta-ble")
            boundaries.append(s2 - 2)
            continue
        if len(cluster) == 0:
            boundaries.append(s2)  # vowel hiatus: split between groups
        elif len(cluster) == 1:
            boundaries.append(s2 - 1)  # V-CV: consonant onsets next syllable
        elif len(cluster) == 2 and cluster in DIGRAPHS:
            boundaries.append(s2 - 2)  # digraph stays together
        else:
            # 2+ consonants: split inside the cluster (VC-CV)
            boundaries.append(e1 + 1)

    syllables: list[str] = []
    prev = 0
    for b in boundaries:
        syllables.append(cleaned[prev:b])
        prev = b
    syllables.append(cleaned[prev:])
    return [s for s in syllables if s]


def assign_syllable_timings(
    word: Word,
    syllables: Sequence[str],
    audio: Optional[np.ndarray] = None,
    sample_rate: Optional[int] = None,
) -> WordSyllables:
    """Assign start/end times to a word's syllables.

    Base timings split the word's span proportionally by syllable
    length. When audio is provided, interior boundaries snap to the
    nearest acoustic energy dip and the result carries higher,
    dip-strength-based confidence.
    """
    result = WordSyllables(
        word_text=word.text, start=word.start, end=word.end
    )
    if not syllables:
        return result

    duration = max(word.end - word.start, 0.0)
    if len(syllables) == 1 or duration <= 0:
        result.syllables = [
            {"text": syllables[0], "start": word.start, "end": word.end}
        ]
        return result

    # Proportional split by character count
    total_chars = sum(len(s) for s in syllables)
    boundaries: list[float] = []
    t = word.start
    for syl in syllables[:-1]:
        t += duration * len(syl) / total_chars
        boundaries.append(t)

    confidence = TEXT_ESTIMATE_CONFIDENCE
    method = "text_estimate"

    if audio is not None and sample_rate:
        snapped, dip_confidence = _snap_boundaries_to_dips(
            audio, sample_rate, word, boundaries
        )
        if snapped is not None:
            boundaries = snapped
            method = "audio_refined"
            confidence = dip_confidence

    out: list[dict] = []
    prev = word.start
    for syl, boundary in zip(syllables, [*boundaries, word.end]):
        out.append({"text": syl, "start": round(prev, 4), "end": round(boundary, 4)})
        prev = boundary
    result.syllables = out
    result.method = method
    result.confidence = confidence
    result.use_syllable_animation = should_use_syllable_animation(word, result)
    return result


def _frame_energies(
    audio: np.ndarray,
    sample_rate: int,
    start: float,
    end: float,
) -> np.ndarray:
    """Vectorized per-frame RMS energy over a time span (10 ms frames)."""
    i0 = max(0, int(start * sample_rate))
    i1 = min(len(audio), int(end * sample_rate))
    if i1 - i0 < 2:
        return np.array([])
    span = audio[i0:i1]
    frame = int(FRAME_HOP * sample_rate)
    n_frames = len(span) // frame
    if n_frames < 2:
        return np.array([])
    trimmed = span[: n_frames * frame].reshape(n_frames, frame)
    return np.sqrt(np.mean(trimmed**2, axis=1))


def _snap_boundaries_to_dips(
    audio: np.ndarray,
    sample_rate: int,
    word: Word,
    boundaries: list[float],
) -> tuple[Optional[list[float]], float]:
    """Snap proportional boundaries to local energy minima.

    Returns (snapped_boundaries, confidence) or (None, 0.0) when the
    word span has no usable energy signal. Confidence is the average
    relative dip depth at the snapped boundaries (1 = silence at the
    boundary, 0 = no dip at all), floored at 0.5 for any real signal so
    that mild dips in continuous speech still count as refined.
    """
    energies = _frame_energies(audio, sample_rate, word.start, word.end)
    if len(energies) < 4 or float(energies.max()) <= 0:
        return None, 0.0

    duration = word.end - word.start
    snapped: list[float] = []
    dip_depths: list[float] = []
    prev = word.start

    for i, boundary in enumerate(boundaries):
        # Limit movement: not past neighbors, not beyond ±30% of the
        # surrounding syllable durations.
        right_limit = boundaries[i + 1] if i + 1 < len(boundaries) else word.end
        window = MAX_SNAP_RATIO * duration / max(len(boundaries), 1)
        lo = max(prev + 0.01, boundary - window)
        hi = min(right_limit - 0.01, boundary + window)
        if hi <= lo:
            snapped.append(boundary)
            dip_depths.append(0.5)
            prev = boundary
            continue

        f_lo = int((lo - word.start) / FRAME_HOP)
        f_hi = min(len(energies) - 1, int((hi - word.start) / FRAME_HOP) + 1)
        if f_hi <= f_lo:
            snapped.append(boundary)
            dip_depths.append(0.5)
            prev = boundary
            continue

        local = energies[f_lo:f_hi]
        best = int(np.argmin(local)) + f_lo
        snapped_t = word.start + best * FRAME_HOP + FRAME_HOP / 2
        snapped.append(snapped_t)
        depth = 1.0 - float(energies[best]) / (float(energies.max()) + 1e-10)
        dip_depths.append(max(depth, 0.0))
        prev = snapped_t

    confidence = min(1.0, 0.5 + 0.5 * (sum(dip_depths) / len(dip_depths)))
    return snapped, confidence


def should_use_syllable_animation(
    word: Word,
    result: WordSyllables,
    min_confidence: float = MIN_SYLLABLE_CONFIDENCE,
    min_duration: float = MIN_SYLLABLE_WORD_DURATION,
) -> bool:
    """The spec's automatic word-level vs syllable-level decision.

    Syllable animation only when there are multiple syllables, the word
    is long enough for the viewer to perceive the animation, and the
    timing confidence clears the threshold (in practice: audio-refined
    timings; text-only estimates stay word-level).
    """
    return (
        len(result.syllables) >= 2
        and (word.end - word.start) >= min_duration
        and result.confidence >= min_confidence
    )


def syllabify_words(
    words: Sequence[Word],
    audio: Optional[np.ndarray] = None,
    sample_rate: Optional[int] = None,
) -> list[WordSyllables]:
    """Split and time syllables for a word sequence.

    Args:
        words: Words with timings (ASR + alignment output).
        audio: Optional waveform for acoustic boundary refinement.
        sample_rate: Required when audio is given.

    Returns:
        One WordSyllables per input word.
    """
    results: list[WordSyllables] = []
    for word in words:
        syllables = split_syllables(word.text)
        results.append(
            assign_syllable_timings(word, syllables, audio, sample_rate)
        )
    refined = sum(1 for r in results if r.method == "audio_refined")
    animated = sum(1 for r in results if r.use_syllable_animation)
    logger.info(
        "Syllabified %d words (%d audio-refined, %d syllable-animated)",
        len(results),
        refined,
        animated,
    )
    return results
