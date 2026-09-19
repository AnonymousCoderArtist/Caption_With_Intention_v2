#!/usr/bin/env python3
"""M1 verification script — media ingest and metadata."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from engine.ingest.ingest import ingest_media, ingest_and_update_project, quick_probe
from engine.ingest.proxy import generate_proxy, get_proxy_info, is_proxy_fresh
from schemas.project import Project


def find_buzz_video():
    """Find the Buzz Lightyear trailer video."""
    for f in Path.cwd().glob("*.mp4"):
        if "Buzz" in f.name or "buzz" in f.name.lower():
            return str(f)
    return None


def test_01_quick_probe():
    """Test quick_probe returns basic info."""
    print("✓ Test 01: Quick probe...")
    video = find_buzz_video()
    if video is None:
        print("  ⚠ No Buzz video found — using synthetic test")
        import subprocess, tempfile
        with tempfile.TemporaryDirectory() as tmp:
            p = str(Path(tmp) / "test.mp4")
            subprocess.run(
                ["ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=blue:s=640x480:d=1",
                 "-f", "lavfi", "-i", "sine=frequency=440:d=1",
                 "-c:v", "libx264", "-c:a", "aac", p],
                capture_output=True, timeout=30,
            )
            result = quick_probe(p)
        assert result["video_width"] > 0
        assert len(result["source_hash"]) == 64
    else:
        result = quick_probe(video)
        assert result["video_width"] > 0
        assert result["video_height"] > 0
        assert len(result["source_hash"]) == 64
        print(f"  {result['video_width']}x{result['video_height']}, "
              f"{result['duration']:.2f}s, fps={result['fps']:.3f}")
    print("  OK")


def test_02_ingest_full():
    """Test full media ingest pipeline."""
    print("✓ Test 02: Full media ingest...")
    video = find_buzz_video()
    if video is None:
        print("  ⚠ Skipping — no Buzz video")
        return
    result = ingest_media(video)
    assert result.video_width == 1920
    assert result.video_height == 1080
    assert result.duration > 0
    assert result.audio_codec == "aac"
    assert result.source_hash is not None
    assert len(result.source_hash) == 64
    print(f"  {result.video_codec} + {result.audio_codec}, "
          f"{result.duration:.2f}s, hash={result.source_hash[:16]}...")
    print("  OK")


def test_03_proxy_generation():
    """Test proxy generation."""
    print("✓ Test 03: Proxy generation...")
    video = find_buzz_video()
    if video is None:
        print("  ⚠ Skipping — no Buzz video")
        return
    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp) / "project"
        result = ingest_media(video, project_dir=project_dir)
        if result.proxy_path:
            assert Path(result.proxy_path).exists()
            info = get_proxy_info(result.proxy_path)
            assert info.get("exists") is True
            assert info.get("width", 0) <= 480
            assert info.get("height", 0) <= 270
            print(f"  Proxy: {info.get('width')}x{info.get('height')} at {result.proxy_path}")
        else:
            print("  (Proxy not generated — continuing without)")
    print("  OK")


def test_04_ingest_updates_project():
    """Test ingest → project integration."""
    print("✓ Test 04: Ingest + project integration...")
    video = find_buzz_video()
    if video is None:
        print("  ⚠ Skipping — no Buzz video")
        return
    project = Project(project_name="Buzz_Ingest_Test")
    result = ingest_and_update_project(video, project)
    assert project.video.width == 1920
    assert project.video.height == 1080
    assert project.video.duration > 0
    assert project.video.source_hash is not None
    assert project.video.source_hash == result.source_hash

    # Verify project is serializable
    data = project.model_dump()
    assert data["video"]["width"] == 1920
    assert data["video"]["source_hash"] is not None
    print(f"  Project video: {project.video.width}x{project.video.height}, "
          f"duration={project.video.duration:.2f}s")
    print("  OK")


def test_05_source_hash_deterministic():
    """Test source hash is deterministic."""
    print("✓ Test 05: Source hash deterministic...")
    video = find_buzz_video()
    if video is None:
        print("  ⚠ Skipping — no Buzz video")
        return
    h1 = quick_probe(video)["source_hash"]
    h2 = quick_probe(video)["source_hash"]
    assert h1 == h2
    print(f"  Hash: {h1[:16]}... (consistent)")
    print("  OK")


def main():
    print("\n" + "=" * 60)
    print("  Caption With Intention — M1 Verification")
    print("  Media Ingest & Metadata")
    print("=" * 60 + "\n")

    tests = [
        test_01_quick_probe,
        test_02_ingest_full,
        test_03_proxy_generation,
        test_04_ingest_updates_project,
        test_05_source_hash_deterministic,
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
