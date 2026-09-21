"""Persistent checkpoint system for scene/chunk pipeline.

Every stage writes checkpoint files after completion.
If the pipeline stops midway, reopening resumes from
the last completed checkpoint.

Design:
- Each chunk has its own checkpoint file
- A master checkpoint tracks overall progress
- Checkpoints are JSON for human readability
- Idempotent: re-running a checkpoint overwrites safely
"""

from __future__ import annotations

import dataclasses
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger("caption_with_intention")


@dataclass(slots=True)
class StageCheckpoint:
    """Checkpoint for a single pipeline stage within a chunk."""

    stage_name: str
    chunk_index: int
    status: str  # "pending", "completed", "failed", "skipped"
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error: Optional[str] = None
    output_path: Optional[str] = None
    metadata: dict = field(default_factory=dict)


@dataclass(slots=True)
class ChunkCheckpoint:
    """Checkpoint for a single chunk containing all stage results."""

    chunk_index: int
    start: float = 0.0
    end: float = 0.0
    status: str = "pending"  # "pending", "completed", "failed", "partial"
    created_at: Optional[str] = None
    completed_at: Optional[str] = None
    stages: list[StageCheckpoint] = field(default_factory=list)
    output_files: dict = field(default_factory=dict)  # stage_name -> path
    notes: str = ""

    def to_dict(self) -> dict:
        return self.model_dump() if hasattr(self, "model_dump") else {
            "chunk_index": self.chunk_index,
            "start": self.start,
            "end": self.end,
            "status": self.status,
            "stages": [s.__dict__ if hasattr(s, "__dict__") else dataclasses.asdict(s) for s in self.stages],
            "output_files": self.output_files,
        }


@dataclass(slots=True)
class MasterCheckpoint:
    """Master checkpoint for the entire video analysis pipeline."""

    project_path: str = ""
    total_duration: float = 0.0
    total_chunks: int = 0
    completed_chunks: list[int] = field(default_factory=list)
    failed_chunks: list[int] = field(default_factory=list)
    chunks: list[dict] = field(default_factory=list)  # ChunkCheckpoint dicts
    pipeline_stages: list[str] = field(default_factory=list)
    current_stage_index: int = 0
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    notes: str = ""

    @property
    def is_complete(self) -> bool:
        return (
            len(self.completed_chunks) == self.total_chunks
            and self.total_chunks > 0
        )

    @property
    def progress_pct(self) -> float:
        if self.total_chunks == 0:
            return 0.0
        return (len(self.completed_chunks) / self.total_chunks) * 100.0


CHECKPOINT_VERSION = "1"


class CheckpointEngine:
    """Manages persistent checkpoint files for pipeline resume."""

    def __init__(self, checkpoint_dir: str | Path):
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self.master_path = self.checkpoint_dir / "master_checkpoint.json"
        self._master: Optional[MasterCheckpoint] = None

    # ── Master checkpoint ──────────────────────────────────────────

    def create_master(
        self,
        project_path: str,
        total_duration: float,
        pipeline_stages: list[str],
        total_chunks: int = 0,
    ) -> MasterCheckpoint:
        """Create a new master checkpoint for a pipeline run."""
        now = datetime.now(timezone.utc).isoformat()

        self._master = MasterCheckpoint(
            project_path=project_path,
            total_duration=total_duration,
            pipeline_stages=pipeline_stages,
            created_at=now,
            updated_at=now,
            total_chunks=total_chunks,
        )
        self._save_master()
        logger.info(
            "Master checkpoint created: %s", self.master_path,
            extra={"stage": "checkpoint"},
        )
        return self._master

    def load_master(self) -> Optional[MasterCheckpoint]:
        """Load existing master checkpoint, if any."""
        if not self.master_path.exists():
            return None

        try:
            with open(self.master_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            self._master = MasterCheckpoint(
                project_path=data.get("project_path", ""),
                total_duration=data.get("total_duration", 0.0),
                total_chunks=data.get("total_chunks", 0),
                pipeline_stages=data.get("pipeline_stages", []),
                completed_chunks=data.get("completed_chunks", []),
                failed_chunks=data.get("failed_chunks", []),
                chunks=data.get("chunks", []),
                current_stage_index=data.get("current_stage_index", 0),
                created_at=data.get("created_at"),
                updated_at=data.get("updated_at"),
                notes=data.get("notes", ""),
            )
            return self._master

        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(
                "Master checkpoint corrupt: %s", e,
                extra={"stage": "checkpoint"},
            )
            return None

    def update_master(self) -> None:
        """Save current master checkpoint state."""
        if self._master is None:
            raise RuntimeError(
                "No master checkpoint created. Call create_master first."
            )
        self._master.updated_at = datetime.now(timezone.utc).isoformat()
        self._save_master()

    # ── Chunk checkpoint ───────────────────────────────────────────

    def create_chunk_checkpoint(
        self,
        chunk_index: int,
        start: float,
        end: float,
        pipeline_stages: Optional[list[str]] = None,
    ) -> ChunkCheckpoint:
        """Create a new chunk checkpoint for a chunk."""
        now = datetime.now(timezone.utc).isoformat()

        checkpoint = ChunkCheckpoint(
            chunk_index=chunk_index,
            start=start,
            end=end,
            created_at=now,
        )

        if pipeline_stages:
            checkpoint.stages = [
                StageCheckpoint(
                    stage_name=stage,
                    chunk_index=chunk_index,
                    status="pending",
                )
                for stage in pipeline_stages
            ]

        self._save_chunk_checkpoint(checkpoint)
        return checkpoint

    def load_chunk_checkpoint(
        self,
        chunk_index: int,
    ) -> Optional[ChunkCheckpoint]:
        """Load checkpoint for a specific chunk."""
        path = self._chunk_path(chunk_index)
        if not path.exists():
            return None

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            return ChunkCheckpoint(
                chunk_index=data.get("chunk_index", chunk_index),
                start=data.get("start", 0.0),
                end=data.get("end", 0.0),
                status=data.get("status", "pending"),
                created_at=data.get("created_at"),
                completed_at=data.get("completed_at"),
                stages=[
                    StageCheckpoint(
                        stage_name=s.get("stage_name", ""),
                        chunk_index=s.get("chunk_index", chunk_index),
                        status=s.get("status", "pending"),
                        started_at=s.get("started_at"),
                        completed_at=s.get("completed_at"),
                        error=s.get("error"),
                        output_path=s.get("output_path"),
                        metadata=s.get("metadata", {}),
                    )
                    for s in data.get("stages", [])
                ],
                output_files=data.get("output_files", {}),
                notes=data.get("notes", ""),
            )

        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(
                "Chunk checkpoint corrupt for chunk %d: %s",
                chunk_index,
                e,
                extra={"stage": "checkpoint"},
            )
            return None

    def save_chunk_stage(
        self,
        chunk_index: int,
        stage_name: str,
        status: str,
        output_path: Optional[str] = None,
        error: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> None:
        """Update a stage within a chunk checkpoint."""
        checkpoint = self.load_chunk_checkpoint(chunk_index)

        if checkpoint is None:
            raise RuntimeError(
                f"No checkpoint found for chunk {chunk_index}. "
                f"Call create_chunk_checkpoint first."
            )

        # Find or create the stage
        stage = None
        for s in checkpoint.stages:
            if s.stage_name == stage_name:
                stage = s
                break

        if stage is None:
            stage = StageCheckpoint(
                stage_name=stage_name,
                chunk_index=chunk_index,
                status="pending",
            )
            checkpoint.stages.append(stage)

        now = datetime.now(timezone.utc).isoformat()
        stage.status = status
        stage.started_at = stage.started_at or now
        stage.completed_at = now
        stage.error = error
        stage.output_path = output_path
        if metadata is not None:
            stage.metadata = metadata

        # Update chunk status based on stage statuses
        if all(
            s.status == "completed" for s in checkpoint.stages
        ):
            checkpoint.status = "completed"
            checkpoint.completed_at = now
        elif any(
            s.status == "failed" for s in checkpoint.stages
        ):
            checkpoint.status = "partial"

        self._save_chunk_checkpoint(checkpoint)
        logger.info(
            "Saved stage '%s' for chunk %d: %s",
            stage_name,
            chunk_index,
            status,
            extra={"stage": "checkpoint"},
        )

    # ── Resume helpers ─────────────────────────────────────────────

    def get_pending_chunks(
        self, chunks: list[dict]
    ) -> list[dict]:
        """Return chunks that haven't been completed."""
        if self._master is None:
            return chunks
        completed = set(self._master.completed_chunks)
        return [c for c in chunks if c.get("chunk_index", 0) not in completed]

    def get_failed_chunks(self) -> list[int]:
        """Return chunks that failed."""
        if self._master is None:
            return []
        return list(self._master.failed_chunks)

    def mark_chunk_completed(self, chunk_index: int) -> None:
        """Mark a chunk as completed in master checkpoint."""
        if self._master is None:
            return
        if chunk_index not in self._master.completed_chunks:
            self._master.completed_chunks.append(chunk_index)
            if chunk_index in self._master.failed_chunks:
                self._master.failed_chunks.remove(chunk_index)
        self.update_master()

    def mark_chunk_failed(self, chunk_index: int) -> None:
        """Mark a chunk as failed in master checkpoint."""
        if self._master is None:
            return
        if chunk_index not in self._master.failed_chunks:
            self._master.failed_chunks.append(chunk_index)
        self.update_master()

    def set_total_chunks(self, total_chunks: int) -> None:
        """Set total chunk count after chunk generation."""
        if self._master is None:
            return
        self._master.total_chunks = total_chunks
        self.update_master()

    # ── Internal ───────────────────────────────────────────────────

    def _chunk_path(self, chunk_index: int) -> Path:
        return self.checkpoint_dir / f"chunk_{chunk_index:06d}.json"

    def _save_master(self) -> None:
        if self._master is None:
            return
        data = {
            "version": CHECKPOINT_VERSION,
            "project_path": self._master.project_path,
            "total_duration": self._master.total_duration,
            "total_chunks": self._master.total_chunks,
            "pipeline_stages": self._master.pipeline_stages,
            "completed_chunks": self._master.completed_chunks,
            "failed_chunks": self._master.failed_chunks,
            "chunks": self._master.chunks,
            "current_stage_index": self._master.current_stage_index,
            "created_at": self._master.created_at,
            "updated_at": self._master.updated_at,
            "notes": self._master.notes,
        }
        with open(self.master_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)

    def _save_chunk_checkpoint(
        self, checkpoint: ChunkCheckpoint
    ) -> None:
        path = self._chunk_path(checkpoint.chunk_index)
        data = checkpoint.to_dict()
        data["version"] = CHECKPOINT_VERSION
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)
