"""Schema definitions for Caption With Intention canonical project model."""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class SpeakerCategory(str, Enum):
    main = "main"
    supporting = "supporting"
    minor = "minor"


class EventType(str, Enum):
    dialogue = "dialogue"
    sound_effect = "sound_effect"
    music = "music"
    speaker_overlap = "speaker_overlap"
    custom = "custom"


class ReviewState(str, Enum):
    pending = "pending"
    accepted = "accepted"
    rejected = "rejected"
    corrected = "corrected"


class Word(BaseModel):
    text: str
    start: float
    end: float
    size_pct: float = 5.0
    weight: int = 400
    width: int = 100
    color: str = "#FFFFFF"
    opacity: float = 1.0
    italic: bool = False
    confidence: Optional[float] = None
    source_model: Optional[str] = None
    source_timestamp: Optional[float] = None
    manual_override: bool = False
    review_state: ReviewState = ReviewState.pending
    syllables: Optional[list[dict]] = None


class Style(BaseModel):
    read_ahead_opacity: float = 0.90
    pop_scale: float = 1.15
    size_mode: str = "auto"
    weight_mode: str = "auto"
    width_mode: str = "auto"
    color_transition_point: Optional[float] = None
    color_transition_duration: Optional[float] = None
    pop_duration: Optional[float] = None
    pop_easing: str = "smooth"
    syllable_mode: bool = False


class CaptionEvent(BaseModel):
    id: str
    type: EventType = EventType.dialogue
    start: float
    end: float
    speaker_id: Optional[str] = None
    off_camera: bool = False
    text: str = ""
    style: Style = Style()
    words: list[Word] = []
    confidence: Optional[float] = None
    source_model: Optional[str] = None
    source_timestamp: Optional[float] = None
    manual_override: bool = False
    review_state: ReviewState = ReviewState.pending
    exception_profile: Optional[str] = None
    notes: str = ""


class Speaker(BaseModel):
    id: str
    name: str = "Unknown"
    category: SpeakerCategory = SpeakerCategory.main
    role: Optional[str] = None
    color: str = "#E5E517"
    confidence: Optional[float] = None
    source_model: Optional[str] = None
    source_timestamp: Optional[float] = None
    manual_override: bool = False
    review_state: ReviewState = ReviewState.pending
    off_camera: bool = False
    active_speaker: bool = False
    notes: str = ""


class VideoInfo(BaseModel):
    width: int = 1920
    height: int = 1080
    fps: float = 23.976
    duration: float = 0.0
    pixel_aspect_ratio: Optional[tuple[float, float]] = None
    codec: Optional[str] = None
    audio_codec: Optional[str] = None
    audio_sample_rate: Optional[int] = None
    audio_channels: Optional[int] = None
    language: Optional[str] = None
    source_hash: Optional[str] = None


class Project(BaseModel):
    schema_version: str = "ci-project-1"
    design_system: str = "caption-with-intention-v1.0"
    project_name: str = "Untitled"
    video: VideoInfo = VideoInfo()
    speakers: list[Speaker] = []
    events: list[CaptionEvent] = []
    scenes: list[dict] = []
    created_at: Optional[str] = None
    modified_at: Optional[str] = None
    profile_version: str = "v1.0"
    notes: str = ""
