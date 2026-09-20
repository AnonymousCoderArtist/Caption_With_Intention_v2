"""Speaker diarization data models."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class SpeakerSegment:
    """A contiguous speech segment attributed to a speaker."""

    speaker_id: str
    start: float
    end: float
    confidence: float = 0.0
    source: str = ""  # e.g. "whisper", "pyannote", "wav2vec2"

    @property
    def duration(self) -> float:
        return self.end - self.start

    def to_dict(self) -> dict:
        return {
            "speaker_id": self.speaker_id,
            "start": self.start,
            "end": self.end,
            "duration": self.duration,
            "confidence": self.confidence,
            "source": self.source,
        }


@dataclass(slots=True)
class SpeakerLabel:
    """A named speaker with metadata."""

    id: str
    name: str = "Unknown"
    category: str = "main"  # main, supporting, minor
    color: str = "#E5E517"
    confidence: float = 0.0
    off_camera: bool = False
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "color": self.color,
            "confidence": self.confidence,
            "off_camera": self.off_camera,
            "tags": self.tags,
        }
