"""Scene list builder — groups shots into scenes, writes scenes.json.

This module bridges shot detection and chunking by converting
raw shot boundaries into a structured scene list that the
chunk engine can consume.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

from engine.scenes.chunking import (
    ChunkConfig,
    DEFAULT_CHUNK_DURATION,
    generate_chunks,
)
from engine.scenes.models import Scene, SceneType, Shot
from engine.scenes.shot_detection import detect_shots, ShotBoundary

logger = logging.getLogger("caption_with_intention")

# Default gap between shots before we start a new scene
DEFAULT_SCENE_GAP = 5.0  # seconds
# Default minimum scene duration
MIN_SCENE_DURATION = 3.0


def build_scene_list(
    source_path: str | Path,
    shot_threshold: float = 0.3,
    min_shot_duration: float = 0.5,
    scene_gap: float = DEFAULT_SCENE_GAP,
    chunk_duration: float = DEFAULT_CHUNK_DURATION,
) -> dict:
    """Full pipeline: detect shots → build scenes → generate chunks.

    Args:
        source_path: Path to source video.
        shot_threshold: FFmpeg scene detection threshold.
        min_shot_duration: Minimum time between shot boundaries.
        scene_gap: Gap between shots that starts a new scene.
        chunk_duration: Duration per chunk in seconds.

    Returns:
        Dict with 'scenes', 'shots', and 'chunks' keys.
    """
    # 1. Detect shots
    shots = detect_shots(
        source_path,
        threshold=shot_threshold,
        min_shot_duration=min_shot_duration,
    )

    # 2. Convert shots to scene segments
    scenes = shots_to_scenes(shots, scene_gap)

    # 3. Get video duration from probe (use last scene end)
    from engine.media.probe import probe_video
    try:
        info = probe_video(source_path)
        total_duration = info.get("duration", scenes[-1].end if scenes else 0)
    except Exception:
        total_duration = scenes[-1].end if scenes else 0

    # 4. Generate chunks
    config = ChunkConfig(chunk_duration=chunk_duration)
    chunks = generate_chunks(total_duration, config)

    return {
        "shots": [s.to_dict() if hasattr(s, "to_dict") else {
            "time_sec": s.time_sec,
            "confidence": s.confidence,
        } for s in shots],
        "scenes": [sc.to_dict() for sc in scenes],
        "chunks": [c.to_dict() for c in chunks],
        "total_duration": total_duration,
        "shot_count": len(shots),
        "scene_count": len(scenes),
        "chunk_count": len(chunks),
    }


def shots_to_scenes(
    shot_boundaries: list[ShotBoundary],
    gap: float = DEFAULT_SCENE_GAP,
) -> list[Scene]:
    """Convert shot boundaries into Scene objects.

    Shots within `gap` seconds of each other are considered
    part of the same scene. Larger gaps start new scenes.

    Args:
        shot_boundaries: List of detected shot boundaries.
        gap: Time gap threshold for scene splitting.

    Returns:
        List of Scene objects with shot assignments.
    """
    if not shot_boundaries:
        return []

    scenes: list[Scene] = []
    scene_start = 0.0
    scene_shots: list[Shot] = []

    # First shot: 0 to first boundary
    first = shot_boundaries[0]
    scene_shots.append(
        Shot(id="shot_0", start=0.0, end=first.time_sec)
    )

    for i in range(1, len(shot_boundaries)):
        prev_time = shot_boundaries[i - 1].time_sec
        curr_time = shot_boundaries[i].time_sec
        gap_duration = curr_time - prev_time

        if gap_duration > gap:
            # End current scene at previous boundary
            scene = _create_scene(
                scenes, scene_start, prev_time, scene_shots
            )
            scenes.append(scene)
            # Start new scene at current boundary
            scene_start = curr_time
            scene_shots = []
        else:
            # Same scene — add shot from prev to current boundary
            scene_shots.append(
                Shot(
                    id=f"shot_{i}",
                    start=prev_time,
                    end=curr_time,
                )
            )

    # Flush remaining shots or create empty scene at last boundary
    if scene_shots:
        last_end = scene_shots[-1].end
        scene = _create_scene(
            scenes, scene_start, last_end, scene_shots
        )
        scenes.append(scene)
    elif scene_start > 0 or len(scenes) == 0:
        # Last boundary started a scene with no subsequent shot
        scene = _create_scene(
            scenes, scene_start, scene_start, []
        )
        scenes.append(scene)

    return scenes


def _create_scene(
    existing_scenes: list[Scene],
    start: float,
    end: float,
    shots: list[Shot],
) -> Scene:
    """Create a Scene from shot list."""
    scene_id = f"scene_{len(existing_scenes):03d}"
    return Scene(
        id=scene_id,
        start=start,
        end=end,
        scene_type=SceneType.dialogue,
        shots=shots,
    )


def save_scene_list(
    scenes: list[Scene],
    output_path: str | Path,
    total_duration: float = 0.0,
) -> None:
    """Save scene list to a JSON file (scenes.json).

    Args:
        scenes: List of Scene objects.
        output_path: Path to output JSON file.
        total_duration: Total video duration.
    """
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "version": "1",
        "total_duration": total_duration,
        "scene_count": len(scenes),
        "scenes": [
            {
                "id": scene.id,
                "start": scene.start,
                "end": scene.end,
                "scene_type": scene.scene_type.value
                if hasattr(scene.scene_type, "value")
                else str(scene.scene_type),
                "shot_count": len(scene.shots),
                "shots": [
                    {
                        "id": shot.id,
                        "start": shot.start,
                        "end": shot.end,
                        "shot_type": shot.shot_type,
                        "is_reaction_shot": shot.is_reaction_shot,
                    }
                    for shot in scene.shots
                ],
                "dominant_speaker": scene.dominant_speaker,
                "is_off_camera": scene.is_off_camera,
                "notes": scene.notes,
                "override": scene.override,
            }
            for scene in scenes
        ],
    }

    with open(output, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)

    logger.info(
        "Scene list saved: %d scenes → %s",
        len(scenes),
        output,
        extra={"stage": "scene_list"},
    )


def load_scene_list(
    path: str | Path,
) -> dict:
    """Load scene list from a JSON file."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
