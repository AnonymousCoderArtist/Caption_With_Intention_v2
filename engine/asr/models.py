"""ASR data models — transcription results, words, segments."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass(slots=True)
class Word:
    """A single word with timing and speaker attribution."""

    text: str
    start: float
    end: float
    confidence: float = 0.0
    speaker_id: Optional[str] = None

    @property
    def duration(self) -> float:
        return self.end - self.start

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "start": self.start,
            "end": self.end,
            "duration": self.duration,
            "confidence": self.confidence,
            "speaker_id": self.speaker_id,
        }


@dataclass(slots=True)
class Segment:
    """A contiguous transcription segment (sentence or utterance)."""

    text: str
    start: float
    end: float
    confidence: float = 0.0
    words: list[Word] = field(default_factory=list)
    speaker_id: Optional[str] = None

    @property
    def duration(self) -> float:
        return self.end - self.start

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "start": self.start,
            "end": self.end,
            "duration": self.duration,
            "confidence": self.confidence,
            "speaker_id": self.speaker_id,
            "words": [w.to_dict() for w in self.words],
        }


@dataclass(slots=True)
class TranscriptionResult:
    """Full transcription output from a Transcriber run."""

    text: str  # Plain text concatenation of all segments
    segments: list[Segment] = field(default_factory=list)
    words: list[Word] = field(default_factory=list)
    language: str = "en"
    model: str = ""
    source_path: str = ""
    duration: float = 0.0

    @property
    def word_count(self) -> int:
        return len(self.words)

    @property
    def segment_count(self) -> int:
        return len(self.segments)

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "language": self.language,
            "model": self.model,
            "source_path": self.source_path,
            "duration": self.duration,
            "word_count": self.word_count,
            "segment_count": self.segment_count,
            "segments": [s.to_dict() for s in self.segments],
            "words": [w.to_dict() for w in self.words],
        }
