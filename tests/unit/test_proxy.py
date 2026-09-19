"""Tests for engine.ingest.proxy."""

from __future__ import annotations

import pytest
import subprocess
import tempfile
import os
import time
from pathlib import Path

from engine.ingest.proxy import generate_proxy, get_proxy_info, is_proxy_fresh
from engine.media.probe import probe_video


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


class TestGenerateProxy:
    def test_returns_dict_with_required_keys(self, tmp_path):
        source = str(tmp_path / "source.mp4")
        _create_test_video(source, duration=2)
        result = generate_proxy(source)
        assert "proxy_path" in result
        assert "width" in result
        assert "height" in result
        assert "duration" in result
        assert "video_codec" in result or "audio_codec" in result

    def test_proxy_dimensions_are_scaled(self, tmp_path):
        source = str(tmp_path / "source.mp4")
        _create_test_video(source, duration=2)
        result = generate_proxy(source, scale=0.25)
        assert result["width"] == 480
        assert result["height"] == 270

    def test_custom_output_path(self, tmp_path):
        source = str(tmp_path / "source.mp4")
        output = str(tmp_path / "custom_proxy.mp4")
        _create_test_video(source, duration=2)
        result = generate_proxy(source, output_path=output)
        assert result["proxy_path"] == output
        assert Path(output).exists()

    def test_default_output_path(self, tmp_path):
        source = str(tmp_path / "my_video.mp4")
        _create_test_video(source, duration=2)
        result = generate_proxy(source)
        expected = str(tmp_path / "my_video_proxy.mp4")
        assert result["proxy_path"] == expected
        assert Path(expected).exists()

    def test_does_not_modify_source(self, tmp_path):
        source = str(tmp_path / "source.mp4")
        _create_test_video(source, duration=2)
        source_mtime = Path(source).stat().st_mtime
        result = generate_proxy(source, scale=0.5)
        assert Path(source).exists()
        assert Path(source).stat().st_mtime == source_mtime
        src_info = probe_video(source)
        assert src_info["width"] == 1920
        assert src_info["height"] == 1080

    def test_raises_file_not_found(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            generate_proxy(str(tmp_path / "nonexistent.mp4"))

    def test_audio_stream_copied(self, tmp_path):
        """Verify audio codec is preserved in proxy."""
        source = str(tmp_path / "source.mp4")
        _create_test_video(source, duration=2)
        result = generate_proxy(source)
        assert result["audio_codec"] == "aac"
        assert result["width"] == 480
        assert result["height"] == 270

    def test_custom_preset(self, tmp_path):
        source = str(tmp_path / "source.mp4")
        _create_test_video(source, duration=1)
        result = generate_proxy(source, preset="ultrafast")
        assert result["width"] > 0


class TestGetProxyInfo:
    def test_returns_info_for_existing_proxy(self, tmp_path):
        source = str(tmp_path / "source.mp4")
        _create_test_video(source, duration=2)
        proxy = str(tmp_path / "source_proxy.mp4")
        generate_proxy(source, output_path=proxy)
        info = get_proxy_info(proxy)
        assert info["exists"] is True
        assert info["width"] > 0
        assert info["height"] > 0
        assert info["duration"] > 0

    def test_returns_exists_false_for_missing(self, tmp_path):
        info = get_proxy_info(str(tmp_path / "no_proxy.mp4"))
        assert info["exists"] is False

    def test_missing_file_returns_exists_false(self, tmp_path):
        """Non-existent proxy returns exists=False, not an exception."""
        info = get_proxy_info(str(tmp_path / "missing.mp4"))
        assert isinstance(info, dict)
        assert info.get("exists") is False


class TestIsProxyFresh:
    def test_proxy_older_than_source(self, tmp_path):
        source = str(tmp_path / "source.mp4")
        proxy = str(tmp_path / "proxy.mp4")
        _create_test_video(source, duration=2)
        _create_test_video(proxy, duration=2)
        future_time = time.time() + 1000
        os.utime(source, (future_time, future_time))
        assert is_proxy_fresh(source, proxy) is False

    def test_proxy_newer_than_source(self, tmp_path):
        source = str(tmp_path / "source.mp4")
        proxy = str(tmp_path / "proxy.mp4")
        _create_test_video(source, duration=2)
        _create_test_video(proxy, duration=2)
        assert is_proxy_fresh(source, proxy) is True

    def test_missing_proxy_returns_false(self, tmp_path):
        source = str(tmp_path / "source.mp4")
        _create_test_video(source, duration=2)
        assert is_proxy_fresh(source, str(tmp_path / "missing_proxy.mp4")) is False

    def test_missing_source_returns_true(self, tmp_path):
        """If source is gone but proxy exists, proxy is considered fresh."""
        proxy = str(tmp_path / "proxy.mp4")
        _create_test_video(proxy, duration=2)
        assert is_proxy_fresh(str(tmp_path / "missing_source.mp4"), proxy) is True
