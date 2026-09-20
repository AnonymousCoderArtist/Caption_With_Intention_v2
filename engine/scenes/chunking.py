"""Adaptive chunking for video analysis pipelines.

Chunks divide a video into manageable segments for processing.
Each chunk has a defined time range and overlap with neighbors.

Design principles:
- Never load entire video into RAM
- Process in 5-10 minute chunks (adjustable)
- Maintain 1-2 second overlap across chunks
- Write results to disk immediately after each chunk
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field, model_validator

logger = logging.getLogger("caption_with_intention")


DEFAULT_CHUNK_DURATION = 600  # 10 minutes in seconds
DEFAULT_OVERLAP_DURATION = 2.0  # 2 seconds overlap
MIN_CHUNK_DURATION = 30  # 30 seconds minimum
MAX_CHUNK_DURATION = 600  # 10 minutes maximum


class Chunk(BaseModel):
    """A time-bounded segment of a video."""

    index: int
    start: float
    end: float
    overlap_start: float = 0.0  # Where overlap begins (for processing)
    overlap_end: float = 0.0    # Where overlap ends
    notes: str = ""

    model_config = {"populate_by_name": True}

    @property
    def duration(self) -> float:
        return self.end - self.start

    @property
    def overlap_duration(self) -> float:
        return self.overlap_end - self.overlap_start

    @model_validator(mode="after")
    def validate_duration(self) -> "Chunk":
        if self.duration <= 0:
            raise ValueError(
                f"Chunk {self.index} has non-positive duration: "
                f"{self.duration:.3f}s"
            )
        return self

    def to_dict(self) -> dict:
        return self.model_dump()


class ChunkConfig(BaseModel):
    """Configuration for chunk generation."""

    chunk_duration: float = DEFAULT_CHUNK_DURATION
    overlap_duration: float = DEFAULT_OVERLAP_DURATION
    min_chunk_duration: float = MIN_CHUNK_DURATION
    max_chunk_duration: float = MAX_CHUNK_DURATION

    @model_validator(mode="after")
    def validate_durations(self) -> "ChunkConfig":
        if self.chunk_duration < self.min_chunk_duration:
            raise ValueError(
                f"Chunk duration {self.chunk_duration}s is below "
                f"minimum {self.min_chunk_duration}s"
            )
        if self.chunk_duration > self.max_chunk_duration:
            raise ValueError(
                f"Chunk duration {self.chunk_duration}s exceeds "
                f"maximum {self.max_chunk_duration}s"
            )
        if self.overlap_duration >= self.chunk_duration / 2:
            raise ValueError(
                f"Overlap duration {self.overlap_duration}s is too large "
                f"relative to chunk duration {self.chunk_duration}s"
            )
        return self

    def validate(self, total_duration: float) -> None:
        """Validate config against video duration."""
        if self.chunk_duration > total_duration:
            return  # Single chunk covers entire video
        if self.chunk_duration < self.min_chunk_duration:
            raise ValueError(
                f"Chunk duration {self.chunk_duration}s is below "
                f"minimum {self.min_chunk_duration}s"
            )
        if self.chunk_duration > self.max_chunk_duration:
            raise ValueError(
                f"Chunk duration {self.chunk_duration}s exceeds "
                f"maximum {self.max_chunk_duration}s"
            )
        if self.overlap_duration >= self.chunk_duration / 2:
            raise ValueError(
                f"Overlap duration {self.overlap_duration}s is too large "
                f"relative to chunk duration {self.chunk_duration}s"
            )


def generate_chunks(
    total_duration: float,
    config: Optional[ChunkConfig] = None,
) -> list[Chunk]:
    """Generate chunks for a video of given duration.

    Args:
        total_duration: Total video duration in seconds.
        config: Chunk configuration. Uses defaults if None.

    Returns:
        List of Chunk objects covering the entire video.
    """
    if config is None:
        config = ChunkConfig()

    config.validate(total_duration)

    chunks: list[Chunk] = []

    # If video is shorter than chunk duration, single chunk
    if total_duration <= config.chunk_duration:
        chunks.append(
            Chunk(
                index=0,
                start=0.0,
                end=total_duration,
                overlap_start=0.0,
                overlap_end=0.0,
            )
        )
        logger.info(
            "Generated 1 chunk for %.1fs (single chunk)", total_duration,
            extra={"stage": "chunking"},
        )
        return chunks

    chunk_duration = config.chunk_duration
    overlap = config.overlap_duration
    effective_chunk = chunk_duration - overlap  # Non-overlapping portion

    index = 0
    current_start = 0.0

    while current_start < total_duration:
        current_end = min(current_start + chunk_duration, total_duration)
        overlap_start = max(0.0, current_start)
        overlap_end = min(current_start + overlap, total_duration)

        # For the last chunk, overlap_end should be at start of previous chunk's overlap
        chunk = Chunk(
            index=index,
            start=current_start,
            end=current_end,
            overlap_start=overlap_start,
            overlap_end=overlap_end,
        )
        chunks.append(chunk)
        logger.debug(
            "Chunk %d: %.3fs - %.3fs (overlap: %.3fs - %.3fs)",
            index,
            current_start,
            current_end,
            overlap_start,
            overlap_end,
            extra={"stage": "chunking"},
        )

        index += 1
        current_start += effective_chunk

        # Safety: avoid infinite loop
        if current_start >= total_duration - 0.001:
            break

    logger.info(
        "Generated %d chunks for %.1fs video",
        len(chunks),
        total_duration,
        extra={"stage": "chunking"},
    )

    return chunks


def get_chunk_overlap_regions(
    chunks: list[Chunk],
) -> list[tuple[float, float, int, int]]:
    """Get overlap regions between adjacent chunks.

    Returns:
        List of (overlap_start, overlap_end, left_chunk_idx, right_chunk_idx)
        tuples.
    """
    overlaps: list[tuple[float, float, int, int]] = []
    for i in range(len(chunks) - 1):
        left = chunks[i]
        right = chunks[i + 1]
        overlap_start = max(left.overlap_end, right.overlap_start)
        overlap_end = min(left.end, right.start)
        if overlap_start < overlap_end:
            overlaps.append(
                (overlap_start, overlap_end, i, i + 1)
            )
    return overlaps


def split_chunks_for_resume(
    chunks: list[Chunk],
    completed_indices: set[int],
) -> list[Chunk]:
    """Return only the chunks that haven't been processed yet.

    Args:
        chunks: All chunks.
        completed_indices: Set of chunk indices already completed.

    Returns:
        List of pending chunks.
    """
    return [
        chunk for chunk in chunks if chunk.index not in completed_indices
    ]
