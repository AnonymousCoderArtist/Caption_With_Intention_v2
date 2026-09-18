"""Project file format specification and utilities.

The .ci project file is a JSON file containing the canonical project model.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from schemas.project import Project


PROJECT_EXTENSION = ".ci"
METADATA_FILE = "project.json"
ANALYSIS_DIR = "analysis"
CAPTIONS_DIR = "captions"
CACHE_DIR = "cache"
RENDERS_DIR = "renders"
EXPORTS_DIR = "exports"
LOGS_DIR = "logs"

# Analysis sub-files per spec §9.2
MEDIA_JSON = "media.json"
SCENES_JSON = "scenes.json"
TRANSCRIPT_JSON = "transcript.json"
WORDS_JSON = "words.json"
SYLLABLES_JSON = "syllables.json"
SPEAKERS_JSON = "speakers.json"
FACES_JSON = "faces.json"
ACTIVE_SPEAKER_JSON = "active_speaker.json"
LOUDNESS_JSON = "loudness.json"
PITCH_DIR = "pitch"
HARMONICS_DIR = "harmonics"
SOUND_EVENTS_JSON = "sound_events.json"
MUSIC_JSON = "music.json"
CONFIDENCE_JSON = "confidence.json"

# Caption files per spec §9.2
CI_EVENTS_JSON = "ci_events.json"
REVIEW_STATE_JSON = "review_state.json"


def build_project_structure(base_dir: str | Path) -> Path:
    """Create the standard project directory structure.

    Args:
        base_dir: Root directory for the project.

    Returns:
        The base directory Path.
    """
    base = Path(base_dir)
    dirs = [
        base,
        base / ANALYSIS_DIR,
        base / CAPTIONS_DIR,
        base / CACHE_DIR,
        base / RENDERS_DIR,
        base / EXPORTS_DIR,
        base / LOGS_DIR,
        base / ANALYSIS_DIR / PITCH_DIR,
        base / ANALYSIS_DIR / HARMONICS_DIR,
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)
    return base


def save_project_metadata(project: Project, base_dir: str | Path) -> None:
    """Save project metadata file.

    Args:
        project: The project to save.
        base_dir: Project root directory.
    """
    base = Path(base_dir)
    meta_path = base / METADATA_FILE
    data = project.model_dump()
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)


def load_project_metadata(base_dir: str | Path) -> dict:
    """Load project metadata file.

    Args:
        base_dir: Project root directory.

    Returns:
        The metadata dictionary.
    """
    meta_path = Path(base_dir) / METADATA_FILE
    with open(meta_path, "r", encoding="utf-8") as f:
        return json.load(f)


def is_valid_project_dir(path: str | Path) -> bool:
    """Check if a directory contains a valid project structure."""
    return (Path(path) / METADATA_FILE).exists()
