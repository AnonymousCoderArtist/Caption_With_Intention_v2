"""M0 unit tests — project foundation, colors, and typography constants."""

from __future__ import annotations

import json
import pytest
import tempfile
import os
from pathlib import Path

from schemas.project import Project, Speaker, CaptionEvent, EventType, VideoInfo, SpeakerCategory
from engine.rules.colors import (
    MAIN_COLORS,
    SUPPORTING_COLORS,
    color_distance_hex,
    generate_minor_palette,
    generate_minor_color,
    validate_palette_collision,
    assign_speaker_color,
)
from engine.typography.mapping import (
    volume_to_size,
    pitch_to_weight,
    harmonics_to_width,
    compute_word_typography,
)
from engine.project.format import build_project_structure, PROJECT_EXTENSION


# ─── Color Tests ────────────────────────────────────────────────────────


class TestMainColors:
    def test_main_colors_count(self):
        assert len(MAIN_COLORS) == 6

    def test_main_color_values(self):
        assert MAIN_COLORS["yellow"] == "#E5E517"
        assert MAIN_COLORS["blue_cyan"] == "#17E5E5"
        assert MAIN_COLORS["red"] == "#E51717"
        assert MAIN_COLORS["orange"] == "#E58017"
        assert MAIN_COLORS["green"] == "#17E517"
        assert MAIN_COLORS["pink"] == "#E517E5"


class TestSupportingColors:
    def test_supporting_colors_count(self):
        assert len(SUPPORTING_COLORS) == 12


class TestColorDistance:
    def test_same_color_zero_distance(self):
        d = color_distance_hex("#E5E517", "#E5E517")
        assert d >= 0

    def test_different_colors_positive_distance(self):
        d1 = color_distance_hex("#E5E517", "#17E5E5")
        d2 = color_distance_hex("#E5E517", "#E51717")
        assert d1 > 0 and d2 > 0
        # Yellow and cyan should be far apart
        assert d1 > 30

    def test_main_colors_different_from_each_other(self):
        colors = list(MAIN_COLORS.values())
        for i, c1 in enumerate(colors):
            for c2 in colors[i + 1:]:
                d = color_distance_hex(c1, c2)
                assert d > 20, f"{c1} and {c2} too close: {d}"


class TestMinorPalette:
    def test_minor_palette_count(self):
        palette = generate_minor_palette(24)
        assert len(palette) == 24

    def test_minor_palette_all_unique(self):
        palette = generate_minor_palette(24)
        assert len(set(palette)) == 24

    def test_minor_palette_pastel(self):
        palette = generate_minor_palette(24)
        for color in palette:
            h, s, v = __import__("colorsys").rgb_to_hsv(
                int(color[1:3], 16) / 255,
                int(color[3:5], 16) / 255,
                int(color[5:7], 16) / 255,
            )
            assert abs(s - 0.30) < 0.01 or s <= 0.30
            assert v >= 0.85


class TestPaletteAssignment:
    def test_assign_main_color(self):
        from schemas.project import Speaker, SpeakerCategory
        spk = Speaker(id="spk_1", name="Hero", category=SpeakerCategory.main)
        color = assign_speaker_color(spk)
        assert color in MAIN_COLORS.values()

    def test_assign_supporting_color(self):
        spk = Speaker(id="spk_2", name="Support", category=SpeakerCategory.supporting)
        color = assign_speaker_color(spk)
        assert color in SUPPORTING_COLORS

    def test_assign_minor_color(self):
        spk = Speaker(id="spk_3", name="Minor", category=SpeakerCategory.minor)
        color = assign_speaker_color(spk)
        assert color.startswith("#")


# ─── Typography Tests ────────────────────────────────────────────────────


class TestVolumeToSize:
    def test_quiet_is_minimum(self):
        size = volume_to_size(0.0)
        assert size == 3.0

    def test_loud_is_maximum(self):
        size = volume_to_size(1.0)
        assert size == 12.0

    def test_normal_is_approximate_baseline(self):
        size = volume_to_size(0.42)  # ~50% loudness
        assert 3.0 <= size <= 12.0

    def test_clamps_to_range(self):
        assert volume_to_size(-1.0) == 3.0
        assert volume_to_size(2.0) == 12.0


class TestPitchToWeight:
    def test_baseline_pitch_neutral(self):
        weight = pitch_to_weight(180)
        assert weight == 400

    def test_low_pitch_heavy(self):
        weight = pitch_to_weight(100)
        assert weight > 400

    def test_high_pitch_light(self):
        weight = pitch_to_weight(300)
        assert weight < 400

    def test_none_pitch_returns_baseline(self):
        weight = pitch_to_weight(None)
        assert weight == 400


class TestHarmonicsToWidth:
    def test_low_harmonic_dominant_wide(self):
        width = harmonics_to_width(1.0, 0.0)
        assert width > 100

    def test_high_harmonic_dominant_narrow(self):
        width = harmonics_to_width(0.0, 1.0)
        assert width < 100

    def test_equal_harmonics_mid(self):
        width = harmonics_to_width(0.5, 0.5)
        assert 40 < width < 120


class TestComputeWordTypography:
    def test_quiet_low_pitch_wide(self):
        result = compute_word_typography(0.1, 100, 0.9, 0.1)
        assert result["size_pct"] <= 5.0
        assert result["weight"] > 400
        assert result["width"] > 100

    def test_loud_high_pitch_narrow(self):
        result = compute_word_typography(0.9, 300, 0.1, 0.9)
        assert result["size_pct"] >= 5.0
        assert result["weight"] < 400
        assert result["width"] < 100


# ─── Project Format Tests ────────────────────────────────────────────────


class TestProjectStructure:
    def test_build_creates_directories(self, tmp_path):
        base = build_project_structure(tmp_path)
        assert base.exists()
        assert (base / "analysis").exists()
        assert (base / "captions").exists()
        assert (base / "cache").exists()

    def test_project_extension(self):
        assert PROJECT_EXTENSION == ".ci"


# ─── Schema Tests ────────────────────────────────────────────────────────


class TestProjectSchema:
    def test_create_minimal_project(self):
        project = Project(project_name="Test")
        assert project.project_name == "Test"
        assert project.schema_version == "ci-project-1"
        assert project.design_system == "caption-with-intention-v1.0"

    def test_project_serialization(self, tmp_path):
        project = Project(project_name="TestProject")
        data = project.model_dump()
        assert "schema_version" in data
        assert "speakers" in data
        assert "events" in data

    def test_speaker_model(self):
        spk = Speaker(id="spk_1", name="Character A", category="main", color="#E5E517")
        assert spk.id == "spk_1"
        assert spk.category.value == "main"

    def test_event_model(self):
        event = CaptionEvent(
            id="evt_1",
            type=EventType.dialogue,
            start=0.0,
            end=2.0,
            text="Hello.",
        )
        assert event.start == 0.0
        assert event.text == "Hello."
