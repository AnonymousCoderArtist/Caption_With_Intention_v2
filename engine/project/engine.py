"""Project engine — create, open, save projects."""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from pydantic import ValidationError

from schemas.project import Project
from engine.logging.logger import setup_logging
from engine.errors.errors import ProjectCorruptionError, CWIError

logger = setup_logging()


class ProjectEngine:
    """Handles project creation, loading, and saving."""

    def __init__(self, project_path: Optional[str | Path] = None):
        self.project_path = Path(project_path) if project_path else None
        self.project: Optional[Project] = None
        self._lock_file: Optional[Path] = None

    def create(
        self,
        project_name: str,
        video_path: Optional[str | Path] = None,
        project_dir: Optional[str | Path] = None,
    ) -> Project:
        """Create a new project.

        Args:
            project_name: Name for the project.
            video_path: Path to source video (stored as reference, not copied).
            project_dir: Directory for project files. Auto-generated if not given.

        Returns:
            The newly created Project object.
        """
        logger.info("Creating project: %s", project_name, extra={"stage": "project_create"})

        if project_dir is None:
            project_dir = Path.cwd() / project_name.replace(" ", "_")
        project_dir = Path(project_dir)
        project_dir.mkdir(parents=True, exist_ok=True)

        now = datetime.now(timezone.utc).isoformat()

        project = Project(
            project_name=project_name,
            created_at=now,
            modified_at=now,
        )

        if video_path is not None:
            video_path = Path(video_path)
            if not video_path.exists():
                raise FileNotFoundError(f"Video file not found: {video_path}")
            project.video.duration = 0.0  # Will be populated by media ingest
            logger.info(
                "Source video path stored: %s (not copied into memory)",
                video_path,
                extra={"stage": "project_create"},
            )

        self.project = project
        self.project_path = project_dir / f"{project_name.replace(' ', '_')}.ci"
        self.save()

        logger.info("Project created at: %s", self.project_path, extra={"stage": "project_create"})
        return project

    def open(self, project_path: str | Path) -> Project:
        """Open an existing project.

        Args:
            project_path: Path to the .ci project file.

        Returns:
            The loaded Project object.

        Raises:
            ProjectCorruptionError: If the project file is invalid or corrupt.
            FileNotFoundError: If the project file doesn't exist.
        """
        project_path = Path(project_path)
        logger.info("Opening project: %s", project_path, extra={"stage": "project_open"})

        if not project_path.exists():
            raise FileNotFoundError(f"Project file not found: {project_path}")

        try:
            with open(project_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Validate schema version
            schema_version = data.get("schema_version")
            if schema_version != "ci-project-1":
                raise ProjectCorruptionError(
                    f"Unsupported schema version: {schema_version}",
                    details={"found": schema_version, "expected": "ci-project-1"},
                )

            self.project = Project.model_validate(data)
            self.project_path = project_path

            logger.info(
                "Project loaded: %s (%d events, %d speakers)",
                project_path,
                len(self.project.events),
                len(self.project.speakers),
                extra={"stage": "project_open"},
            )
            return self.project

        except json.JSONDecodeError as e:
            raise ProjectCorruptionError(
                f"Corrupt project file: {e}",
                details={"path": str(project_path)},
            )
        except ValidationError as e:
            raise ProjectCorruptionError(
                f"Project validation failed: {e}",
                details={"path": str(project_path)},
            )

    def save(self) -> None:
        """Save the current project to disk.

        Raises:
            RuntimeError: If no project is loaded.
        """
        if self.project is None:
            raise RuntimeError("No project loaded to save")

        if self.project_path is None:
            raise RuntimeError("No project path set")

        self.project.modified_at = datetime.now(timezone.utc).isoformat()

        data = self.project.model_dump()
        project_dir = self.project_path.parent
        project_dir.mkdir(parents=True, exist_ok=True)

        with open(self.project_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)

        logger.info(
            "Project saved: %s", self.project_path, extra={"stage": "project_save"}
        )

    def add_speaker(self, speaker) -> None:
        """Add a speaker to the project."""
        if self.project is None:
            raise RuntimeError("No project loaded")
        self.project.speakers.append(speaker)
        self.save()

    def add_event(self, event) -> None:
        """Add a caption event to the project."""
        if self.project is None:
            raise RuntimeError("No project loaded")
        self.project.events.append(event)
        self.save()

    @property
    def is_loaded(self) -> bool:
        return self.project is not None
