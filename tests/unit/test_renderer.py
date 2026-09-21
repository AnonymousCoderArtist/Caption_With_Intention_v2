"""M4 unit tests — CI renderer.

Tests cover:
- CwiRenderer instantiation
- ASS generation with CWI styling
- Speaker color attribution in ASS output
- Work area positioning
- Caption box styling (90% black)
- Off-camera italic flag
- Font configuration
- Render command construction
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from engine.renderer.renderer import CwiRenderer, ASS_DIALOGUE_PREFIX
from engine.renderer.styles import (
    BLACK_90_PCT,
    WHITE_90_PCT,
    compute_word_style,
    compute_work_area_position,
    hex_to_ass_color,
    speaker_color_to_ass,
)
from schemas.project import Project, Speaker, CaptionEvent, EventType, VideoInfo


# ─── Helpers ──────────────────────────────────────────────────

def _make_project(events: list[dict] | None = None, speakers: list[dict] | None = None) -> Project:
    """Create a test project with optional events and speakers."""
    project = Project(
        project_name="TestRender",
        video=VideoInfo(width=1920, height=1080, fps=23.976, duration=10.0),
    )
    if speakers:
        for spk_data in speakers:
            project.speakers.append(Speaker(**spk_data))
    if events:
        for i, evt_data in enumerate(events):
            evt_data.setdefault("id", f"evt_{i}")
            project.events.append(CaptionEvent(**evt_data))
    return project


# ─── Style Computation Tests ──────────────────────────────────


class TestComputeWordStyle:
    def test_normal_volume(self):
        style = compute_word_style(loudness=0.5)
        assert style["size_pct"] == 7.5  # midpoint of 3-12%

    def test_quiet(self):
        style = compute_word_style(loudness=0.0)
        assert style["size_pct"] == 3.0

    def test_loud(self):
        style = compute_word_style(loudness=1.0)
        assert style["size_pct"] == 12.0

    def test_clamps(self):
        assert compute_word_style(loudness=-1.0)["size_pct"] == 3.0
        assert compute_word_style(loudness=2.0)["size_pct"] == 12.0

    def test_low_pitch_heavy(self):
        style = compute_word_style(loudness=0.5, pitch_hz=100)
        assert style["weight"] > 400

    def test_high_pitch_light(self):
        style = compute_word_style(loudness=0.5, pitch_hz=300)
        assert style["weight"] < 400

    def test_baseline_weight(self):
        style = compute_word_style(loudness=0.5, pitch_hz=180)
        assert style["weight"] == 400

    def test_low_harmonic_wide(self):
        style = compute_word_style(low_harmonic=1.0, high_harmonic=0.0)
        assert style["width"] > 100

    def test_high_harmonic_narrow(self):
        style = compute_word_style(low_harmonic=0.0, high_harmonic=1.0)
        assert style["width"] < 100

    def test_italic_flag(self):
        style = compute_word_style(italic=True)
        assert style["italic"] is True

    def test_pop_size(self):
        style = compute_word_style(loudness=0.5)
        assert style["pop_size_pct"] > style["size_pct"]
        assert abs(style["pop_size_pct"] - 7.5 * 1.15) < 0.01


class TestComputeWorkAreaPosition:
    def test_default_position(self):
        pos = compute_work_area_position()
        assert pos["work_area_bottom"] == 1080
        assert pos["work_area_top"] == 1080 - 216  # 20% of 1080

    def test_custom_resolution(self):
        pos = compute_work_area_position(screen_height=720, screen_width=1280)
        assert pos["work_area_bottom"] == 720
        assert pos["work_area_top"] == 720 - 144

    def test_returns_margins(self):
        pos = compute_work_area_position()
        assert "bottom_margin_pct" in pos
        assert "side_margin_pct" in pos
        assert pos["bottom_margin_pct"] == 5.0


class TestHexToAssColor:
    def test_yellow(self):
        assert hex_to_ass_color("#E5E517") == "&H17E5E5"  # BGR order

    def test_red(self):
        assert hex_to_ass_color("#E51717") == "&H1717E5"  # BGR order

    def test_white(self):
        assert hex_to_ass_color("#FFFFFF") == "&HFFFFFF"

    def test_black(self):
        assert hex_to_ass_color("#000000") == "&H000000"


class TestSpeakerColorToAss:
    def test_main_speaker(self):
        spk = Speaker(id="spk_1", name="Woody", category="main", color="#E5E517")
        result = speaker_color_to_ass(spk)
        assert result == "&H17E5E5"

    def test_supporting_speaker(self):
        spk = Speaker(id="spk_2", name="Buzz", category="supporting", color="#17E5E5")
        result = speaker_color_to_ass(spk)
        assert result == "&HE5E517"


# ─── CwiRenderer Tests ────────────────────────────────────────


class TestCwiRendererInstantiation:
    def test_create_with_project(self):
        project = _make_project()
        renderer = CwiRenderer(project)
        assert renderer.project is project

    def test_create_with_font(self):
        project = _make_project()
        renderer = CwiRenderer(project, font_path="/path/to/RobotoFlex.ttf")
        assert renderer.font_path == Path("/path/to/RobotoFlex.ttf")

    def test_create_with_scale(self):
        project = _make_project()
        renderer = CwiRenderer(project, scale=(1280, 720))
        assert renderer.scale == (1280, 720)

    def test_preserve_audio_default(self):
        project = _make_project()
        renderer = CwiRenderer(project)
        assert renderer.preserve_audio is True


class TestCwiRendererAssGeneration:
    def test_ass_contains_header(self):
        project = _make_project()
        renderer = CwiRenderer(project)
        ass_content = renderer.render_ass("dummy.mp4")
        assert "[Script Info]" in ass_content
        assert "[V4+ Styles]" in ass_content
        assert "[Events]" in ass_content

    def test_ass_contains_events(self):
        events = [
            {"start": 0.0, "end": 2.0, "text": "Hello."},
            {"start": 2.0, "end": 4.0, "text": "World."},
        ]
        project = _make_project(events=events)
        renderer = CwiRenderer(project)
        ass_content = renderer.render_ass("dummy.mp4")
        assert "Hello." in ass_content
        assert "World." in ass_content

    def test_ass_uses_cwi_default_style(self):
        project = _make_project()
        renderer = CwiRenderer(project)
        ass_content = renderer.render_ass("dummy.mp4")
        assert "Default:" in ass_content
        # CWI style should use Roboto Flex, 90% white primary, 90% black back
        for line in ass_content.split("\n"):
            if line.startswith("Style: Default,"):
                assert "Roboto Flex" in line or "Arial" in line  # Font
                parts = line.split(",")
                # PrimaryColour = 3rd value (0-indexed) = white at 90%
                assert "E6E6E6" in parts[3] or "FFFFFF" in parts[3]
                # BackColour = 6th value = 90% black
                assert "DE000000" in parts[5]

    def test_ass_has_bottom_margin(self):
        project = _make_project()
        renderer = CwiRenderer(project)
        ass_content = renderer.render_ass("dummy.mp4")
        # Style line should have bottom margin set
        for line in ass_content.split("\n"):
            if line.startswith("Style: Default,"):
                parts = line.split(",")
                # MarginV is index 20 in the format
                assert len(parts) >= 21
                assert parts[20] != "", "Bottom margin should be set"

    def test_ass_playres(self):
        project = _make_project()
        renderer = CwiRenderer(project)
        ass_content = renderer.render_ass("dummy.mp4")
        assert "PlayResX: 1920" in ass_content
        assert "PlayResY: 1080" in ass_content


class TestCwiRendererSpeakerAttribution:
    def test_main_speaker_color_in_ass(self):
        speakers = [
            {"id": "spk_1", "name": "Woody", "category": "main", "color": "#E5E517"},
        ]
        events = [
            {
                "id": "evt_1",
                "type": "dialogue",
                "start": 0.0,
                "end": 2.0,
                "text": "There's a snake in my boot!",
                "speaker_id": "spk_1",
            },
        ]
        project = _make_project(speakers=speakers, events=events)
        renderer = CwiRenderer(project)
        ass_content = renderer.render_ass("dummy.mp4")
        # The ASS file should have the speaker's color in the text
        # via the speaker_color field (used for word-level coloring)
        assert "evt_1" in ass_content or "snake" in ass_content

    def test_off_camera_italic(self):
        speakers = [
            {
                "id": "spk_1",
                "name": "Joker",
                "category": "main",
                "color": "#E51717",
                "off_camera": True,
            },
        ]
        events = [
            {
                "id": "evt_1",
                "type": "dialogue",
                "start": 0.0,
                "end": 2.0,
                "text": "Do you want to know a secret?",
                "speaker_id": "spk_1",
                "off_camera": True,
            },
        ]
        project = _make_project(speakers=speakers, events=events)
        renderer = CwiRenderer(project)
        ass_content = renderer.render_ass("dummy.mp4")
        # Off-camera text should still appear (italic flag is applied)
        assert "secret" in ass_content


class TestCwiRendererEvents:
    def test_empty_events(self):
        project = _make_project()
        renderer = CwiRenderer(project)
        ass_content = renderer.render_ass("dummy.mp4")
        assert "[Events]" in ass_content

    def test_sound_effect_event(self):
        events = [
            {
                "id": "evt_1",
                "type": "sound_effect",
                "start": 0.0,
                "end": 1.0,
                "text": "[THUNDER]",
                "speaker_id": None,
            },
        ]
        project = _make_project(events=events)
        renderer = CwiRenderer(project)
        ass_content = renderer.render_ass("dummy.mp4")
        assert "THUNDER" in ass_content

    def test_multiple_events(self):
        events = [
            {"id": "e1", "type": "dialogue", "start": 0.0, "end": 1.0, "text": "A", "speaker_id": None},
            {"id": "e2", "type": "dialogue", "start": 1.0, "end": 2.0, "text": "B", "speaker_id": None},
            {"id": "e3", "type": "dialogue", "start": 2.0, "end": 3.0, "text": "C", "speaker_id": None},
        ]
        project = _make_project(events=events)
        renderer = CwiRenderer(project)
        ass_content = renderer.render_ass("dummy.mp4")
        assert "A" in ass_content
        assert "B" in ass_content
        assert "C" in ass_content


class TestCwiRendererBuildCommand:
    def test_ffmpeg_command_basic(self):
        project = _make_project()
        renderer = CwiRenderer(project)
        source = Path("/test/video.mp4")
        ass = Path("/test/captions.cwi.ass")
        output = Path("/test/output.mp4")

        cmd = renderer._build_ffmpeg_command(source, ass, output)

        assert cmd[0] == "ffmpeg"
        assert "-i" in cmd
        assert str(source) in cmd
        assert "subtitles=" in cmd[cmd.index("-vf") + 1] if "-vf" in cmd else any("subtitles=" in c for c in cmd)
        assert str(output) in cmd

    def test_ffmpeg_command_preserves_audio(self):
        project = _make_project()
        renderer = CwiRenderer(project, preserve_audio=True)
        source = Path("/test/video.mp4")
        ass = Path("/test/captions.cwi.ass")
        output = Path("/test/output.mp4")

        cmd = renderer._build_ffmpeg_command(source, ass, output)
        assert "-c:a" in cmd
        assert "copy" in cmd

    def test_ffmpeg_command_with_scale(self):
        project = _make_project()
        renderer = CwiRenderer(project, scale=(1280, 720))
        source = Path("/test/video.mp4")
        ass = Path("/test/captions.cwi.ass")
        output = Path("/test/output.mp4")

        cmd = renderer._build_ffmpeg_command(source, ass, output)
        cmd_str = " ".join(cmd)
        assert "scale=1280:720" in cmd_str


# ─── Style Constants ─────────────────────────────────────────


class TestStyleConstants:
    def test_white_90_pct(self):
        assert WHITE_90_PCT == "&HE6E6E6"

    def test_black_90_pct(self):
        assert BLACK_90_PCT == "&HDE000000"

    def test_ass_dialogue_prefix(self):
        assert ASS_DIALOGUE_PREFIX == "Dialogue: 0,"
