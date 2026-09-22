"""Editor API service layer — transport-agnostic JSON interface for the Editor engine.

Provides methods that accept/return JSON-serializable data, suitable for
exposure via IPC, HTTP, or WebChannel to a React/TypeScript frontend.

All methods return dicts (JSON-ready) or primitive types. Errors are returned
as {error: message} dicts rather than raising exceptions, matching the
frontend's expected response shape.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

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

logger = logging.getLogger("caption_with_intention")


class EditorAPI:
    """Transport-agnostic API wrapping the Editor engine.

    All methods return JSON-serializable dicts or primitives.
    Success responses use the data directly; error responses return
    {"error": "<message>"}.

    Args:
        editor: An existing Editor instance. Creates a new one if None.
    """

    def __init__(self, editor: Optional[Editor] = None) -> None:
        self.editor = editor or Editor()

    # ─── Project ─────────────────────────────────────────────────────

    def get_project(self) -> dict[str, Any]:
        """Return the current project as a JSON-serializable dict."""
        try:
            return {"success": True, "data": self.editor.project.model_dump(mode="json")}
        except Exception as exc:
            return {"error": str(exc)}

    def get_project_summary(self) -> dict[str, Any]:
        """Return a lightweight summary of the project state."""
        try:
            project = self.editor.project
            return {
                "success": True,
                "data": {
                    "project_name": project.project_name,
                    "schema_version": project.schema_version,
                    "video": project.video.model_dump(mode="json") if project.video else {},
                    "speaker_count": len(project.speakers),
                    "event_count": len(project.events),
                    "scene_count": len(project.scenes),
                    "modified_at": project.modified_at,
                    "selected_items": self.editor.selected,
                },
            }
        except Exception as exc:
            return {"error": str(exc)}

    # ─── Undo / Redo ─────────────────────────────────────────────────

    def undo(self) -> dict[str, Any]:
        """Undo the last edit."""
        try:
            result = self.editor.undo()
            return {"success": True, "data": {"undid": result, "selected": self.editor.selected}}
        except Exception as exc:
            return {"error": str(exc)}

    def redo(self) -> dict[str, Any]:
        """Redo the last undone edit."""
        try:
            result = self.editor.redo()
            return {"success": True, "data": {"redid": result, "selected": self.editor.selected}}
        except Exception as exc:
            return {"error": str(exc)}

    def can_undo(self) -> dict[str, Any]:
        """Check if undo is available."""
        return {"success": True, "data": {"can_undo": len(self.editor._undo_stack) > 0}}

    def can_redo(self) -> dict[str, Any]:
        """Check if redo is available."""
        return {"success": True, "data": {"can_redo": len(self.editor._redo_stack) > 0}}

    # ─── Speakers ────────────────────────────────────────────────────

    def add_speaker(
        self,
        name: str,
        category: str = "main",
        color: str = "#E5E517",
        role: Optional[str] = None,
        off_camera: bool = False,
    ) -> dict[str, Any]:
        """Add a new speaker."""
        try:
            speaker = self.editor.add_speaker(
                name=name,
                category=SpeakerCategory(category),
                color=color,
                role=role,
                off_camera=off_camera,
            )
            return {"success": True, "data": speaker.model_dump(mode="json")}
        except Exception as exc:
            return {"error": str(exc)}

    def update_speaker(self, speaker_id: str, **kwargs: Any) -> dict[str, Any]:
        """Update speaker properties."""
        try:
            result = self.editor.update_speaker(speaker_id, **kwargs)
            if not result:
                return {"error": f"Speaker {speaker_id} not found"}
            speaker = self.editor._get_speaker(speaker_id)
            return {"success": True, "data": speaker.model_dump(mode="json") if speaker else {}}
        except Exception as exc:
            return {"error": str(exc)}

    def remove_speaker(self, speaker_id: str) -> dict[str, Any]:
        """Remove a speaker."""
        try:
            result = self.editor.remove_speaker(speaker_id)
            if not result:
                return {"error": f"Speaker {speaker_id} not found"}
            return {"success": True, "data": {"removed": speaker_id}}
        except Exception as exc:
            return {"error": str(exc)}

    def get_speakers(self) -> dict[str, Any]:
        """Return all speakers."""
        try:
            speakers = [s.model_dump(mode="json") for s in self.editor.project.speakers]
            return {"success": True, "data": speakers}
        except Exception as exc:
            return {"error": str(exc)}

    # ─── Events ──────────────────────────────────────────────────────

    def add_event(
        self,
        text: str,
        start: float,
        end: float,
        speaker_id: Optional[str] = None,
        event_type: str = "dialogue",
        words: Optional[list[dict]] = None,
    ) -> dict[str, Any]:
        """Add a new caption event."""
        try:
            event = self.editor.add_event(
                text=text,
                start=start,
                end=end,
                speaker_id=speaker_id,
                event_type=event_type,
                words=words,
            )
            return {"success": True, "data": event.model_dump(mode="json")}
        except Exception as exc:
            return {"error": str(exc)}

    def update_event(self, event_id: str, **kwargs: Any) -> dict[str, Any]:
        """Update event properties."""
        try:
            result = self.editor.update_event(event_id, **kwargs)
            if not result:
                return {"error": f"Event {event_id} not found"}
            event = self.editor._get_event(event_id)
            return {"success": True, "data": event.model_dump(mode="json") if event else {}}
        except Exception as exc:
            return {"error": str(exc)}

    def remove_event(self, event_id: str) -> dict[str, Any]:
        """Remove an event."""
        try:
            result = self.editor.remove_event(event_id)
            if not result:
                return {"error": f"Event {event_id} not found"}
            return {"success": True, "data": {"removed": event_id}}
        except Exception as exc:
            return {"error": str(exc)}

    def get_events(self) -> dict[str, Any]:
        """Return all events with their words."""
        try:
            events = []
            for event in self.editor.project.events:
                event_dict = event.model_dump(mode="json")
                events.append(event_dict)
            return {"success": True, "data": events}
        except Exception as exc:
            return {"error": str(exc)}

    # ─── Words ───────────────────────────────────────────────────────

    def add_word(self, event_id: str, text: str, start: float, end: float) -> dict[str, Any]:
        """Add a word to an event."""
        try:
            result = self.editor.add_word(event_id, text, start, end)
            if not result:
                return {"error": f"Event {event_id} not found"}
            event = self.editor._get_event(event_id)
            return {"success": True, "data": event.model_dump(mode="json") if event else {}}
        except Exception as exc:
            return {"error": str(exc)}

    def update_word(self, event_id: str, word_index: int, **kwargs: Any) -> dict[str, Any]:
        """Update word properties."""
        try:
            result = self.editor.update_word(event_id, word_index, **kwargs)
            if not result:
                return {"error": f"Word {word_index} in event {event_id} not found"}
            event = self.editor._get_event(event_id)
            return {"success": True, "data": event.model_dump(mode="json") if event else {}}
        except Exception as exc:
            return {"error": str(exc)}

    def remove_word(self, event_id: str, word_index: int) -> dict[str, Any]:
        """Remove a word from an event."""
        try:
            result = self.editor.remove_word(event_id, word_index)
            if not result:
                return {"error": f"Word {word_index} in event {event_id} not found"}
            event = self.editor._get_event(event_id)
            return {"success": True, "data": event.model_dump(mode="json") if event else {}}
        except Exception as exc:
            return {"error": str(exc)}

    # ─── Syllables ───────────────────────────────────────────────────

    def add_syllable(
        self, event_id: str, word_index: int, text: str, start: float, end: float
    ) -> dict[str, Any]:
        """Add a syllable to a word."""
        try:
            result = self.editor.add_syllable(event_id, word_index, text, start, end)
            if not result:
                return {"error": f"Word {word_index} in event {event_id} not found"}
            event = self.editor._get_event(event_id)
            return {"success": True, "data": event.model_dump(mode="json") if event else {}}
        except Exception as exc:
            return {"error": str(exc)}

    def update_syllable(
        self,
        event_id: str,
        word_index: int,
        syllable_index: int,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Update syllable properties."""
        try:
            result = self.editor.update_syllable(event_id, word_index, syllable_index, **kwargs)
            if not result:
                return {"error": f"Syllable {syllable_index} not found"}
            event = self.editor._get_event(event_id)
            return {"success": True, "data": event.model_dump(mode="json") if event else {}}
        except Exception as exc:
            return {"error": str(exc)}

    # ─── Timing ──────────────────────────────────────────────────────

    def adjust_event_timing(
        self, event_id: str, start_delta: float, end_delta: float
    ) -> dict[str, Any]:
        """Adjust event timing by deltas in seconds."""
        try:
            result = self.editor.adjust_event_timing(event_id, start_delta, end_delta)
            if not result:
                return {"error": f"Event {event_id} not found"}
            event = self.editor._get_event(event_id)
            return {"success": True, "data": event.model_dump(mode="json") if event else {}}
        except Exception as exc:
            return {"error": str(exc)}

    def adjust_word_timing(
        self, event_id: str, word_index: int, start_delta: float, end_delta: float
    ) -> dict[str, Any]:
        """Adjust word timing by deltas in seconds."""
        try:
            result = self.editor.adjust_word_timing(event_id, word_index, start_delta, end_delta)
            if not result:
                return {"error": f"Word {word_index} in event {event_id} not found"}
            event = self.editor._get_event(event_id)
            return {"success": True, "data": event.model_dump(mode="json") if event else {}}
        except Exception as exc:
            return {"error": str(exc)}

    # ─── Typography Inspector ────────────────────────────────────────

    def set_typography(self, event_id: str, **kwargs: Any) -> dict[str, Any]:
        """Set typography properties on an event's style."""
        try:
            result = self.editor.set_typography(event_id, **kwargs)
            if not result:
                return {"error": f"Event {event_id} not found"}
            event = self.editor._get_event(event_id)
            return {"success": True, "data": event.model_dump(mode="json") if event else {}}
        except Exception as exc:
            return {"error": str(exc)}

    # ─── Animation Inspector ─────────────────────────────────────────

    def set_animation(self, event_id: str, **kwargs: Any) -> dict[str, Any]:
        """Set animation properties on an event's style."""
        try:
            result = self.editor.set_animation(event_id, **kwargs)
            if not result:
                return {"error": f"Event {event_id} not found"}
            event = self.editor._get_event(event_id)
            return {"success": True, "data": event.model_dump(mode="json") if event else {}}
        except Exception as exc:
            return {"error": str(exc)}

    # ─── Box / Work-Area Inspector ───────────────────────────────────

    def set_box_properties(self, event_id: str, **kwargs: Any) -> dict[str, Any]:
        """Set caption box properties on an event's style."""
        try:
            result = self.editor.set_box_properties(event_id, **kwargs)
            if not result:
                return {"error": f"Event {event_id} not found"}
            event = self.editor._get_event(event_id)
            return {"success": True, "data": event.model_dump(mode="json") if event else {}}
        except Exception as exc:
            return {"error": str(exc)}

    # ─── Speaker Editor ──────────────────────────────────────────────

    def set_speaker_color(self, speaker_id: str, color: str) -> dict[str, Any]:
        """Set a speaker's color."""
        result = self.editor.set_speaker_color(speaker_id, color)
        if not result:
            return {"error": f"Speaker {speaker_id} not found"}
        speaker = self.editor._get_speaker(speaker_id)
        return {"success": True, "data": speaker.model_dump(mode="json") if speaker else {}}

    def set_speaker_category(self, speaker_id: str, category: str) -> dict[str, Any]:
        """Change a speaker's category."""
        result = self.editor.set_speaker_category(speaker_id, SpeakerCategory(category))
        if not result:
            return {"error": f"Speaker {speaker_id} not found"}
        speaker = self.editor._get_speaker(speaker_id)
        return {"success": True, "data": speaker.model_dump(mode="json") if speaker else {}}

    def set_speaker_off_camera(self, speaker_id: str, off_camera: bool) -> dict[str, Any]:
        """Toggle off-camera status."""
        result = self.editor.set_speaker_off_camera(speaker_id, off_camera)
        if not result:
            return {"error": f"Speaker {speaker_id} not found"}
        speaker = self.editor._get_speaker(speaker_id)
        return {"success": True, "data": speaker.model_dump(mode="json") if speaker else {}}

    # ─── Palette Assignment ──────────────────────────────────────────

    def assign_palette_color(self, speaker_id: str, color: str) -> dict[str, Any]:
        """Assign a palette color to a speaker."""
        result = self.editor.assign_palette_color(speaker_id, color)
        if not result:
            return {"error": f"Speaker {speaker_id} not found"}
        speaker = self.editor._get_speaker(speaker_id)
        return {"success": True, "data": speaker.model_dump(mode="json") if speaker else {}}

    # ─── Scene Overrides ─────────────────────────────────────────────

    def set_scene_override(self, scene_id: str, overrides: dict[str, Any]) -> dict[str, Any]:
        """Set overrides for a scene."""
        try:
            self.editor.set_scene_override(scene_id, overrides)
            return {"success": True, "data": {"scene_id": scene_id, "overrides": overrides}}
        except Exception as exc:
            return {"error": str(exc)}

    # ─── Multi-Select ────────────────────────────────────────────────

    def select(self, item_id: str) -> dict[str, Any]:
        """Add an item to the selection."""
        self.editor.select(item_id)
        return {"success": True, "data": {"selected": self.editor.selected}}

    def deselect(self, item_id: str) -> dict[str, Any]:
        """Remove an item from the selection."""
        self.editor.deselect(item_id)
        return {"success": True, "data": {"selected": self.editor.selected}}

    def select_all(self) -> dict[str, Any]:
        """Select all events."""
        self.editor.select_all()
        return {"success": True, "data": {"selected": self.editor.selected}}

    def clear_selection(self) -> dict[str, Any]:
        """Clear the selection."""
        self.editor.clear_selection()
        return {"success": True, "data": {"selected": []}}

    def apply_to_selection(self, **kwargs: Any) -> dict[str, Any]:
        """Apply property changes to all selected events."""
        try:
            count = self.editor.apply_to_selection(**kwargs)
            return {"success": True, "data": {"affected": count}}
        except Exception as exc:
            return {"error": str(exc)}

    def get_selection(self) -> dict[str, Any]:
        """Return current selection."""
        return {"success": True, "data": {"selected": self.editor.selected}}

    # ─── Copy / Paste Style ──────────────────────────────────────────

    def copy_style(self, source_event_id: str) -> dict[str, Any]:
        """Copy style from an event."""
        try:
            style = self.editor.copy_style(source_event_id)
            if style is None:
                return {"error": f"Event {source_event_id} not found"}
            return {"success": True, "data": {"copied_style": style}}
        except Exception as exc:
            return {"error": str(exc)}

    def paste_style(self, source_event_id: str, target_event_id: str) -> dict[str, Any]:
        """Paste style from one event to another."""
        try:
            result = self.editor.paste_style(source_event_id, target_event_id)
            if not result:
                return {"error": "One or both events not found"}
            event = self.editor._get_event(target_event_id)
            return {
                "success": True,
                "data": event.model_dump(mode="json") if event else {},
            }
        except Exception as exc:
            return {"error": str(exc)}

    # ─── Build from Transcript ───────────────────────────────────────

    def build_from_transcript(
        self,
        transcript: list[dict[str, Any]],
        video_width: int = 1920,
        video_height: int = 1080,
        fps: float = 23.976,
        speakers: Optional[list[dict[str, Any]]] = None,
    ) -> dict[str, Any]:
        """Build a complete CI project from a transcript."""
        try:
            project = self.editor.build_from_transcript(
                transcript=transcript,
                video_width=video_width,
                video_height=video_height,
                fps=fps,
                speakers=speakers,
            )
            return {"success": True, "data": project.model_dump(mode="json")}
        except Exception as exc:
            return {"error": str(exc)}

    # ─── Style Templates ─────────────────────────────────────────────

    def get_default_style(self) -> dict[str, Any]:
        """Return a default Style as a dict."""
        default = Style()
        return {"success": True, "data": default.model_dump(mode="json")}

    def get_speaker_palette_colors(self) -> dict[str, Any]:
        """Return available palette colors from the color rules module."""
        try:
            from engine.rules.colors import (
                MAIN_COLORS,
                SUPPORTING_COLORS,
            )

            palette = list(MAIN_COLORS.values()) + SUPPORTING_COLORS
            return {"success": True, "data": palette}
        except Exception as exc:
            return {"error": str(exc)}
