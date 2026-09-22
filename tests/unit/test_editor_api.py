"""Tests for the Editor API service layer."""

import pytest
from engine.editor.api import EditorAPI
from engine.editor.editor import Editor
from schemas.project import Project, Speaker, CaptionEvent, Word, Style, EventType, VideoInfo


class TestEditorAPI:
    """Test the transport-agnostic Editor API."""

    @pytest.fixture
    def api(self):
        """Create an EditorAPI with a populated project."""
        editor = Editor()

        # Add speakers
        editor.add_speaker(name="Alice", category="main", color="#E5E517")
        editor.add_speaker(name="Bob", category="supporting", color="#FF6B6B")

        # Add events
        editor.add_event(
            text="Hello there",
            start=0.0,
            end=3.0,
            speaker_id="spk_001",
            event_type="dialogue",
            words=[
                {"text": "Hello", "start": 0.0, "end": 1.5},
                {"text": "there", "start": 1.5, "end": 3.0},
            ],
        )

        editor.add_event(
            text="Background music",
            start=3.0,
            end=5.0,
            event_type="music",
        )

        return EditorAPI(editor)

    # ─── Project ─────────────────────────────────────

    def test_get_project(self, api):
        result = api.get_project()
        assert result["success"] is True
        assert "data" in result
        project = result["data"]
        assert project["project_name"] == "Untitled"
        assert len(project["speakers"]) == 2
        assert len(project["events"]) == 2

    def test_get_project_summary(self, api):
        result = api.get_project_summary()
        assert result["success"] is True
        data = result["data"]
        assert data["speaker_count"] == 2
        assert data["event_count"] == 2
        assert data["scene_count"] == 0
        assert data["selected_items"] == []

    # ─── Undo / Redo ─────────────────────────────────

    def test_undo_redo(self, api):
        # Clear pre-existing undo actions from fixture setup
        editor = api.editor
        editor._undo_stack.clear()
        editor._redo_stack.clear()

        # Undo with empty stack should report undid=False
        result = api.undo()
        assert result["success"] is True
        assert result["data"]["undid"] is False

        # Make an action via the editor directly (bypasses API's response handling)
        event = editor.add_event(text="test", start=0.0, end=1.0)

        # Now undo should work
        result = api.undo()
        assert result["success"] is True
        assert result["data"]["undid"] is True

        # Event should be back to 2 events (undo removed the added one)
        assert len(editor.project.events) == 2

        # Redo should work
        result = api.redo()
        assert result["success"] is True
        assert result["data"]["redid"] is True

        # Event should be back to 3 events
        assert len(editor.project.events) == 3

    # ─── Speakers ────────────────────────────────────

    def test_add_speaker(self, api):
        result = api.add_speaker(name="Charlie", category="minor")
        assert result["success"] is True
        assert result["data"]["name"] == "Charlie"
        assert result["data"]["category"] == "minor"

    def test_update_speaker(self, api):
        result = api.update_speaker("spk_001", name="Alicia")
        assert result["success"] is True
        assert result["data"]["name"] == "Alicia"

    def test_remove_speaker(self, api):
        result = api.remove_speaker("spk_002")
        assert result["success"] is True

        # Verify removed
        speakers = api.get_speakers()
        assert speakers["success"] is True
        assert len(speakers["data"]) == 1
        assert speakers["data"][0]["id"] == "spk_001"

    def test_get_speakers(self, api):
        result = api.get_speakers()
        assert result["success"] is True
        assert len(result["data"]) == 2
        assert result["data"][0]["name"] == "Alice"

    # ─── Events ──────────────────────────────────────

    def test_add_event(self, api):
        result = api.add_event(
            text="New event",
            start=5.0,
            end=7.0,
            speaker_id="spk_001",
            event_type="dialogue",
        )
        assert result["success"] is True
        assert result["data"]["text"] == "New event"
        assert result["data"]["start"] == 5.0

    def test_remove_event(self, api):
        result = api.remove_event("evt_001")
        assert result["success"] is True

        events = api.get_events()
        assert len(events["data"]) == 1
        assert events["data"][0]["id"] == "evt_002"

    def test_get_events(self, api):
        result = api.get_events()
        assert result["success"] is True
        assert len(result["data"]) == 2

    # ─── Words ───────────────────────────────────────

    def test_add_word(self, api):
        result = api.add_word("evt_001", "test", 0.5, 1.0)
        assert result["success"] is True
        event = result["data"]
        assert len(event["words"]) == 3

    def test_update_word(self, api):
        result = api.update_word("evt_001", 0, text="Hi")
        assert result["success"] is True
        assert result["data"]["words"][0]["text"] == "Hi"

    def test_remove_word(self, api):
        result = api.remove_word("evt_001", 0)
        assert result["success"] is True
        assert len(result["data"]["words"]) == 1

    # ─── Timing ──────────────────────────────────────

    def test_adjust_event_timing(self, api):
        event = api.editor.project.events[0]
        original_start = event.start
        result = api.adjust_event_timing("evt_001", 2.0, 2.0)
        assert result["success"] is True
        assert result["data"]["start"] == original_start + 2.0

    def test_adjust_word_timing(self, api):
        event = api.editor.project.events[0]
        original_start = event.words[0].start
        result = api.adjust_word_timing("evt_001", 0, 1.0, 1.0)
        assert result["success"] is True
        # Word start should have been increased by 1.0
        assert result["data"]["words"][0]["start"] == original_start + 1.0

    # ─── Typography ──────────────────────────────────

    def test_set_typography(self, api):
        result = api.set_typography("evt_001", size_pct=10.0, weight=700)
        assert result["success"] is True
        assert result["data"]["style"]["size_pct"] == 10.0
        assert result["data"]["style"]["weight"] == 700

    # ─── Animation ─────────────────────────────────────────

    def test_set_animation(self, api):
        result = api.set_animation("evt_001", pop_scale=1.5, syllable_mode=True)
        assert result["success"] is True
        assert result["data"]["style"]["pop_scale"] == 1.5
        assert result["data"]["style"]["syllable_mode"] is True

    # ─── Box Properties ───────────────────────────

    def test_set_box_properties(self, api):
        result = api.set_box_properties(
            "evt_001", box_opacity=0.5, box_padding=20
        )
        assert result["success"] is True
        assert result["data"]["style"]["box_opacity"] == 0.5
        assert result["data"]["style"]["box_padding"] == 20

    # ─── Speaker Editor ──────────────────────────────

    def test_set_speaker_color(self, api):
        result = api.set_speaker_color("spk_001", "#000000")
        assert result["success"] is True
        assert result["data"]["color"] == "#000000"

    def test_set_speaker_category(self, api):
        result = api.set_speaker_category("spk_001", "minor")
        assert result["success"] is True
        assert result["data"]["category"] == "minor"

    def test_set_speaker_off_camera(self, api):
        result = api.set_speaker_off_camera("spk_001", True)
        assert result["success"] is True
        assert result["data"]["off_camera"] is True

    def test_assign_palette_color(self, api):
        result = api.assign_palette_color("spk_001", "#FF0000")
        assert result["success"] is True
        assert result["data"]["color"] == "#FF0000"

    # ─── Scene Overrides ─────────────────────────────

    def test_set_scene_override(self, api):
        result = api.set_scene_override("scene_001", {"opacity": 0.5})
        assert result["success"] is True
        assert result["data"]["scene_id"] == "scene_001"

    # ─── Multi-Select ────────────────────────────────

    def test_selection(self, api):
        api.select("evt_001")
        result = api.get_selection()
        assert result["success"] is True
        assert "evt_001" in result["data"]["selected"]

        api.deselect("evt_001")
        result = api.get_selection()
        assert result["data"]["selected"] == []

        api.select_all()
        result = api.get_selection()
        assert len(result["data"]["selected"]) == 2

        api.clear_selection()
        result = api.get_selection()
        assert result["data"]["selected"] == []

    def test_apply_to_selection(self, api):
        api.select("evt_001")
        result = api.apply_to_selection(text="Updated")
        assert result["success"] is True
        assert result["data"]["affected"] >= 0

    # ─── Copy / Paste Style ──────────────────────────

    def test_copy_style(self, api):
        result = api.copy_style("evt_001")
        assert result["success"] is True
        assert "copied_style" in result["data"]
        assert result["data"]["copied_style"]["size_pct"] == 5.0

    def test_paste_style(self, api):
        # Copy from evt_001
        api.copy_style("evt_001")
        # Paste to evt_002
        result = api.paste_style("evt_001", "evt_002")
        assert result["success"] is True
        assert result["data"]["style"]["size_pct"] == 5.0

    # ─── Default Style ─────────────────────────────────

    def test_get_default_style(self, api):
        result = api.get_default_style()
        assert result["success"] is True
        assert result["data"]["size_pct"] == 5.0

    # ─── Build from Transcript ───────────────────────

    def test_build_from_transcript(self, api):
        transcript = [
            {"text": "Hello world", "start": 0.0, "end": 2.0},
            {"text": "Goodbye", "start": 3.0, "end": 4.0},
        ]
        result = api.build_from_transcript(
            transcript=transcript,
            video_width=1280,
            video_height=720,
            fps=30.0,
            speakers=[
                {"name": "Charlie", "category": "main", "color": "#00FF00"},
            ],
        )
        assert result["success"] is True
        project = result["data"]
        assert len(project["events"]) >= 2
        assert project["video"]["width"] == 1280
        assert project["video"]["height"] == 720

    # ─── Error handling ──────────────────────────────

    def test_remove_nonexistent_speaker(self, api):
        result = api.remove_speaker("spk_999")
        assert "error" in result

    def test_update_nonexistent_event(self, api):
        result = api.update_event("evt_999", text="test")
        assert "error" in result
