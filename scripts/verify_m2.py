#!/usr/bin/env python3
"""M2 verification script — scene/chunk engine.

Verifies:
1. Shot detection produces results
2. Scene list is built correctly
3. Adaptive chunking works with overlap
4. Checkpoint save/load/resume works
5. Full pipeline: shots → scenes → chunks → checkpoints

Exit codes: 0 = all pass, 1 = any fail.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from engine.scenes.models import Scene, SceneType, Shot
from engine.scenes.chunking import ChunkConfig, generate_chunks
from engine.scenes.checkpoint import CheckpointEngine
from engine.scenes.scene_list import (
    build_scene_list,
    load_scene_list,
    save_scene_list,
    shots_to_scenes,
)
from engine.scenes.shot_detection import detect_shots, ShotBoundary


def find_buzz_video():
    for f in Path.cwd().glob("*.mp4"):
        if "Buzz" in f.name or "buzz" in f.name.lower():
            return str(f)
    return None


# ─── Test Functions ─────────────────────────────────────


def test_01_shot_detection():
    """Test shot detection returns ShotBoundary list."""
    print("✓ Test 01: Shot detection...")
    video = find_buzz_video()
    if video:
        boundaries = detect_shots(video, threshold=0.3)
        assert isinstance(boundaries, list)
        for b in boundaries:
            assert isinstance(b, ShotBoundary)
            assert b.time_sec >= 0
            assert 0 <= b.confidence <= 1
        print(f"  {len(boundaries)} shots detected")
    else:
        print("  ⚠ No Buzz video — skipping")
    print("  OK")


def test_02_scene_list_from_shots():
    """Test shots → scenes conversion."""
    print("✓ Test 02: Scene list from shots...")
    boundaries = [
        ShotBoundary(time_sec=2.0),
        ShotBoundary(time_sec=5.0),
        ShotBoundary(time_sec=20.0),
        ShotBoundary(time_sec=25.0),
    ]
    scenes = shots_to_scenes(boundaries, gap=5.0)
    assert len(scenes) >= 1
    for scene in scenes:
        assert isinstance(scene, Scene)
        assert scene.start < scene.end
        assert scene.duration > 0
    print(f"  {len(scenes)} scenes from {len(boundaries)} shots")
    print("  OK")


def test_03_adaptive_chunking():
    """Test adaptive chunking with overlap."""
    print("✓ Test 03: Adaptive chunking...")
    # Short video → 1 chunk
    chunks = generate_chunks(30.0)
    assert len(chunks) == 1
    assert chunks[0].start == 0.0
    assert chunks[0].end == 30.0

    # Long video → multiple chunks with overlap
    chunks = generate_chunks(700.0)
    assert len(chunks) >= 2
    # Verify coverage
    assert chunks[0].start == 0.0
    assert chunks[-1].end >= 699.9
    # Verify overlap exists between adjacent chunks
    if len(chunks) > 1:
        assert chunks[1].start < chunks[0].end
    print(f"  {len(chunks)} chunks for 700s video")

    # Custom chunk duration
    chunks = generate_chunks(600.0, config=ChunkConfig(chunk_duration=300.0))
    assert len(chunks) >= 2
    # Chunks cover full duration
    assert chunks[0].start == 0.0
    assert chunks[-1].end >= 599.9
    print(f"  {len(chunks)} chunks for 600s at 300s each")
    print("  OK")


def test_04_checkpoint_resume():
    """Test checkpoint save/load/resume."""
    print("✓ Test 04: Checkpoint resume...")
    with tempfile.TemporaryDirectory() as tmp:
        engine = CheckpointEngine(tmp)

        # Create master checkpoint
        engine.create_master(
            project_path="/test/project.ci",
            total_duration=120.0,
            pipeline_stages=["shot_detect", "analysis"],
        )

        # Create chunk checkpoints
        for i in range(2):
            engine.create_chunk_checkpoint(
                chunk_index=i,
                start=i * 60.0,
                end=(i + 1) * 60.0,
                pipeline_stages=["shot_detect", "analysis"],
            )
        engine.set_total_chunks(2)

        # Complete chunk 0
        engine.save_chunk_stage(
            chunk_index=0,
            stage_name="shot_detect",
            status="completed",
        )
        engine.save_chunk_stage(
            chunk_index=0,
            stage_name="analysis",
            status="completed",
        )
        engine.mark_chunk_completed(0)

        # Verify master state
        master = engine.load_master()
        assert master is not None
        assert master.is_complete is False
        assert 0 in master.completed_chunks

        # Verify chunk checkpoint
        chunk_checkpoint = engine.load_chunk_checkpoint(0)
        assert chunk_checkpoint is not None
        assert chunk_checkpoint.status == "completed"
        assert chunk_checkpoint.stages[0].status == "completed"

        # Complete chunk 1
        engine.save_chunk_stage(
            chunk_index=1,
            stage_name="shot_detect",
            status="completed",
        )
        engine.save_chunk_stage(
            chunk_index=1,
            stage_name="analysis",
            status="completed",
        )
        engine.mark_chunk_completed(1)

        master = engine.load_master()
        assert master.is_complete is True
        assert len(master.completed_chunks) == 2

        # Verify JSON files exist and are valid
        master_path = Path(tmp) / "master_checkpoint.json"
        chunk_path = Path(tmp) / "chunk_000000.json"
        assert master_path.exists()
        assert chunk_path.exists()
        import json
        with open(master_path) as f:
            m = json.load(f)
        assert "version" in m
        with open(chunk_path) as f:
            c = json.load(f)
        assert c["chunk_index"] == 0

    print("  Resume workflow verified")
    print("  OK")


def test_05_full_pipeline():
    """Test full pipeline: shots → scenes → chunks → save."""
    print("✓ Test 05: Full pipeline...")
    video = find_buzz_video()
    if video:
        result = build_scene_list(video, chunk_duration=300)
        assert "scenes" in result
        assert "shots" in result
        assert "chunks" in result
        assert "total_duration" in result
        assert result["scene_count"] >= 0
        assert result["chunk_count"] >= 1
        assert result["shot_count"] >= 0
        assert result["total_duration"] > 0

        # Verify scenes have valid structure
        for scene in result["scenes"]:
            assert "id" in scene
            assert "start" in scene
            assert "end" in scene
            assert scene["start"] < scene["end"]

        # Verify chunks cover full duration
        assert result["chunks"][0]["start"] == 0.0
        assert result["chunks"][-1]["end"] >= result["total_duration"] - 0.01

        # Save and reload scene list
        with tempfile.TemporaryDirectory() as tmp:
            scenes_path = Path(tmp) / "scenes.json"
            save_scene_list(
                [Scene(**{k: v for k, v in s.items()
                          if k in ("id", "start", "end", "scene_type",
                                   "shots", "dominant_speaker",
                                   "is_off_camera", "notes", "override")})
                 for s in result["scenes"]],
                scenes_path,
                total_duration=result["total_duration"],
            )
            loaded = load_scene_list(scenes_path)
            assert loaded["scene_count"] == result["scene_count"]

        print(f"  {result['scene_count']} scenes, {result['chunk_count']} chunks")
    else:
        print("  ⚠ No Buzz video — skipping full pipeline")
    print("  OK")


def main():
    print("\n" + "=" * 60)
    print("  Caption With Intention — M2 Verification")
    print("  Scene/Chunk Engine")
    print("=" * 60 + "\n")

    tests = [
        test_01_shot_detection,
        test_02_scene_list_from_shots,
        test_03_adaptive_chunking,
        test_04_checkpoint_resume,
        test_05_full_pipeline,
    ]

    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"  ✗ FAILED: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print("\n" + "=" * 60)
    print(f"  Results: {passed} passed, {failed} failed, {len(tests)} total")
    print("=" * 60 + "\n")

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
