"""M5 — Full Manual Editor tests.

Tests cover all M5 editor features per spec §M5:

- Caption event editing (add/update/remove)
- Word editing (add/update/remove)
- Syllable editing (add/update)
- Timing editor (event-level and word-level)
- Speaker editor (add/update/remove, color, category)
- Palette assignment
- Typography inspector (size, weight, width)
- Animation inspector (pop_scale, syllable_mode)
- Box/work-area inspector
- Scene overrides
- Undo/redo
- Copy/paste style
- Multi-select edits
- Build from transcript
"""

from __future__ import annotations

import pytest

from engine.editor.editor import Editor, EditAction
from schemas.project import (
    Project,
    Speaker,
    CaptionEvent,
    Word,
    Style,
    EventType,
    SpeakerCategory,
    VideoInfo,
)


# ─── Helpers ──────────────────────────────────────────

def _make_editor() -> Editor:
    project = Project(
        project_name="TestEditor",
        video=VideoInfo(width=1920, height=1080, fps=23.976, duration=10.0),
    )
    return Editor(project=project)


def _make_event(editor: Editor, **kwargs) -> CaptionEvent:
    defaults = {
        "id": f"evt_{len(editor.project.events)}",
        "type": EventType.dialogue,
        "start": 0.0,
        "end": 1.0,
        "speaker_id": None,
        "text": "Test.",
        "style": Style(),
        "words": [],
    }
    defaults.update(kwargs)
    event = CaptionEvent(**defaults)
    editor.project.events.append(event)
    return event


# ─── Undo / Redo ──────────────────────────────────────

class TestUndoRedo:
    def test_undo_updates_event(self):
        editor = _make_editor()
        event = _make_event(editor, text="Original")
        editor.update_event(event.id, text="Changed")
        assert editor.project.events[0].text == "Changed"
        editor.undo()
        assert editor.project.events[0].text == "Original"

    def test_redo_reapplies_change(self):
        editor = _make_editor()
        event = _make_event(editor, text="Original")
        editor.update_event(event.id, text="Changed")
        editor.undo()
        assert editor.project.events[0].text == "Original"
        editor.redo()
        assert editor.project.events[0].text == "Changed"

    def test_undo_empty_stack(self):
        editor = _make_editor()
        assert editor.undo() is False

    def test_redo_empty_stack(self):
        editor = _make_editor()
        assert editor.redo() is False

    def test_new_action_clears_redo(self):
        editor = _make_editor()
        event = _make_event(editor, text="A")
        editor.update_event(event.id, text="B")
        editor.undo()
        editor.update_event(event.id, text="C")
        assert editor.redo() is False

    def test_multiple_undos(self):
        editor = _make_editor()
        event = _make_event(editor, text="A")
        editor.update_event(event.id, text="B")
        editor.update_event(event.id, text="C")
        editor.update_event(event.id, text="D")
        assert editor.undo() is True
        assert editor.undo() is True
        assert editor.project.events[0].text == "B"


# ─── Speaker Operations ───────────────────────────────

class TestSpeakerOperations:
    def test_add_speaker(self):
        editor = _make_editor()
        speaker = editor.add_speaker(
            name="Test Speaker",
            category=SpeakerCategory.main,
            color="#E5E517",
        )
        assert speaker.id.startswith("spk_")
        assert len(editor.project.speakers) == 1

    def test_add_multiple_speakers(self):
        editor = _make_editor()
        editor.add_speaker("Speaker 1")
        editor.add_speaker("Speaker 2")
        assert len(editor.project.speakers) == 2

    def test_update_speaker(self):
        editor = _make_editor()
        speaker = editor.add_speaker("Test")
        editor.update_speaker(speaker.id, color="#FF0000")
        assert editor.project.speakers[0].color == "#FF0000"

    def test_remove_speaker(self):
        editor = _make_editor()
        speaker = editor.add_speaker("Test")
        editor.remove_speaker(speaker.id)
        assert len(editor.project.speakers) == 0

    def test_remove_speaker_reassigns_events(self):
        editor = _make_editor()
        speaker = editor.add_speaker("Test")
        event = _make_event(editor, speaker_id=speaker.id)
        editor.remove_speaker(speaker.id)
        assert event.speaker_id is None

    def test_update_speaker_category(self):
        editor = _make_editor()
        speaker = editor.add_speaker("Test", category=SpeakerCategory.main)
        editor.update_speaker(
            speaker.id, category=SpeakerCategory.supporting
        )
        assert (
            editor.project.speakers[0].category
            == SpeakerCategory.supporting
        )


# ─── Event Operations ─────────────────────────────────

class TestEventOperations:
    def test_add_event(self):
        editor = _make_editor()
        event = editor.add_event(
            text="Hello world.",
            start=0.0,
            end=2.0,
        )
        assert event.id.startswith("evt_")
        assert len(editor.project.events) == 1

    def test_update_event(self):
        editor = _make_editor()
        event = _make_event(editor, text="Original")
        editor.update_event(event.id, text="Updated")
        assert editor.project.events[0].text == "Updated"

    def test_update_event_timing(self):
        editor = _make_editor()
        event = _make_event(editor, start=0.0, end=1.0)
        editor.update_event(event.id, start=0.5, end=2.0)
        assert editor.project.events[0].start == 0.5
        assert editor.project.events[0].end == 2.0

    def test_remove_event(self):
        editor = _make_editor()
        event = _make_event(editor)
        editor.remove_event(event.id)
        assert len(editor.project.events) == 0

    def test_add_event_with_words(self):
        editor = _make_editor()
        event = editor.add_event(
            text="Hello world.",
            start=0.0,
            end=1.0,
            words=[
                {"text": "Hello", "start": 0.0, "end": 0.5},
                {"text": "world.", "start": 0.5, "end": 1.0},
            ],
        )
        assert len(event.words) == 2


# ─── Word Operations ──────────────────────────────────

class TestWordOperations:
    def test_add_word(self):
        editor = _make_editor()
        event = _make_event(editor)
        editor.add_word(event.id, "Test", 0.0, 0.5)
        assert len(event.words) == 1
        assert event.words[0].text == "Test"

    def test_add_multiple_words(self):
        editor = _make_editor()
        event = _make_event(editor)
        editor.add_word(event.id, "Hello", 0.0, 0.3)
        editor.add_word(event.id, "world", 0.3, 0.6)
        assert len(event.words) == 2

    def test_update_word(self):
        editor = _make_editor()
        event = _make_event(editor)
        editor.add_word(event.id, "Original", 0.0, 0.5)
        editor.update_word(event.id, 0, text="Changed", start=0.1)
        assert event.words[0].text == "Changed"
        assert event.words[0].start == 0.1

    def test_update_word_size(self):
        editor = _make_editor()
        event = _make_event(editor)
        editor.add_word(event.id, "Test", 0.0, 0.5)
        editor.update_word(
            event.id, 0, size_pct=8.0, weight=700, width=120
        )
        assert event.words[0].size_pct == 8.0
        assert event.words[0].weight == 700
        assert event.words[0].width == 120

    def test_remove_word(self):
        editor = _make_editor()
        event = _make_event(editor)
        editor.add_word(event.id, "Hello", 0.0, 0.3)
        editor.add_word(event.id, "world", 0.3, 0.6)
        editor.remove_word(event.id, 0)
        assert len(event.words) == 1
        assert event.words[0].text == "world"


# ─── Syllable Operations ──────────────────────────────

class TestSyllableOperations:
    def test_add_syllable(self):
        editor = _make_editor()
        event = _make_event(editor)
        editor.add_word(event.id, "Testing", 0.0, 0.5)
        editor.add_syllable(event.id, 0, "Test", 0.0, 0.25)
        editor.add_syllable(event.id, 0, "ing", 0.25, 0.5)
        assert len(event.words[0].syllables) == 2

    def test_update_syllable(self):
        editor = _make_editor()
        event = _make_event(editor)
        editor.add_word(event.id, "Testing", 0.0, 0.5)
        editor.add_syllable(event.id, 0, "Test", 0.0, 0.25)
        editor.update_syllable(
            event.id, 0, 0, text="Tests", start=0.0, end=0.3
        )
        assert event.words[0].syllables[0]["text"] == "Tests"


# ─── Timing Editor ────────────────────────────────────

class TestTimingEditor:
    def test_adjust_event_timing(self):
        editor = _make_editor()
        event = _make_event(editor, start=1.0, end=3.0)
        editor.adjust_event_timing(event.id, 0.5, 0.5)
        assert event.start == 1.5
        assert event.end == 3.5

    def test_adjust_event_timing_clamps_to_zero(self):
        editor = _make_editor()
        event = _make_event(editor, start=0.5, end=1.0)
        editor.adjust_event_timing(event.id, -1.0, 0.0)
        assert event.start == 0.0

    def test_adjust_word_timing(self):
        editor = _make_editor()
        event = _make_event(editor)
        editor.add_word(event.id, "Test", 0.0, 0.5)
        editor.adjust_word_timing(event.id, 0, 0.5, 0.5)
        assert event.words[0].start == 0.5
        assert event.words[0].end == 1.0


# ─── Typography Inspector ─────────────────────────────

class TestTypographyInspector:
    def test_set_size(self):
        editor = _make_editor()
        event = _make_event(editor)
        editor.set_typography(event.id, size_pct=8.0)
        assert event.style.size_pct == 8.0

    def test_set_weight(self):
        editor = _make_editor()
        event = _make_event(editor)
        editor.set_typography(event.id, weight=700)
        assert event.style.weight == 700

    def test_set_width(self):
        editor = _make_editor()
        event = _make_event(editor)
        editor.set_typography(event.id, width=120)
        assert event.style.width == 120

    def test_set_italic(self):
        editor = _make_editor()
        event = _make_event(editor)
        editor.set_typography(event.id, italic=True)
        assert event.style.italic is True

    def test_set_multiple_typography(self):
        editor = _make_editor()
        event = _make_event(editor)
        editor.set_typography(
            event.id,
            size_pct=8.0,
            weight=700,
            width=120,
            italic=True,
        )
        assert event.style.size_pct == 8.0
        assert event.style.weight == 700
        assert event.style.width == 120
        assert event.style.italic is True


# ─── Animation Inspector ──────────────────────────────

class TestAnimationInspector:
    def test_set_pop_scale(self):
        editor = _make_editor()
        event = _make_event(editor)
        editor.set_animation(event.id, pop_scale=1.25)
        assert event.style.pop_scale == 1.25

    def test_set_syllable_mode(self):
        editor = _make_editor()
        event = _make_event(editor)
        editor.set_animation(event.id, syllable_mode=True)
        assert event.style.syllable_mode is True

    def test_set_pop_easing(self):
        editor = _make_editor()
        event = _make_event(editor)
        editor.set_animation(event.id, pop_easing="ease_in")
        assert event.style.pop_easing == "ease_in"


# ─── Box / Work-Area Inspector ────────────────────────

class TestBoxInspector:
    def test_set_box_opacity(self):
        editor = _make_editor()
        event = _make_event(editor)
        editor.set_box_properties(event.id, box_opacity=0.95)
        assert event.style.box_opacity == 0.95

    def test_set_breakout_permission(self):
        editor = _make_editor()
        event = _make_event(editor)
        editor.set_box_properties(
            event.id, breakout_permission=True
        )
        assert event.style.breakout_permission is True


# ─── Speaker Editor ───────────────────────────────────

class TestSpeakerEditor:
    def test_set_speaker_color(self):
        editor = _make_editor()
        speaker = editor.add_speaker("Test")
        editor.set_speaker_color(speaker.id, "#FF0000")
        assert editor.project.speakers[0].color == "#FF0000"

    def test_set_speaker_off_camera(self):
        editor = _make_editor()
        speaker = editor.add_speaker("Test")
        editor.set_speaker_off_camera(speaker.id, True)
        assert editor.project.speakers[0].off_camera is True

    def test_set_speaker_category(self):
        editor = _make_editor()
        speaker = editor.add_speaker("Test")
        editor.set_speaker_category(
            speaker.id, SpeakerCategory.supporting
        )
        assert (
            editor.project.speakers[0].category
            == SpeakerCategory.supporting
        )


# ─── Palette Assignment ───────────────────────────────

class TestPaletteAssignment:
    def test_assign_palette_color(self):
        editor = _make_editor()
        speaker = editor.add_speaker("Test")
        editor.assign_palette_color(speaker.id, "#17E5E5")
        assert editor.project.speakers[0].color == "#17E5E5"


# ─── Scene Overrides ──────────────────────────────────

class TestSceneOverrides:
    def test_set_scene_override(self):
        editor = _make_editor()
        editor.set_scene_override("scene_1", {"attribution": False})
        assert len(editor.project.scenes) == 1
        assert editor.project.scenes[0]["id"] == "scene_1"
        assert editor.project.scenes[0]["overrides"] == {
            "attribution": False
        }

    def test_update_scene_override(self):
        editor = _make_editor()
        editor.set_scene_override("scene_1", {"attribution": False})
        editor.set_scene_override("scene_1", {"attribution": True})
        assert editor.project.scenes[0]["overrides"] == {
            "attribution": True
        }


# ─── Multi-Select ─────────────────────────────────────

class TestMultiSelect:
    def test_select(self):
        editor = _make_editor()
        editor.add_event(text="A", start=0.0, end=1.0)
        editor.add_event(text="B", start=1.0, end=2.0)
        editor.select("evt_0")
        editor.select("evt_1")
        assert len(editor.selected) == 2

    def test_deselect(self):
        editor = _make_editor()
        editor.add_event(text="A", start=0.0, end=1.0)
        editor.select("evt_0")
        editor.deselect("evt_0")
        assert len(editor.selected) == 0

    def test_select_all(self):
        editor = _make_editor()
        editor.add_event(text="A", start=0.0, end=1.0)
        editor.add_event(text="B", start=1.0, end=2.0)
        editor.select_all()
        assert len(editor.selected) == 2

    def test_clear_selection(self):
        editor = _make_editor()
        editor.add_event(text="A", start=0.0, end=1.0)
        editor.select_all()
        editor.clear_selection()
        assert len(editor.selected) == 0

    def test_apply_to_selection(self):
        editor = _make_editor()
        event1 = editor.add_event(
            text="A", start=0.0, end=1.0
        )
        event2 = editor.add_event(
            text="B", start=1.0, end=2.0
        )
        editor.select(event1.id)
        editor.select(event2.id)
        count = editor.apply_to_selection(text="Updated")
        assert count == 2
        assert editor.project.events[0].text == "Updated"
        assert editor.project.events[1].text == "Updated"


# ─── Copy / Paste Style ───────────────────────────────

class TestCopyPasteStyle:
    def test_copy_style(self):
        editor = _make_editor()
        event = _make_event(editor)
        editor.set_typography(event.id, size_pct=8.0, weight=700)
        style = editor.copy_style(event.id)
        assert style is not None
        assert style["size_pct"] == 8.0
        assert style["weight"] == 700

    def test_paste_style(self):
        editor = _make_editor()
        event1 = _make_event(editor)
        event2 = _make_event(editor)
        editor.set_typography(
            event1.id, size_pct=8.0, weight=700, italic=True
        )
        editor.paste_style(event1.id, event2.id)
        assert event2.style.size_pct == 8.0
        assert event2.style.weight == 700
        assert event2.style.italic is True


# ─── Build from Transcript ───────────────────────────

class TestBuildFromTranscript:
    def test_build_simple_transcript(self):
        editor = _make_editor()
        transcript = [
            {"text": "Hello world.", "start": 0.0, "end": 1.0},
            {"text": "Goodbye.", "start": 1.0, "end": 2.0},
        ]
        project = editor.build_from_transcript(transcript)
        assert len(project.events) == 2
        assert project.events[0].text == "Hello world."
        assert project.events[1].text == "Goodbye."
        # Each event should have words
        assert len(project.events[0].words) == 2  # Hello, world.
        assert len(project.events[1].words) == 1  # Goodbye.

    def test_build_with_speakers(self):
        editor = _make_editor()
        transcript = [{"text": "Hello.", "start": 0.0, "end": 1.0}]
        speakers = [
            {"id": "spk_1", "name": "Test", "category": "main"},
        ]
        project = editor.build_from_transcript(
            transcript, speakers=speakers
        )
        assert len(project.speakers) == 1
        assert project.events[0].speaker_id is None  # Not auto-assigned

    def test_build_sets_video_info(self):
        editor = _make_editor()
        transcript = [
            {"text": "Test.", "start": 0.0, "end": 5.0},
        ]
        project = editor.build_from_transcript(
            transcript,
            video_width=1280,
            video_height=720,
            fps=30.0,
        )
        assert project.video.width == 1280
        assert project.video.height == 720
        assert project.video.fps == 30.0
        assert project.video.duration == 5.0

    def test_build_single_word(self):
        editor = _make_editor()
        transcript = [{"text": "Hi", "start": 0.0, "end": 0.5}]
        project = editor.build_from_transcript(transcript)
        assert len(project.events) == 1
        assert len(project.events[0].words) == 1
        assert project.events[0].words[0].text == "Hi"

    def test_build_empty_transcript(self):
        editor = _make_editor()
        project = editor.build_from_transcript([])
        assert len(project.events) == 0
        assert project.video.duration == 0.0
