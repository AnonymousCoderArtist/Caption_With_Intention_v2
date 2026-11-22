"""Stable motion rules, replacing the rejected held-tail/pitch-cancellation rules.

These test the time/geometry contract rather than the number of ASS lines
or an exact legacy transform string. Visual evidence is still required.
"""
import math
import re

import pytest

from engine.renderer.renderer import (
    AUTO_EMPHASIS_SIZE_RATIO,
    MOTION_LIFT_RATIO,
    MOTION_PITCH_MOD_RATIO,
    MOTION_RISE_MS,
    MOTION_SETTLE_MS,
    CwiRenderer,
    _letter_lift_px,
    _motion_envelope,
    _spoken_size_at,
)
from schemas.project import CaptionEvent, Project, Speaker, Word


def make_renderer(words, **style):
    project = Project(project_name="Motion regression")
    project.speakers = [Speaker(id="s", color="#17E5E5")]
    project.events = [CaptionEvent(
        id="e", start=0, end=3, speaker_id="s", text=" ".join(w.text for w in words),
        words=words, style=style,
    )]
    return CwiRenderer(project)


def runs_at(renderer, t):
    lines = [e for e in renderer._build_cwi_events(1920, 1080)
             if e["type"] == "dialogue" and e["start"] <= t < e["end"]]
    assert len(lines) == 1
    line = lines[0]
    runs = re.findall("\ue000([0-9]+)\ue001([^\ue000]*)", line["text"])
    return [(text, line["span_tags"][int(index)]) for index, text in runs]


def letters_at(renderer, t):
    return [(char, tag) for text, tag in runs_at(renderer, t)
            for char in text if not char.isspace()]


def test_single_cosine_envelope_has_no_hold():
    assert _motion_envelope(0) == 0
    assert _motion_envelope(MOTION_RISE_MS) == pytest.approx(1)
    assert _motion_envelope(MOTION_RISE_MS + MOTION_SETTLE_MS) == 0
    before = [_motion_envelope(t) for t in range(int(MOTION_RISE_MS) + 1)]
    after = [_motion_envelope(t) for t in range(int(MOTION_RISE_MS), 250)]
    assert before == sorted(before)
    assert after == sorted(after, reverse=True)


@pytest.mark.parametrize("pitch", [None, 50, 110, 180, 250, 500])
def test_pitch_cannot_cancel_or_double_the_wave(pitch):
    word = Word(text="a", start=0.5, end=1, pitch_hz=pitch)
    peak = _letter_lift_px(word, 0, 1, 0.56, 54, 1.25)
    assert 54 * (MOTION_LIFT_RATIO - MOTION_PITCH_MOD_RATIO) <= peak + 1e-8
    assert peak <= 54 * (MOTION_LIFT_RATIO + MOTION_PITCH_MOD_RATIO) + 1e-8
    assert _letter_lift_px(word, 0, 1, 1.2, 54, 1.25) == 0


def test_missing_pitch_still_uses_the_same_motion():
    word = Word(text="a", start=0.5, end=1)
    assert _letter_lift_px(word, 0, 1, 0.56, 54, 1.25) == pytest.approx(54 * 0.12)


def test_pop_control_changes_strength_without_canceling_other_letters():
    word = Word(text="a", start=0.5, end=1)
    default = _letter_lift_px(word, 0, 1, 0.56, 54, 1.25)
    assert _letter_lift_px(word, 0, 1, 0.56, 54, 1.5) == pytest.approx(default * 2)
    assert _letter_lift_px(word, 0, 1, 0.56, 54, 1.0) == 0


def test_letter_crest_travels_left_to_right_and_finishes():
    word = Word(text="abc", start=0.5, end=1.1)
    assert _letter_lift_px(word, 0, 3, 0.56, 54, 1.25) > 0
    assert _letter_lift_px(word, 1, 3, 0.56, 54, 1.25) == 0
    assert _letter_lift_px(word, 0, 3, 0.96, 54, 1.25) == 0
    assert _letter_lift_px(word, 2, 3, 0.96, 54, 1.25) > 0
    assert all(_letter_lift_px(word, j, 3, 1.31, 54, 1.25) == 0 for j in range(3))


def test_syllable_boundaries_do_not_restart_an_envelope():
    word = Word(text="test", start=0.5, end=1.5)
    plain = [_letter_lift_px(word, 1, 4, t / 1000, 54, 1.25) for t in range(500, 1600)]
    word.syllables = [{"text": "te", "start": 0.5, "end": 1},
                      {"text": "st", "start": 1, "end": 1.5}]
    syllabified = [_letter_lift_px(word, 1, 4, t / 1000, 54, 1.25) for t in range(500, 1600)]
    assert plain == syllabified


def test_low_pitch_never_leaves_a_below_baseline_tail():
    word = Word(text="low", start=0, end=0.5, pitch_hz=110)
    offsets = [_letter_lift_px(word, j, 3, t / 1000, 54, 1.25)
               for j in range(3) for t in range(1000)]
    assert min(offsets) == 0
    assert max(offsets) > 0
    assert all(_letter_lift_px(word, j, 3, 0.71, 54, 1.25) == 0 for j in range(3))


@pytest.mark.parametrize("size", [3.0, 4.0, 4.9, 5.0, 5.2, 6.0, 7.5])
def test_ordinary_auto_sizes_share_one_fixed_baseline(size):
    word = Word(text="ordinary", start=0.5, end=1, size_pct=size, source_model="test-asr")
    renderer = make_renderer([word])
    _, spans = renderer._compose_word_spans(renderer.project.events[0], 1080)
    assert spans[0]["size_px"] == 54
    assert {_spoken_size_at(spans[0], 54, t / 100) for t in range(150)} == {54}


def test_strong_emphasis_and_manual_whisper_are_not_discarded():
    words = [Word(text="LOUD", start=0, end=1, size_pct=9, source_model="test-asr"),
             Word(text="whisper", start=1, end=2, size_pct=3)]
    renderer = make_renderer(words)
    _, spans = renderer._compose_word_spans(renderer.project.events[0], 1080)
    assert spans[0]["size_px"] == 97
    assert spans[1]["size_px"] == 32
    assert AUTO_EMPHASIS_SIZE_RATIO > 1.5


def test_sustained_emphasis_grows_only_after_a_hold_and_is_capped():
    word = Word(text="WHOOA", start=0, end=2, size_pct=9)
    span = {"word": word, "size_px": 97, "size_cap": 130}
    assert _spoken_size_at(span, 54, 0.2) == pytest.approx(97)
    assert _spoken_size_at(span, 54, 1) > 97
    assert max(_spoken_size_at(span, 54, t / 1000) for t in range(2300)) <= 130
    assert _spoken_size_at(span, 54, 2) == 130
    assert 54 < _spoken_size_at(span, 54, 2.07) < 130
    assert _spoken_size_at(span, 54, 2.141) == 54


def test_rendered_color_starts_on_time_not_before():
    renderer = make_renderer([Word(text="abc", start=0.5, end=1.1)])
    assert all("\\c&HFFFFFF&" in tag and "\\org" not in tag
               for _, tag in letters_at(renderer, 0.4))
    start = letters_at(renderer, 0.501)
    assert "\\t(0,40,\\c&HE5E517&" in start[0][1]
    assert "\\c&HFFFFFF&" in start[-1][1]
    late = letters_at(renderer, 1.11)
    assert all("\\c&HE5E517&" in tag for _, tag in late)


@pytest.mark.parametrize("duration,probe", [(2.0, 1.8), (0.3, 0.29)])
def test_rendered_sweep_reaches_the_last_letter_within_the_word(duration, probe):
    renderer = make_renderer([Word(text="WHOOOOOA", start=0, end=duration, size_pct=9)])
    early = letters_at(renderer, 0.001)
    late = letters_at(renderer, probe)
    assert "\\c&HFFFFFF&" in early[-1][1]
    assert "\\c&HE5E517&" in late[-1][1]


def test_rendered_words_are_flat_after_the_envelope():
    renderer = make_renderer([Word(text="test", start=0.5, end=1)])
    for _, tag in runs_at(renderer, 1.25):
        assert "\\org" not in tag
        assert "\\fs54.000" in tag


def test_rendered_geometry_is_bounded_across_every_sample():
    renderer = make_renderer([Word(text="test", start=0.5, end=1, pitch_hz=500)])
    angles = [float(x) for line in renderer._build_cwi_events(1920, 1080)
              for tag in line.get("span_tags", [])
              for x in re.findall(r"\\frz(-?[0-9.]+)", tag)]
    assert angles
    max_degrees = math.degrees(54 * 0.14 / 100960) + 1e-5
    assert all(0 <= x <= max_degrees for x in angles)


def test_line_fitting_uses_the_effective_automatic_baseline():
    words = [Word(text="ordinary", start=i * 0.15, end=(i + 1) * 0.15,
                  size_pct=3, source_model="test-asr") for i in range(12)]
    renderer = make_renderer(words)
    event = renderer.project.events[0]
    children = renderer._split_event_lines(event, 1920, 1080)
    assert len(children) == 2
    for child, _ in children:
        _, spans = renderer._compose_word_spans(child, 1080)
        assert all(span["size_px"] == 54 for span in spans)


def test_ordinary_box_geometry_never_pulses_or_changes_height():
    word = Word(text="ordinary", start=0.5, end=1, size_pct=5.2,
                width=102, source_model="test-asr")
    renderer = make_renderer([word])
    boxes = [line for line in renderer._build_cwi_events(1920, 1080)
             if line["type"] == "box"]
    assert boxes
    assert len({tuple(line.get("span_tags", [])) for line in boxes}) == 1
    assert all("\\fs54" in tag and "\\fsp0.000" in tag
               for line in boxes for tag in line["span_tags"])
