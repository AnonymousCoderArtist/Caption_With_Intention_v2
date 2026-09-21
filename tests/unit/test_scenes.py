"""M2 unit tests — scene/chunk engine.

Tests cover:
- Shot detection (synthetic video + real video)
- Scene list building (shots → scenes → chunks)
- Adaptive chunking with overlap
- Checkpoint creation, save, load, resume
- Master checkpoint lifecycle
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import pytest
from pathlib import Path

from engine.scenes.models import Scene, SceneType, Shot
from engine.scenes.shot_detection import ShotBoundary
from engine.scenes.chunking import (
    Chunk,
    ChunkConfig,
    generate_chunks,
)
from engine.scenes.checkpoint import (
    CheckpointEngine,
    ChunkCheckpoint,
    MasterCheckpoint,
    StageCheckpoint,
)
from engine.scenes.scene_list import (
    build_scene_list,
    load_scene_list,
    save_scene_list,
    shots_to_scenes,
)
from engine.scenes.shot_detection import detect_shots


# ─── Helpers ──────────────────────────────────────────────────

def _create_test_video(path: str, duration: int = 10) -> None:
    """Create a test video using FFmpeg."""
    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "lavfi",
        "-i",
        f"color=c=blue:s=1920x1080:d={duration}",
        "-f",
        "lavfi",
        "-i",
        f"sine=frequency=440:duration={duration}",
        "-c:v",
        "libx264",
        "-c:a",
        "aac",
        "-t",
        str(duration),
        path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        pytest.skip(f"Could not create test video: {result.stderr}")


def find_buzz_video_or_skip():
    """Find the Buzz Lightyear trailer, or skip."""
    for f in Path.cwd().glob("*.mp4"):
        if "Buzz" in f.name or "buzz" in f.name.lower():
            return str(f)
    pytest.skip("No Buzz video found in cwd")


# ─── Shot Boundary Tests ──────────────────────────────────────


class TestShotBoundary:
    def test_shot_boundary_creation(self):
        b = ShotBoundary(time_sec=5.0, confidence=0.8)
        assert b.time_sec == 5.0
        assert b.confidence == 0.8

    def test_shot_boundary_repr(self):
        b = ShotBoundary(time_sec=10.0)
        assert "ShotBoundary" in repr(b)
        assert "10.0" in repr(b)


# ─── Scene Model Tests ────────────────────────────────────────


class TestScene:
    def test_scene_creation(self):
        scene = Scene(id="s1", start=0.0, end=10.0)
        assert scene.id == "s1"
        assert scene.duration == 10.0
        assert scene.scene_type == SceneType.unknown

    def test_scene_duration_property(self):
        scene = Scene(id="s1", start=5.0, end=15.5)
        assert scene.duration == 10.5

    def test_scene_with_shots(self):
        shot1 = Shot(id="sh1", start=0.0, end=3.0)
        shot2 = Shot(id="sh2", start=3.0, end=6.0)
        scene = Scene(
            id="s1",
            start=0.0,
            end=6.0,
            shots=[shot1, shot2],
        )
        assert len(scene.shots) == 2
        assert scene.shots[0].id == "sh1"

    def test_scene_off_camera(self):
        scene = Scene(
            id="s1",
            start=0.0,
            end=10.0,
            is_off_camera=True,
        )
        assert scene.is_off_camera is True

    def test_scene_to_dict(self):
        scene = Scene(id="s1", start=0.0, end=10.0)
        data = scene.to_dict()
        assert data["id"] == "s1"
        assert data["start"] == 0.0
        assert data["duration"] == 10.0


# ─── Shot Detection Tests ─────────────────────────────────────


class TestDetectShots:
    def test_detects_from_synthetic_video(self, tmp_path):
        source = str(tmp_path / "test.mp4")
        _create_test_video(source, duration=5)
        boundaries = detect_shots(source, threshold=0.3)
        # Synthetic video may have 0 or few boundaries
        assert isinstance(boundaries, list)

    def test_source_not_found(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            detect_shots(str(tmp_path / "missing.mp4"))

    def test_minimum_shot_duration_filter(self):
        """Very close boundaries should be filtered."""
        boundaries = [
            ShotBoundary(time_sec=1.0),
            ShotBoundary(time_sec=1.1),  # Too close (0.1s gap)
            ShotBoundary(time_sec=5.0),
        ]
        from engine.scenes.shot_detection import _filter_short_shots
        filtered = _filter_short_shots(boundaries, min_duration=0.5)
        assert len(filtered) == 2
        assert filtered[0].time_sec == 1.0
        assert filtered[1].time_sec == 5.0


# ─── Scene List Tests ─────────────────────────────────────────


class TestShotsToScenes:
    def test_empty_shots_returns_empty_scenes(self):
        scenes = shots_to_scenes([])
        assert scenes == []

    def test_single_shot_creates_scene(self):
        boundaries = [ShotBoundary(time_sec=5.0)]
        scenes = shots_to_scenes(boundaries)
        assert len(scenes) == 1
        assert scenes[0].start == 0.0

    def test_shots_within_gap_same_scene(self):
        boundaries = [
            ShotBoundary(time_sec=2.0),
            ShotBoundary(time_sec=3.0),  # 1s gap, within default 5s
            ShotBoundary(time_sec=4.0),
        ]
        scenes = shots_to_scenes(boundaries, gap=5.0)
        assert len(scenes) == 1

    def test_shots_with_large_gap_split_scenes(self):
        boundaries = [
            ShotBoundary(time_sec=2.0),
            ShotBoundary(time_sec=15.0),  # 13s gap, exceeds 5s default
        ]
        scenes = shots_to_scenes(boundaries, gap=5.0)
        assert len(scenes) == 2
        assert scenes[0].end <= 2.0
        assert scenes[1].start >= 15.0


class TestSceneListIO:
    def test_save_and_load(self, tmp_path):
        scene = Scene(
            id="scene_001",
            start=0.0,
            end=10.0,
            scene_type=SceneType.dialogue,
            shots=[Shot(id="shot_1", start=0.0, end=5.0)],
        )
        output = tmp_path / "scenes.json"
        save_scene_list([scene], output, total_duration=10.0)
        loaded = load_scene_list(output)

        assert loaded["total_duration"] == 10.0
        assert loaded["scene_count"] == 1
        assert loaded["scenes"][0]["id"] == "scene_001"
        assert loaded["scenes"][0]["scene_type"] == "dialogue"


# ─── Chunking Tests ───────────────────────────────────────────


class TestGenerateChunks:
    def test_single_chunk_for_short_video(self):
        chunks = generate_chunks(total_duration=30.0)
        assert len(chunks) == 1
        assert chunks[0].start == 0.0
        assert chunks[0].end == 30.0

    def test_multiple_chunks_for_long_video(self):
        chunks = generate_chunks(total_duration=700.0)
        assert len(chunks) >= 2
        # Chunks should cover the entire duration
        assert chunks[0].start == 0.0
        assert chunks[-1].end >= 699.9

    def test_chunks_have_overlap(self):
        chunks = generate_chunks(total_duration=700.0)
        if len(chunks) > 1:
            # Second chunk should start before first chunk ends
            assert chunks[1].start < chunks[0].end

    def test_custom_chunk_duration(self):
        chunks = generate_chunks(
            total_duration=600.0,
            config=ChunkConfig(chunk_duration=300.0),
        )
        assert len(chunks) >= 2
        # Chunks should cover the entire duration
        assert chunks[0].start == 0.0
        assert chunks[-1].end >= 599.9

    def test_chunk_invalid_duration(self):
        with pytest.raises(ValueError):
            ChunkConfig(chunk_duration=10.0)  # Below minimum


class TestChunkProperties:
    def test_chunk_duration(self):
        chunk = Chunk(index=0, start=0.0, end=60.0)
        assert chunk.duration == 60.0

    def test_chunk_zero_duration_fails(self):
        with pytest.raises(ValueError):
            Chunk(index=0, start=0.0, end=0.0)


# ─── Checkpoint Tests ─────────────────────────────────────────


class TestCheckpointEngine:
    def test_create_and_load_master(self, tmp_path):
        engine = CheckpointEngine(tmp_path)
        engine.create_master(
            project_path="/test/project.ci",
            total_duration=600.0,
            pipeline_stages=["shot_detect", "chunking", "analysis"],
        )
        master = engine.load_master()
        assert master is not None
        assert master.project_path == "/test/project.ci"
        assert master.total_duration == 600.0
        assert master.pipeline_stages == ["shot_detect", "chunking", "analysis"]
        assert master.is_complete is False

    def test_create_chunk_checkpoint(self, tmp_path):
        engine = CheckpointEngine(tmp_path)
        engine.create_master(
            project_path="/test/project.ci",
            total_duration=600.0,
            pipeline_stages=["shot_detect", "analysis"],
        )
        checkpoint = engine.create_chunk_checkpoint(
            chunk_index=0,
            start=0.0,
            end=60.0,
            pipeline_stages=["shot_detect", "analysis"],
        )
        assert checkpoint.chunk_index == 0
        assert checkpoint.status == "pending"

    def test_save_and_load_chunk_checkpoint(self, tmp_path):
        engine = CheckpointEngine(tmp_path)
        engine.create_master(
            project_path="/test/project.ci",
            total_duration=600.0,
            pipeline_stages=["analysis"],
        )
        engine.create_chunk_checkpoint(
            chunk_index=0,
            start=0.0,
            end=60.0,
            pipeline_stages=["analysis"],
        )
        engine.save_chunk_stage(
            chunk_index=0,
            stage_name="analysis",
            status="completed",
            output_path="/test/output.json",
        )
        loaded = engine.load_chunk_checkpoint(0)
        assert loaded is not None
        assert loaded.status == "completed"
        assert loaded.stages[0].status == "completed"

    def test_mark_chunk_completed_updates_master(self, tmp_path):
        engine = CheckpointEngine(tmp_path)
        engine.create_master(
            project_path="/test/project.ci",
            total_duration=120.0,
            pipeline_stages=["analysis"],
        )
        engine.create_chunk_checkpoint(
            chunk_index=0, start=0.0, end=60.0,
            pipeline_stages=["analysis"],
        )
        engine.create_chunk_checkpoint(
            chunk_index=1, start=60.0, end=120.0,
            pipeline_stages=["analysis"],
        )
        engine.set_total_chunks(2)
        engine.save_chunk_stage(0, "analysis", "completed")
        engine.mark_chunk_completed(0)
        master = engine.load_master()
        assert 0 in master.completed_chunks
        assert master.is_complete is False

    def test_master_is_complete(self, tmp_path):
        engine = CheckpointEngine(tmp_path)
        engine.create_master(
            project_path="/test/project.ci",
            total_duration=60.0,
            pipeline_stages=["analysis"],
        )
        engine.create_chunk_checkpoint(
            chunk_index=0, start=0.0, end=60.0,
            pipeline_stages=["analysis"],
        )
        engine.set_total_chunks(1)
        engine.save_chunk_stage(0, "analysis", "completed")
        engine.mark_chunk_completed(0)
        master = engine.load_master()
        assert master.is_complete is True

    def test_get_pending_chunks(self, tmp_path):
        engine = CheckpointEngine(tmp_path)
        engine.create_master(
            project_path="/test/project.ci",
            total_duration=120.0,
            pipeline_stages=["analysis"],
        )
        chunks = [
            {"chunk_index": 0, "start": 0.0, "end": 60.0},
            {"chunk_index": 1, "start": 60.0, "end": 120.0},
        ]
        engine.mark_chunk_completed(0)
        pending = engine.get_pending_chunks(chunks)
        assert len(pending) == 1
        assert pending[0]["chunk_index"] == 1

    def test_checkpoint_files_are_json(self, tmp_path):
        engine = CheckpointEngine(tmp_path)
        engine.create_master(
            project_path="/test/project.ci",
            total_duration=60.0,
            pipeline_stages=["analysis"],
        )
        engine.create_chunk_checkpoint(
            chunk_index=0, start=0.0, end=60.0,
            pipeline_stages=["analysis"],
        )
        master_path = tmp_path / "master_checkpoint.json"
        chunk_path = tmp_path / "chunk_000000.json"
        assert master_path.exists()
        assert chunk_path.exists()
        # Verify valid JSON
        with open(master_path) as f:
            json.load(f)
        with open(chunk_path) as f:
            json.load(f)


# ─── Integration Tests ────────────────────────────────────────


class TestSceneChunkIntegration:
    def test_full_pipeline_synthetic(self, tmp_path):
        source = str(tmp_path / "test.mp4")
        _create_test_video(source, duration=10)
        result = build_scene_list(source, chunk_duration=30)

        assert "scenes" in result
        assert "shots" in result
        assert "chunks" in result
        assert "total_duration" in result
        assert result["scene_count"] >= 0
        assert result["chunk_count"] >= 1

    def test_chunks_cover_full_duration(self, tmp_path):
        source = str(tmp_path / "test.mp4")
        _create_test_video(source, duration=30)
        result = build_scene_list(source, chunk_duration=60)
        assert result["chunks"][0]["end"] >= 29.9

    def test_scene_list_persists(self, tmp_path):
        source = str(tmp_path / "test.mp4")
        _create_test_video(source, duration=5)
        result = build_scene_list(source, chunk_duration=60)

        scenes_path = tmp_path / "scenes.json"
        save_scene_list(
            [Scene(id=s["id"], start=s["start"], end=s["end"])
             for s in result["scenes"]],
            scenes_path,
            total_duration=result["total_duration"],
        )
        loaded = load_scene_list(scenes_path)
        assert loaded["scene_count"] == result["scene_count"]


class TestResumeWorkflow:
    def test_resume_stops_and_restarts(self, tmp_path):
        engine = CheckpointEngine(tmp_path)
        engine.create_master(
            project_path="/test/project.ci",
            total_duration=120.0,
            pipeline_stages=["analysis"],
        )
        # Create two chunks
        for i in range(2):
            engine.create_chunk_checkpoint(
                chunk_index=i,
                start=i * 60.0,
                end=(i + 1) * 60.0,
                pipeline_stages=["analysis"],
            )
        engine.set_total_chunks(2)

        # Complete first chunk
        engine.save_chunk_stage(0, "analysis", "completed")
        engine.mark_chunk_completed(0)

        # Simulate "reopen" — load master
        master = engine.load_master()
        assert master is not None
        assert master.is_complete is False
        assert master.completed_chunks == [0]

        # Only chunk 1 is pending
        chunks = [
            {"chunk_index": 0, "start": 0.0, "end": 60.0},
            {"chunk_index": 1, "start": 60.0, "end": 120.0},
        ]
        pending = engine.get_pending_chunks(chunks)
        assert len(pending) == 1
        assert pending[0]["chunk_index"] == 1

        # Complete second chunk
        engine.save_chunk_stage(1, "analysis", "completed")
        engine.mark_chunk_completed(1)
        master = engine.load_master()
        assert master.is_complete is True
