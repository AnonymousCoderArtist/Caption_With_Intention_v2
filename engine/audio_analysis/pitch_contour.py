"""Per-syllable and per-letter pitch contours (M9 extension, 2026-11-22).

The renderer's mid-word pitch contour (syllable "pitch_hz") and the
scaled-text wave on held loud words (Word.letter_pitches) need real
pitch data per syllable/letter. This module derives that data from the
audio so the effects light up automatically for any video - no
hand-fed values.

Data shapes match the renderer contract exactly:
    syllable dicts carry optional "pitch_hz" (see schemas/project.py)
    Word.letter_pitches: per-letter Hz aligned to the word's letters,
    only for sustained loud words whose pitch glides inside a single
    syllable (multi-syllable words already sweep by syllable).
"""

from __future__ import annotations

import logging
from typing import Optional

import numpy as np

from engine.audio_analysis.basic import estimate_pitch
from engine.renderer.renderer import LETTER_SWEEP_MIN_PER_LETTER_S
from engine.renderer.styles import DEFAULT_BASELINE_SIZE_PCT
from schemas.project import Style

logger = logging.getLogger("caption_with_intention")

# Spans shorter than this give unreliable pitch estimates (M9 rule).
MIN_RELIABLE_SPAN_S = 0.04


def span_pitch(
    audio: np.ndarray,
    sample_rate: int,
    start: float,
    end: float,
) -> Optional[float]:
    """Estimate the voice pitch over one time span (seconds).

    Returns None for unvoiced, silent or too-short spans.
    """
    s = max(0, int(start * sample_rate))
    e = min(len(audio), int(end * sample_rate))
    if e - s < int(MIN_RELIABLE_SPAN_S * sample_rate):
        return None
    return estimate_pitch(audio[s:e], sample_rate)


def attach_syllable_pitch(
    audio: np.ndarray,
    sample_rate: int,
    syllables: list[dict],
) -> list[dict]:
    """Copy syllable dicts with "pitch_hz" filled from the audio.

    Syllables whose span is unvoiced or too short simply carry no
    "pitch_hz" key - the renderer leaves those on the baseline.
    """
    out: list[dict] = []
    for syl in syllables:
        d = dict(syl)
        pitch = span_pitch(
            audio,
            sample_rate,
            float(d.get("start", 0.0)),
            float(d.get("end", 0.0)),
        )
        if pitch is not None:
            d["pitch_hz"] = round(pitch, 1)
        out.append(d)
    return out


def letter_pitches_for_word(
    audio: np.ndarray,
    sample_rate: int,
    start: float,
    end: float,
    text: str,
    size_pct: float,
    syllable_count: int = 1,
    escalation_gate: Optional[float] = None,
) -> Optional[list[Optional[float]]]:
    """Per-letter pitch for a sustained loud word (scream glide).

    Mirrors the renderer's letter-sweep rule: the word must be loud
    enough to escalate (size_pct >= escalation_gate x baseline), held
    long enough for a readable letter sweep, and a single syllable -
    multi-syllable words ride the wave per syllable instead.

    Returns a list aligned to the word's non-space letters (None per
    unvoiced letter), or None when the word does not qualify.
    """
    if syllable_count > 1:
        return None
    gate = (
        escalation_gate
        if escalation_gate is not None
        else Style().escalation_gate
    )
    if size_pct < gate * DEFAULT_BASELINE_SIZE_PCT:
        return None
    # Align to the letters the renderer sweeps: the word's non-space
    # characters (ASR word texts can carry surrounding whitespace).
    letters = [ch for ch in text if not ch.isspace()]
    hold = end - start
    if not letters or hold < LETTER_SWEEP_MIN_PER_LETTER_S * max(2, len(letters)):
        return None
    per = hold / len(letters)
    pitches: list[Optional[float]] = []
    voiced = 0
    for k in range(len(letters)):
        p = span_pitch(audio, sample_rate, start + k * per, start + (k + 1) * per)
        if p is not None:
            p = round(p, 1)
            voiced += 1
        pitches.append(p)
    if voiced == 0:
        return None
    return pitches
