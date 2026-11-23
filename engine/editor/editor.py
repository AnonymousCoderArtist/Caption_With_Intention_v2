"""Manual editor engine — build and edit CI caption projects by hand.

Provides:
- CRUD operations for speakers, events, words, syllables
- Timing editor (event-level and word-level)
- Property inspectors (typography, animation, box, work area, speaker, palette)
- Scene overrides
- Undo/redo history
- Copy/paste style
- Multi-select editing
- Build complete CI project from a transcript
"""

from __future__ import annotations

import logging
import copy
from typing import Any, Optional

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

# Word fields accepted from transcript entries (M6 ASR output)
_WORD_FIELDS = {
    "text",
    "start",
    "end",
    "size_pct",
    "weight",
    "width",
    "color",
    "opacity",
    "italic",
    "confidence",
    "source_model",
    "source_timestamp",
    "manual_override",
    "syllables",
    "letter_pitches",
    "character_colors",
    "pitch_hz",
}


class EditAction:
    """Represents a single editable action for undo/redo."""

    def __init__(
        self,
        action_type: str,
        target_id: str,
        before: dict | None,
        after: dict | None,
    ) -> None:
        self.action_type = action_type
        self.target_id = target_id
        self.before = before or {}
        self.after = after or {}


class Editor:
    """Manual editor for Caption With Intention projects.

    Provides a complete API for building and editing CI caption projects
    without AI dependency. All changes are tracked for undo/redo.

    Args:
        project: The project to edit. If None, creates a new empty project.
    """

    def __init__(self, project: Optional[Project] = None) -> None:
        self.project: Project = project or Project(project_name="Untitled")
        self._undo_stack: list[EditAction] = []
        self._redo_stack: list[EditAction] = []
        self._selected: list[str] = []

    # ─── Undo / Redo ─────────────────────────────────────────

    def undo(self) -> bool:
        """Undo the last edit. Returns True if successful."""
        if not self._undo_stack:
            return False
        action = self._undo_stack.pop()
        self._apply_action(action, undo=True)
        self._redo_stack.append(action)
        logger.info("Undo: %s on %s", action.action_type, action.target_id)
        return True

    def redo(self) -> bool:
        """Redo the last undone edit. Returns True if successful."""
        if not self._redo_stack:
            return False
        action = self._redo_stack.pop()
        self._apply_action(action, undo=False)
        self._undo_stack.append(action)
        logger.info("Redo: %s on %s", action.action_type, action.target_id)
        return True

    def _apply_action(self, action: EditAction, undo: bool) -> None:
        """Apply or reverse an edit action."""
        action_type = action.action_type

        if action_type == "update_project":
            self.project = Project.model_validate(action.before if undo else action.after)
            self.project.modified_at = self._now_iso()
            return
        # Event snapshots preserve nested models and exact word timing.
        state = action.before if undo else action.after
        if action_type in {"update_event", "add_word", "remove_word", "update_word"}:
            event_id = action.target_id.split("_w_")[0]
            event = self._get_event(event_id)
            if event is not None and "words" in state:
                restored = CaptionEvent.model_validate(state)
                for key in type(restored).model_fields:
                    setattr(event, key, getattr(restored, key))
                self.project.modified_at = self._now_iso()
                return
        if action_type in {"set_typography", "set_animation", "set_box_properties", "set_style", "paste_style"}:
            event = self._get_event(action.target_id)
            if event is not None:
                event.style = Style.model_validate(state)
                self.project.modified_at = self._now_iso()
            return

        # Handle list-modifying actions
        if action_type in ("add_event", "add_speaker", "add_word"):
            if undo:
                # Undo add = remove element
                self._reverse_add(action)
            else:
                # Redo add = re-add element from after state
                self._reapply_add(action)
            self.project.modified_at = self._now_iso()
            return

        if action_type in ("remove_event", "remove_speaker", "remove_word"):
            if undo:
                # Undo remove = re-add element
                self._reverse_remove(action)
            else:
                # Redo remove = remove element again
                self._reapply_remove(action)
            self.project.modified_at = self._now_iso()
            return

        # Standard property-update actions
        state = action.before if undo else action.after
        target = self._find_target(action.target_id)
        if target is None:
            return

        for key, value in state.items():
            if hasattr(target, key):
                setattr(target, key, value)
        self.project.modified_at = self._now_iso()

    def _reapply_add(self, action: EditAction) -> None:
        """Re-add a previously removed element (redo of add)."""
        state = action.after
        if action.action_type == "add_event":
            event = CaptionEvent(**state)
            self.project.events.append(event)
        elif action.action_type == "add_speaker":
            speaker = Speaker(**state)
            self.project.speakers.append(speaker)
        elif action.action_type == "add_word":
            parts = action.target_id.split("_w_")
            if len(parts) == 2:
                event_id, word_text = parts
                event = self._get_event(event_id)
                if event:
                    # Check if word already exists
                    if not any(w.text == word_text for w in event.words):
                        event.words.append(
                            Word(text=word_text, start=0.0, end=0.0)
                        )

    def _reverse_add(self, action: EditAction) -> None:
        """Reverse an add action by removing the added element."""
        if action.action_type == "add_event":
            self.project.events = [
                e for e in self.project.events if e.id != action.target_id
            ]
        elif action.action_type == "add_speaker":
            self.project.speakers = [
                s for s in self.project.speakers if s.id != action.target_id
            ]
        elif action.action_type == "add_word":
            # target_id format: "evt_XXX_w_YYY" or "evt_XXX_w_word_text"
            parts = action.target_id.split("_w_")
            if len(parts) == 2:
                event_id, word_text = parts
                event = self._get_event(event_id)
                if event and event.words:
                    # Try to remove by index first, then by text
                    try:
                        idx = int(word_text)
                        if 0 <= idx < len(event.words):
                            event.words.pop(idx)
                    except ValueError:
                        event.words = [w for w in event.words if w.text != word_text]

    def _reapply_remove(self, action: EditAction) -> None:
        """Re-remove an element (redo of remove)."""
        if action.action_type == "remove_event":
            self.project.events = [
                e for e in self.project.events if e.id != action.target_id
            ]
        elif action.action_type == "remove_speaker":
            self.project.speakers = [
                s for s in self.project.speakers if s.id != action.target_id
            ]
        elif action.action_type == "remove_word":
            parts = action.target_id.split("_w_")
            if len(parts) == 2:
                event_id, word_text = parts
                event = self._get_event(event_id)
                if event:
                    event.words = [w for w in event.words if w.text != word_text]

    def _reverse_remove(self, action: EditAction) -> None:
        """Reverse a remove action by re-adding the removed element."""
        state = action.before
        if action.action_type == "remove_event":
            event = CaptionEvent(**state)
            self.project.events.append(event)
        elif action.action_type == "remove_speaker":
            speaker = Speaker(**state)
            self.project.speakers.append(speaker)
        elif action.action_type == "remove_word":
            syllable = state.get("syllable")
            if syllable and isinstance(syllable, dict):
                pass  # word-level undo handled via event property restore

    def _find_target(self, target_id: str) -> Any:
        """Find a project element by ID."""
        for speaker in self.project.speakers:
            if speaker.id == target_id:
                return speaker
        for event in self.project.events:
            if event.id == target_id:
                return event
            for word in event.words:
                if word.text == target_id or f"{event.id}_w_{word.text}" == target_id:
                    return word
        return None

    @staticmethod
    def _next_id(prefix: str, items: list) -> str:
        used = {item.id for item in items}
        n = 1
        while f"{prefix}_{n:03d}" in used:
            n += 1
        return f"{prefix}_{n:03d}"

    # ─── Speaker Operations ──────────────────────────────────

    def add_speaker(
        self,
        name: str,
        category: SpeakerCategory = SpeakerCategory.main,
        color: str = "#E5E517",
        role: Optional[str] = None,
        off_camera: bool = False,
    ) -> Speaker:
        """Add a new speaker to the project."""
        speaker = Speaker(
            id=self._next_id("spk", self.project.speakers),
            name=name,
            category=category,
            color=color,
            role=role,
            off_camera=off_camera,
        )
        self.project.speakers.append(speaker)
        self._record_action("add_speaker", speaker.id, {}, speaker.model_dump())
        self._save()
        logger.info("Added speaker: %s (%s)", name, category)
        return speaker

    def update_speaker(self, speaker_id: str, **kwargs: Any) -> bool:
        """Update speaker properties."""
        speaker = self._get_speaker(speaker_id)
        if speaker is None:
            return False
        before = speaker.model_dump()
        data = {**before, **{key: value for key, value in kwargs.items() if key in Speaker.model_fields and key != "id"}}
        candidate = Speaker.model_validate(data)
        import re
        if not re.fullmatch(r"#[0-9a-fA-F]{6}", candidate.color):
            raise ValueError("Speaker color must be a six-digit hex color")
        for key in type(candidate).model_fields:
            setattr(speaker, key, getattr(candidate, key))
        after = speaker.model_dump()
        self._record_action("update_speaker", speaker_id, before, after)
        self._save()
        return True

    def remove_speaker(self, speaker_id: str) -> bool:
        """Remove a speaker and reassign their events to no-speaker."""
        speaker = self._get_speaker(speaker_id)
        if speaker is None:
            return False
        before = self.project.model_dump()
        for event in self.project.events:
            if event.speaker_id == speaker_id:
                event.speaker_id = None
                event.speaker_reviewed = False
        self.project.speakers = [s for s in self.project.speakers if s.id != speaker_id]
        self._record_action("update_project", "project", before, self.project.model_dump())
        self._save()
        return True

    # ─── Event Operations ────────────────────────────────────

    def add_event(
        self,
        text: str,
        start: float,
        end: float,
        speaker_id: Optional[str] = None,
        event_type: str = "dialogue",
        words: Optional[list[dict]] = None,
    ) -> CaptionEvent:
        """Add a new caption event."""
        try:
            etype = EventType(event_type)
        except ValueError:
            etype = EventType.dialogue
        event = CaptionEvent(
            id=self._next_id("evt", self.project.events),
            type=etype,
            start=start,
            end=end,
            speaker_id=speaker_id,
            text=text,
        )
        if words:
            event.words = [Word(**w) if isinstance(w, dict) else w for w in words]
        self._validate_event_timing(event)
        self.project.events.append(event)
        self._record_action(
            "add_event",
            event.id,
            {},
            event.model_dump(),
        )
        self._save()
        logger.info("Added event: %s at %.2f-%.2f", text, start, end)
        return event

    def update_event(self, event_id: str, **kwargs: Any) -> bool:
        """Update event properties."""
        event = self._get_event(event_id)
        if event is None:
            return False
        before = event.model_dump()
        updates = {k: v for k, v in kwargs.items() if k in CaptionEvent.model_fields and k != "id"}
        data = {**copy.deepcopy(before), **updates}
        if "text" in updates and "words" not in updates:
            tokens = data["text"].split()
            old_words = before["words"]
            if len(tokens) == len(old_words):
                data["words"] = [{**w, "text": token, "character_colors": w.get("character_colors") if token == w["text"] else None} for w, token in zip(old_words, tokens)]
            else:
                # Text-count changes explicitly redistribute timing across the event.
                span = data["end"] - data["start"]
                data["words"] = [Word(text=token, start=data["start"] + i * span / len(tokens),
                                      end=data["start"] + (i + 1) * span / len(tokens)).model_dump()
                                 for i, token in enumerate(tokens)]
        if ("start" in updates or "end" in updates) and "words" not in updates and "text" not in updates:
            old_span = before["end"] - before["start"]
            new_span = data["end"] - data["start"]
            def retime(t: float) -> float:
                return data["start"] + (t - before["start"]) * new_span / max(old_span, 0.001)
            for word in data["words"]:
                word["start"], word["end"] = retime(word["start"]), retime(word["end"])
                if word.get("syllables"):
                    word["syllables"] = [{**sy, "start": retime(sy["start"]), "end": retime(sy["end"])} for sy in word["syllables"]]
        candidate = CaptionEvent.model_validate(data)
        self._validate_event_timing(candidate)
        for key in type(candidate).model_fields:
            setattr(event, key, getattr(candidate, key))
        self._record_action("update_event", event_id, before, event.model_dump())
        self._save()
        return True

    def assign_speaker_events(self, event_ids: list[str], speaker_id: Optional[str], reviewed: bool = True) -> bool:
        if speaker_id is not None and not self._get_speaker(speaker_id):
            raise ValueError("Speaker does not exist")
        before = self.project.model_dump()
        candidate = self.project.model_copy(deep=True)
        targets = [event for event in candidate.events if event.id in set(event_ids)]
        if not targets or len(targets) != len(set(event_ids)):
            raise ValueError("Select existing events")
        for event in targets:
            event.speaker_id = speaker_id
            event.speaker_reviewed = reviewed
            event.manual_override = True
        self.project = candidate
        self._record_action("update_project", "project", before, candidate.model_dump())
        self._save()
        return True

    def structure_events(self, event_ids: list[str], operation: str, at: float = 0) -> bool:
        from engine.editor.structure import edit_structure
        before = self.project.model_dump()
        candidate = Project.model_validate(edit_structure(before, event_ids, operation, at))
        for event in candidate.events:
            self._validate_event_timing(event)
        self.project = candidate
        self._record_action("update_project", "project", before, candidate.model_dump())
        self._save()
        return True

    def batch_events(self, event_ids: list[str], operation: str, delta: float = 0, ripple: bool = False) -> bool:
        from engine.editor.batch import edit_batch
        before = self.project.model_dump()
        candidate = Project.model_validate(edit_batch(before, event_ids, operation, delta, ripple))
        for event in candidate.events:
            self._validate_event_timing(event)
        self.project = candidate
        self._record_action("update_project", "project", before, candidate.model_dump())
        self._save()
        return True

    def remove_event(self, event_id: str) -> bool:
        """Remove a caption event."""
        event = self._get_event(event_id)
        if event is None:
            return False
        before = event.model_dump()
        self.project.events = [e for e in self.project.events if e.id != event_id]
        self._record_action("remove_event", event_id, before, {})
        self._save()
        return True

    # ─── Word Operations ─────────────────────────────────────

    @staticmethod
    def _validate_event_timing(event: CaptionEvent) -> None:
        import math

        if not all(math.isfinite(v) for v in (event.start, event.end)) or event.start < 0 or event.end <= event.start:
            raise ValueError("Event end must be after its start, with finite non-negative times")
        for word in event.words:
            if word.character_colors is not None:
                import re
                if any(c is not None and not re.fullmatch(r"#[0-9a-fA-F]{6}", c) for c in word.character_colors):
                    raise ValueError("Character colors must be six-digit hex values or null")
            if not all(math.isfinite(v) for v in (word.start, word.end)) or not (event.start <= word.start < word.end <= event.end + 1e-6):
                raise ValueError("Words must have positive duration inside the event")
            if (not math.isfinite(word.size_pct) or word.size_pct <= 0
                    or not 100 <= word.weight <= 1000 or not 25 <= word.width <= 200
                    or not math.isfinite(word.opacity) or not 0 <= word.opacity <= 1
                    or (word.pitch_hz is not None and (not math.isfinite(word.pitch_hz) or word.pitch_hz < 0))):
                raise ValueError("Word size, weight, width, opacity or pitch is invalid")
            if word.syllables:
                for syllable in word.syllables:
                    if (not isinstance(syllable, dict) or not isinstance(syllable.get("text"), str)
                            or not all(isinstance(syllable.get(k), (float, int)) and math.isfinite(syllable[k]) for k in ("start", "end"))
                            or syllable["start"] < word.start - 1e-6
                            or syllable["end"] > word.end + 1e-6
                            or syllable["end"] <= syllable["start"]):
                        raise ValueError("Syllables need text and finite ordered times inside their word")
                    pitch = syllable.get("pitch_hz")
                    if pitch is not None and (not isinstance(pitch, (int, float)) or not math.isfinite(pitch) or pitch < 0):
                        raise ValueError("Syllable pitch must be a non-negative finite number")
            if word.letter_pitches and any(p is not None and (not math.isfinite(p) or p < 0) for p in word.letter_pitches):
                raise ValueError("Letter pitches must be non-negative finite values or null")

    def add_word(self, event_id: str, text: str, start: float, end: float) -> bool:
        """Add a word, preserving a complete undo snapshot."""
        event = self._get_event(event_id)
        if event is None:
            return False
        words = [w.model_dump() for w in event.words]
        words.append(Word(text=text, start=start, end=end).model_dump())
        return self.update_event(event_id, words=words, text=" ".join(w["text"] for w in words))

    def update_word(self, event_id: str, word_index: int, **kwargs: Any) -> bool:
        """Update a word and keep event text in sync, in one undo step."""
        event = self._get_event(event_id)
        if event is None or not 0 <= word_index < len(event.words):
            return False
        words = [w.model_dump() for w in event.words]
        old_word = copy.deepcopy(words[word_index])
        if "text" in kwargs and kwargs["text"] != old_word["text"] and "character_colors" not in kwargs:
            words[word_index]["character_colors"] = None
        words[word_index].update({k: v for k, v in kwargs.items() if k in Word.model_fields})
        if ("start" in kwargs or "end" in kwargs) and "syllables" not in kwargs and old_word.get("syllables"):
            current = words[word_index]
            def retime(t):
                return current["start"] + (t - old_word["start"]) * (current["end"] - current["start"]) / max(.001, old_word["end"] - old_word["start"])
            current["syllables"] = [{**sy, "start": retime(sy["start"]), "end": retime(sy["end"])} for sy in old_word["syllables"]]
        text = event.text
        if "text" in kwargs:
            cursor = 0
            positions = []
            for word in event.words:
                start = event.text.find(word.text, cursor)
                if start < 0:
                    break
                positions.append(start)
                cursor = start + len(word.text)
            if len(positions) == len(event.words):
                start = positions[word_index]
                text = event.text[:start] + kwargs["text"] + event.text[start + len(old_word["text"]):]
            else:
                text = " ".join(w["text"] for w in words)
        return self.update_event(event_id, words=words, text=text)

    def remove_word(self, event_id: str, word_index: int) -> bool:
        """Remove exactly one word, with repeat-word-safe undo/redo."""
        event = self._get_event(event_id)
        if event is None or not 0 <= word_index < len(event.words):
            return False
        words = [w.model_dump() for i, w in enumerate(event.words) if i != word_index]
        return self.update_event(event_id, words=words, text=" ".join(w["text"] for w in words))

    # ─── Syllable Operations ─────────────────────────────────

    def add_syllable(
        self,
        event_id: str,
        word_index: int,
        text: str,
        start: float,
        end: float,
    ) -> bool:
        """Add a syllable to a word."""
        event = self._get_event(event_id)
        if event is None or not 0 <= word_index < len(event.words):
            return False
        syllables = copy.deepcopy(event.words[word_index].syllables or [])
        syllables.append({"text": text, "start": start, "end": end})
        return self.update_word(event_id, word_index, syllables=syllables)

    def update_syllable(
        self, event_id: str, word_index: int, syllable_index: int, **kwargs: Any,
    ) -> bool:
        """Update a syllable through the validated, undoable word path."""
        event = self._get_event(event_id)
        if event is None or not 0 <= word_index < len(event.words):
            return False
        syllables = copy.deepcopy(event.words[word_index].syllables or [])
        if not 0 <= syllable_index < len(syllables):
            return False
        syllables[syllable_index].update({k: v for k, v in kwargs.items() if k in {"text", "start", "end", "pitch_hz"}})
        return self.update_word(event_id, word_index, syllables=syllables)

    # ─── Timing Editor ───────────────────────────────────────

    def adjust_event_timing(
        self,
        event_id: str,
        start_delta: float,
        end_delta: float,
    ) -> bool:
        """Adjust event timing by deltas in seconds."""
        event = self._get_event(event_id)
        if event is None:
            return False
        start = max(0.0, event.start + start_delta)
        end = max(start + 0.001, event.end + end_delta)
        return self.update_event(event_id, start=start, end=end)

    def adjust_word_timing(
        self,
        event_id: str,
        word_index: int,
        start_delta: float,
        end_delta: float,
    ) -> bool:
        """Adjust word timing by deltas in seconds."""
        event = self._get_event(event_id)
        if event is None or word_index >= len(event.words):
            return False
        word = event.words[word_index]
        start = max(event.start, word.start + start_delta)
        end = min(event.end, max(start + 0.001, word.end + end_delta))
        return self.update_word(event_id, word_index, start=start, end=end)

    # ─── Typography Inspector ────────────────────────────────

    def set_typography(self, event_id: str, **kwargs: Any) -> bool:
        """Set typography properties on an event's style.

        Args:
            event_id: Target event ID.
            size_pct: Font size (% of screen height).
            weight: Font weight (100-900).
            width: Font width (50-150).
            italic: Italic flag.
            size_mode: 'auto' or 'manual'.
            weight_mode: 'auto' or 'manual'.
            width_mode: 'auto' or 'manual'.
        """
        event = self._get_event(event_id)
        if event is None:
            return False
        return self._set_style(event, "set_typography", kwargs, {
            "size_pct", "weight", "width", "italic", "read_ahead_opacity", "minimum_pct", "maximum_pct",
            "escalation_rate", "escalation_max", "escalation_gate", "size_mode", "weight_mode", "width_mode",
        })

    def set_style(self, event_id: str, **kwargs: Any) -> bool:
        """Apply a complete or partial style atomically in one undo step."""
        event = self._get_event(event_id)
        if event is None:
            return False
        return self._set_style(event, "set_style", kwargs, set(Style.model_fields))

    def _set_style(self, event: CaptionEvent, action: str, updates: dict, allowed: set) -> bool:
        import math

        before = event.style.model_dump()
        data = {**before, **{k: v for k, v in updates.items() if k in allowed}}
        candidate = Style.model_validate(data)
        for key in ("read_ahead_opacity", "box_opacity"):
            if not 0 <= getattr(candidate, key) <= 1:
                raise ValueError(f"{key} must be between 0 and 1")
        for key in ("size_pct", "minimum_pct", "maximum_pct", "weight", "width", "pop_scale", "box_padding", "escalation_rate", "escalation_max", "escalation_gate"):
            value = getattr(candidate, key)
            if not math.isfinite(value) or value < 0:
                raise ValueError(f"{key} must be finite and non-negative")
        if candidate.minimum_pct > candidate.maximum_pct:
            raise ValueError("Minimum size cannot exceed maximum size")
        if candidate.size_pct <= 0 or not 100 <= candidate.weight <= 1000 or not 25 <= candidate.width <= 200:
            raise ValueError("Size, weight or width is outside the supported range")
        for key in ("size_mode", "weight_mode", "width_mode"):
            if getattr(candidate, key) not in {"auto", "manual"}:
                raise ValueError(f"{key} must be auto or manual")
        event.style = candidate
        self._record_action(action, event.id, before, candidate.model_dump())
        self._save()
        return True

    # ─── Animation Inspector ─────────────────────────────────

    def set_animation(self, event_id: str, **kwargs: Any) -> bool:
        """Set animation properties on an event's style.

        Args:
            event_id: Target event ID.
            pop_scale: Onset rise multiplier (default 1.25 = 25% elevation).
            pop_duration: Pop animation duration in seconds.
            pop_easing: Easing curve ('smooth', 'ease_in', 'ease_out').
            syllable_mode: Enable syllable-level animation.
            color_transition_point: When color shifts (0-1).
            color_transition_duration: Duration of color transition.
        """
        event = self._get_event(event_id)
        if event is None:
            return False
        return self._set_style(event, "set_animation", kwargs, {
            "pop_scale", "pop_duration", "pop_easing", "syllable_mode", "color_transition_point", "color_transition_duration",
        })

    # ─── Box / Work-Area Inspector ───────────────────────────

    def set_box_properties(self, event_id: str, **kwargs: Any) -> bool:
        """Set caption box properties on an event's style.

        Args:
            event_id: Target event ID.
            box_opacity: Caption box opacity (0-1).
            box_padding: Box padding in pixels.
            breakout_permission: Allow text to break outside box.
        """
        event = self._get_event(event_id)
        if event is None:
            return False
        return self._set_style(event, "set_box_properties", kwargs, {
            "box_opacity", "box_padding", "breakout_permission",
        })

    # ─── Speaker Editor ──────────────────────────────────────

    def set_speaker_color(self, speaker_id: str, color: str) -> bool:
        """Set a speaker's color."""
        return self.update_speaker(speaker_id, color=color)

    def set_speaker_category(
        self, speaker_id: str, category: SpeakerCategory
    ) -> bool:
        """Change a speaker's category."""
        return self.update_speaker(speaker_id, category=category)

    def set_speaker_off_camera(self, speaker_id: str, off_camera: bool) -> bool:
        """Toggle off-camera status."""
        return self.update_speaker(speaker_id, off_camera=off_camera)

    # ─── Palette Assignment ──────────────────────────────────

    def assign_palette_color(
        self, speaker_id: str, color: str
    ) -> bool:
        """Assign a specific palette color to a speaker."""
        return self.update_speaker(speaker_id, color=color)

    # ─── Scene Overrides ─────────────────────────────────────

    def set_scene_override(
        self, scene_id: str, overrides: dict[str, Any]
    ) -> None:
        """Set overrides for a scene.

        Args:
            scene_id: Scene identifier.
            overrides: Dict of property → value overrides.
        """
        if not self.project.scenes:
            self.project.scenes = []
        scene_found = False
        for scene in self.project.scenes:
            if scene.get("id") == scene_id:
                scene["overrides"] = overrides
                scene_found = True
                break
        if not scene_found:
            self.project.scenes.append(
                {"id": scene_id, "overrides": overrides}
            )
        self._save()

    # ─── Multi-Select ────────────────────────────────────────

    def select(self, item_id: str) -> None:
        """Add an item to the selection."""
        if item_id not in self._selected:
            self._selected.append(item_id)

    def deselect(self, item_id: str) -> None:
        """Remove an item from the selection."""
        self._selected = [s for s in self._selected if s != item_id]

    def select_all(self) -> None:
        """Select all events."""
        self._selected = [e.id for e in self.project.events]

    def clear_selection(self) -> None:
        """Clear the selection."""
        self._selected = []

    def apply_to_selection(self, **kwargs: Any) -> int:
        """Apply property changes to all selected items."""
        count = 0
        for item_id in self._selected:
            if self.update_event(item_id, **kwargs):
                count += 1
        if count > 0:
            self._save()
        return count

    # ─── Copy / Paste Style ──────────────────────────────────

    def copy_style(self, source_event_id: str) -> Optional[dict]:
        """Copy the style from an event."""
        event = self._get_event(source_event_id)
        if event is None:
            return None
        return event.style.model_dump()

    def paste_style(
        self, source_event_id: str, target_event_id: str
    ) -> bool:
        """Paste style from one event to another."""
        source = self._get_event(source_event_id)
        target = self._get_event(target_event_id)
        if source is None or target is None:
            return False
        return self.set_style(target_event_id, **source.style.model_dump())

    # ─── Build from Transcript ───────────────────────────────

    def build_from_transcript(
        self,
        transcript: list[dict],
        video_width: int = 1920,
        video_height: int = 1080,
        fps: float = 23.976,
        speakers: Optional[list[dict]] = None,
    ) -> Project:
        """Build a complete CI project from a transcript.

        Args:
            transcript: List of caption entries, each a dict with at least
                'text', 'start', 'end'. M6 ASR entries may also carry:
                    - 'words': precise word timing [{'text', 'start', 'end',
                      'confidence', 'source_model', ...}] — used verbatim
                      instead of evenly spreading word timings.
                    - 'confidence', 'source_model', 'source_timestamp':
                      event-level AI provenance (spec §2.2).
                    - 'speaker_id', 'off_camera', 'manual_override':
                      attribution and review flags.
            video_width: Video width in pixels.
            video_height: Video height in pixels.
            fps: Video frame rate.
            speakers: Optional list of speaker dicts. A 'name' is required;
                an explicit 'id' is honored so events can reference
                pipeline speaker ids.

        Returns:
            The built Project.
        """
        logger.info(
            "Building project from transcript with %d entries",
            len(transcript),
        )

        # Set video info
        self.project.video = VideoInfo(
            width=video_width,
            height=video_height,
            fps=fps,
            duration=max((entry["end"] for entry in transcript), default=0.0),
        )

        # Add speakers if provided (M6: honor explicit ids so events can
        # reference pipeline speaker ids)
        if speakers:
            for spk in speakers:
                spk_kwargs = {
                    k: v
                    for k, v in spk.items()
                    if k
                    in [
                        "name",
                        "category",
                        "color",
                        "role",
                        "off_camera",
                    ]
                }
                if "id" in spk:
                    speaker = Speaker(id=str(spk["id"]), **spk_kwargs)
                    self.project.speakers.append(speaker)
                else:
                    self.add_speaker(**spk_kwargs)

        # Add each transcript entry as an event
        for entry in transcript:
            text = entry.get("text", "")
            start = entry.get("start", 0.0)
            end = entry.get("end", 0.0)

            entry_words = entry.get("words")
            if entry_words:
                # M6: precise word timing from ASR + alignment — use verbatim
                words = []
                for w in entry_words:
                    if not isinstance(w, dict) or not w.get("text"):
                        continue
                    word = {k: v for k, v in w.items() if k in _WORD_FIELDS}
                    word.setdefault("start", start)
                    word.setdefault("end", end)
                    words.append(word)
                    end = max(end, float(word["end"]))
            else:
                words_text = text.split()
                word_count = len(words_text)
                word_duration = (end - start) / max(word_count, 1)

                words = []
                word_start = start
                for w in words_text:
                    word_end = word_start + word_duration
                    words.append(
                        {"text": w, "start": word_start, "end": word_end}
                    )
                    word_start = word_end

            event = self.add_event(
                text=text,
                start=start,
                end=end,
                speaker_id=entry.get("speaker_id"),
                event_type=entry.get("type", "dialogue"),
                words=words if words else None,
            )
            # M6 provenance metadata (spec §2.2)
            for key in (
                "confidence",
                "source_model",
                "source_timestamp",
                "manual_override", "notes",
                "off_camera", "speaker_review_required", "speaker_review_reasons", "speaker_coverage", "speaker_reviewed",
            ):
                if key in entry:
                    setattr(event, key, entry[key])

        self._save()
        logger.info(
            "Project built: %d events, %d speakers",
            len(self.project.events),
            len(self.project.speakers),
        )
        return self.project

    # ─── Internal Helpers ────────────────────────────────────

    def _get_speaker(self, speaker_id: str) -> Optional[Speaker]:
        for speaker in self.project.speakers:
            if speaker.id == speaker_id:
                return speaker
        return None

    def _get_event(self, event_id: str) -> Optional[CaptionEvent]:
        for event in self.project.events:
            if event.id == event_id:
                return event
        return None

    def _record_action(
        self,
        action_type: str,
        target_id: str,
        before: dict,
        after: dict,
    ) -> None:
        """Record an action for undo/redo."""
        action = EditAction(action_type, target_id, before, after)
        self._undo_stack.append(action)
        self._redo_stack.clear()  # Clear redo on new action

    def _save(self) -> None:
        """Mark project as modified."""
        self.project.modified_at = self._now_iso()

    @staticmethod
    def _now_iso() -> str:
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).isoformat()

    @property
    def selected(self) -> list[str]:
        """Return current selection IDs."""
        return list(self._selected)
