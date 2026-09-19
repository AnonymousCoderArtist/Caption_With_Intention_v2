"""M1 unit tests — media ingest and metadata.

Tests cover:
- Proxy generation
- Ingest orchestrator (probe, hash, captions, proxy, result model)
- Ingest + project integration
- Quick probe
- Source hash verification
- Proxy freshness checks
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import pytest
from pathlib import Path

from schemas.project import Project, VideoInfo
from engine.ingest.ingest import (
    ingest_media,
    ingest_and_update_project,
    quick_probe,
    MediaIngestResult,
)
from engine.ingest.proxy import (
    generate_proxy,
    get_proxy_info,
    is_proxy_fresh,
)


# ─── Helpers ──────────────────────────────────────────────────────────

def _create_test_video(path: str, duration: int = 2) -> None:
    """Create a minimal test video using FFmpeg."""
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


def find_buzz_video_or_skip(tmp_path=None):
    """Find the Buzz Lightyear trailer, or skip the test if not found."""
    for f in Path.cwd().glob("*.mp4"):
        if "Buzz" in f.name or "buzz" in f.name.lower():
            return str(f)
    return None


# ─── Proxy Generation Tests ───────────────────────────────────────────

class TestGenerateProxy:
    def test_proxy_creates_file(self, tmp_path):
        source = str(tmp_path / "source.mp4")
        _create_test_video(source, duration=1)
        result = generate_proxy(source, output_path=str(tmp_path / "proxy.mp4"))
        assert Path(result["proxy_path"]).exists()

    def test_proxy_is_smaller(self, tmp_path):
        video = find_buzz_video_or_skip(tmp_path)
        if video is None:
            pytest.skip("No Buzz video for proxy size comparison")
        proxy_path = str(tmp_path / "proxy.mp4")
        generate_proxy(video, output_path=proxy_path, scale=0.25)
        src_size = Path(video).stat().st_size
        proxy_size = Path(proxy_path).stat().st_size
        assert proxy_size < src_size

    def test_proxy_dimensions_scaled(self, tmp_path):
        source = str(tmp_path / "source.mp4")
        _create_test_video(source, duration=1)
        proxy_path = str(tmp_path / "proxy.mp4")
        result = generate_proxy(source, output_path=proxy_path, scale=0.25)
        assert result["width"] <= 480
        assert result["height"] <= 270

    def test_proxy_does_not_modify_source(self, tmp_path):
        source = str(tmp_path / "source.mp4")
        _create_test_video(source, duration=1)
        src_mtime_before = Path(source).stat().st_mtime
        generate_proxy(source, output_path=str(tmp_path / "proxy.mp4"))
        src_mtime_after = Path(source).stat().st_mtime
        assert src_mtime_before == src_mtime_after

    def test_proxy_fresh_after_generation(self, tmp_path):
        source = str(tmp_path / "source.mp4")
        _create_test_video(source, duration=1)
        proxy_path = str(tmp_path / "proxy.mp4")
        generate_proxy(source, output_path=proxy_path)
        assert is_proxy_fresh(source, proxy_path)

    def test_proxy_source_not_found(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            generate_proxy(str(tmp_path / "nonexistent.mp4"))

    def test_proxy_default_path(self, tmp_path):
        source = str(tmp_path / "my_video.mp4")
        _create_test_video(source, duration=1)
        result = generate_proxy(source, scale=0.25)
        assert "proxy" in result["proxy_path"]
        assert result["proxy_path"].endswith(".mp4")


class TestProxyInfo:
    def test_returns_info_for_existing_proxy(self, tmp_path):
        source = str(tmp_path / "source.mp4")
        _create_test_video(source, duration=1)
        proxy = str(tmp_path / "source_proxy.mp4")
        generate_proxy(source, output_path=proxy)
        info = get_proxy_info(proxy)
        assert info["exists"] is True
        assert info["width"] > 0
        assert info["duration"] > 0

    def test_returns_missing_for_nonexistent(self, tmp_path):
        info = get_proxy_info(str(tmp_path / "no_proxy.mp4"))
        assert info["exists"] is False


# ─── Ingest Orchestrator Tests ────────────────────────────────────────

class TestIngestMedia:
    def test_returns_media_ingest_result(self, tmp_path):
        source = str(tmp_path / "source.mp4")
        _create_test_video(source, duration=2)
        result = ingest_media(source)
        assert isinstance(result, MediaIngestResult)

    def test_result_has_required_fields(self, tmp_path):
        source = str(tmp_path / "source.mp4")
        _create_test_video(source, duration=2)
        result = ingest_media(source)
        assert result.source_path == source
        assert len(result.source_hash) == 64  # SHA-256 hex
        assert result.video_width == 1920
        assert result.video_height == 1080
        assert result.duration > 0
        assert result.fps > 0
        assert result.video_codec == "h264"
        assert result.audio_codec == "aac"
        assert result.audio_sample_rate == 44100
        assert isinstance(result.audio_channels, int)
        assert result.audio_channels >= 1

    def test_source_hash_is_deterministic(self, tmp_path):
        source = str(tmp_path / "source.mp4")
        _create_test_video(source, duration=1)
        result1 = ingest_media(source)
        result2 = ingest_media(source)
        assert result1.source_hash == result2.source_hash

    def test_embedded_captions_is_list(self, tmp_path):
        source = str(tmp_path / "source.mp4")
        _create_test_video(source, duration=1)
        result = ingest_media(source)
        assert isinstance(result.embedded_captions, list)

    def test_proxy_generated(self, tmp_path):
        source = str(tmp_path / "source.mp4")
        _create_test_video(source, duration=1)
        project_dir = str(tmp_path / "project")
        result = ingest_media(source, project_dir=project_dir)
        assert result.proxy_path is not None
        assert Path(result.proxy_path).exists()

    def test_ingest_source_not_found(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            ingest_media(str(tmp_path / "missing.mp4"))


class TestIngestAndUpdateProject:
    def test_updates_project_video_info(self, tmp_path):
        source = str(tmp_path / "source.mp4")
        _create_test_video(source, duration=2)
        project = Project(project_name="Test")
        result = ingest_and_update_project(source, project)
        assert project.video.width == 1920
        assert project.video.height == 1080
        assert project.video.duration > 0
        assert project.video.fps > 0
        assert project.video.source_hash == result.source_hash
        assert project.video.source_hash is not None

    def test_project_has_hash_after_ingest(self, tmp_path):
        source = str(tmp_path / "source.mp4")
        _create_test_video(source, duration=1)
        project = Project(project_name="HashTest")
        ingest_and_update_project(source, project)
        assert project.video.source_hash is not None
        assert len(project.video.source_hash) == 64


class TestQuickProbe:
    def test_returns_minimal_info(self, tmp_path):
        source = str(tmp_path / "source.mp4")
        _create_test_video(source, duration=1)
        result = quick_probe(source)
        assert "source_path" in result
        assert "source_hash" in result
        assert "video_width" in result
        assert "video_height" in result
        assert "duration" in result
        assert "fps" in result

    def test_quick_probe_no_proxy(self, tmp_path):
        source = str(tmp_path / "source.mp4")
        _create_test_video(source, duration=1)
        project_dir = str(tmp_path / "project")
        result = quick_probe(source)
        # quick_probe should NOT create a proxy
        assert not any(
            Path(project_dir).rglob("*_proxy.mp4")
        ) if Path(project_dir).exists() else True

    def test_quick_probe_source_not_found(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            quick_probe(str(tmp_path / "missing.mp4"))


# ─── Real Video Tests ─────────────────────────────────────────────────

class TestRealVideoIngest:
    """Tests against the actual Buzz Lightyear trailer in the repo."""

    @pytest.fixture(scope="class")
    def buzz_path(self):
        for f in Path.cwd().glob("*.mp4"):
            if "Buzz" in f.name or "buzz" in f.name.lower():
                return str(f)
        pytest.skip("Buzz Lightyear video not found in cwd")

    def test_probe_real_video(self, buzz_path):
        result = quick_probe(buzz_path)
        assert result["video_width"] > 0
        assert result["video_height"] > 0
        assert result["duration"] > 0
        assert result["fps"] > 0

    def test_real_video_hash(self, buzz_path):
        result = quick_probe(buzz_path)
        assert len(result["source_hash"]) == 64
        # Verify deterministic
        result2 = quick_probe(buzz_path)
        assert result["source_hash"] == result2["source_hash"]

    def test_real_video_metadata(self, buzz_path):
        result = ingest_media(buzz_path)
        assert result.video_width == 1920
        assert result.video_height == 1080
        assert result.duration > 100  # ~150s for the trailer
        assert 20 < result.fps < 25  # ~24fps
        assert result.audio_codec == "aac"
        assert result.audio_sample_rate == 44100

    def test_real_video_ingest_updates_project(self, buzz_path, tmp_path):
        project_dir = Path(tmp_path) / "buzz_project"
        project = Project(project_name="BuzzProject")
        result = ingest_and_update_project(buzz_path, project, project_dir=project_dir)
        assert project.video.width == 1920
        assert project.video.height == 1080
        assert project.video.duration > 100
        assert project.video.source_hash == result.source_hash
        # Project should be serializable
        project_path = project_dir / "BuzzProject.ci"
        project_json = project.model_dump()
        assert "video" in project_json
        assert project_json["video"]["width"] == 1920
