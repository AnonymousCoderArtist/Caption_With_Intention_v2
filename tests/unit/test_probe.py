"""FFmpeg-based media probe integration test."""

from __future__ import annotations

import pytest
import tempfile
import subprocess
import json
import os
from pathlib import Path

from engine.media.probe import probe_video, compute_source_hash, probe_embedded_captions


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


class TestProbeVideo:
    def test_probe_returns_metadata(self, tmp_path):
        video_path = str(tmp_path / "test.mp4")
        _create_test_video(video_path, duration=2)
        result = probe_video(video_path)
        assert "width" in result
        assert "height" in result
        assert "duration" in result
        assert "fps" in result
        assert "audio_sample_rate" in result

    def test_probe_resolution(self, tmp_path):
        video_path = str(tmp_path / "hd.mp4")
        _create_test_video(video_path, duration=1)
        result = probe_video(video_path)
        assert result["width"] == 1920
        assert result["height"] == 1080

    def test_probe_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            probe_video("/nonexistent/video.mp4")

    def test_probe_ffmpeg_available(self):
        """Verify ffprobe is installed."""
        result = subprocess.run(
            ["ffprobe", "-version"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0


class TestComputeSourceHash:
    def test_hash_returns_string(self, tmp_path):
        test_file = tmp_path / "test.txt"
        test_file.write_text("hello world")
        hash_value = compute_source_hash(str(test_file))
        assert isinstance(hash_value, str)
        assert len(hash_value) == 64  # SHA-256 hex length

    def test_hash_is_deterministic(self, tmp_path):
        test_file = tmp_path / "test.txt"
        test_file.write_text("same content")
        hash1 = compute_source_hash(str(test_file))
        hash2 = compute_source_hash(str(test_file))
        assert hash1 == hash2

    def test_different_content_different_hash(self, tmp_path):
        file1 = tmp_path / "a.txt"
        file2 = tmp_path / "b.txt"
        file1.write_text("content A")
        file2.write_text("content B")
        assert compute_source_hash(str(file1)) != compute_source_hash(str(file2))


class TestProbeEmbeddedCaptions:
    def test_returns_list(self, tmp_path):
        video_path = str(tmp_path / "test.mp4")
        _create_test_video(video_path, duration=1)
        result = probe_embedded_captions(video_path)
        assert isinstance(result, list)
