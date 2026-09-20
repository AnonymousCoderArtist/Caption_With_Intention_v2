"""Scene data model and types for scene/chunk engine."""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class SceneType(str, Enum):
    dialogue = "dialogue"
    action = "action"
    montage = "montage"
    title_card = "title_card"
    transition = "transition"
    unknown = "unknown"


class Shot(BaseModel):
    """A single continuous shot within a scene."""

    id: str
    start: float
    end: float
    shot_type: Optional[str] = None  # e.g., "closeup", "wide", "medium"
    is_reaction_shot: bool = False
    notes: str = ""


class Scene(BaseModel):
    """A scene: a continuous segment of the video with consistent attributes."""

    id: str
    start: float
    end: float
    scene_type: SceneType = SceneType.unknown
    shots: list[Shot] = []
    dominant_speaker: Optional[str] = None
    is_off_camera: bool = False
    notes: str = ""
    override: dict = {}  # Editor overrides for this scene

    @property
    def duration(self) -> float:
        return self.end - self.start


class SceneList(BaseModel):
    """Ordered list of scenes for a project."""

    scenes: list[Scene] = []
    total_duration: float = 0.0

    def add_scene(self, scene: Scene) -> None:
        self.scenes.append(scene)
        self._recompute_duration()

    def get_scene_at_time(self, time_sec: float) -> Optional[Scene]:
        """Return the scene that contains the given timestamp."""
        for scene in self.scenes:
            if scene.start <= time_sec < scene.end:
                return scene
        return None

    def _recompute_duration(self) -> None:
        if self.scenes:
            self.total_duration = self.scenes[-1].end

    def to_dict(self) -> dict:
        return self.model_dump()
