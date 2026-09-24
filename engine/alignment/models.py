"""Alignment data models — word boundaries, phoneme alignments."""

from __future__ import annotations

from dataclasses import dataclass, field

from engine.asr.models import Word


@dataclass(slots=True)
class AlignedWord(Word):
    """A word with refined, precise timing from forced alignment."""

    phonemes: list[str] = field(default_factory=list)
    alignment_confidence: float = 0.0
    boundary_type: str = "speech"  # speech, silence, overlap, filler

    def to_dict(self) -> dict:
        d = {
            "text": self.text,
            "start": self.start,
            "end": self.end,
            "duration": self.duration,
            "confidence": self.confidence,
            "speaker_id": self.speaker_id,
            "phonemes": self.phonemes,
            "alignment_confidence": self.alignment_confidence,
            "boundary_type": self.boundary_type,
        }
        return d


@dataclass(slots=True)
class AlignmentResult:
    """Full alignment output."""

    words: list[AlignedWord] = field(default_factory=list)
    total_duration: float = 0.0
    method: str = "vad_refinement"  # "forced" (wav2vec2) or "vad_refinement"
    audio_path: str = ""
    confidence_mean: float = 0.0
    confidence_min: float = 0.0
    confidence_max: float = 0.0
    boundary_counts: dict[str, int] = field(default_factory=dict)

    @property
    def word_count(self) -> int:
        return len(self.words)

    def to_dict(self) -> dict:
        return {
            "method": self.method,
            "audio_path": self.audio_path,
            "word_count": self.word_count,
            "total_duration": self.total_duration,
            "confidence_mean": self.confidence_mean,
            "confidence_min": self.confidence_min,
            "confidence_max": self.confidence_max,
            "boundary_counts": self.boundary_counts,
            "words": [w.to_dict() for w in self.words],
        }
