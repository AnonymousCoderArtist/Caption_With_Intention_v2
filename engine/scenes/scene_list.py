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

from engine.scenes.chunking import ChunkConfig, generate_chunks
from engine.scenes.models import Scene, SceneType, Shot, ShotBoundary
from engine.scenes.shot_detection import detect_shots

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
    chunk_duration: float = ChunkConfig.chunk_duration,  # type: ignore[assignment]
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
    current_scene_shots: list[Shot] = []
    scene_start = 0.0

    # Add a synthetic "end of video" boundary
    # Use a reasonable end if we can't detect it
    last_time = shot_boundaries[-1].time_sec
    # We'll estimate end as some time after last shot

    for i, boundary in enumerate(shot_boundaries):
        if i == 0:
            # First shot starts at 0
            current_scene_shots.append(
                Shot(
                    id=f"shot_000",
                    start=0.0,
                    end=boundary.time_sec,
                )
            )
            scene_start = 0.0
            continue

        gap_duration = boundary.time_sec - shot_boundaries[i - 1].time_sec

        if gap_duration > gap:
            # End current scene and start new one
            end_time = shot_boundaries[i - 1].time_sec
            scene = _create_scene(
                scenes,
                scene_start,
                end_time,
                current_scene_shots,
            )
            scenes.append(scene)

            # Start new scene
            current_scene_shots = [
                Shot(
                    id=f"shot_{len(scenes) * 1000}",
                    start=end_time,
                    end=boundary.time_sec,
                )
            ]
            scene_start = end_time
        else:
            # Same scene — add shot
            current_scene_shots.append(
                Shot(
                    id=f"shot_{len(current_scene_shots)}",
                    start=shot_boundaries[i - 1].time_sec,
                    end=boundary.time_sec,
                )
            )

    # Handle last scene (up to end of video or last shot + buffer)
    if current_scene_shots:
        last_shot_end = current_scene_shots[-1].end
        scene = _create_scene(
            scenes,
            scene_start,
            last_shot_end,
            current_scene_shots,
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
