"""Proxy video generation for fast preview/analysis.

Generates low-resolution proxy videos using FFmpeg so that downstream
processes can work with lightweight files during editing and analysis.
"""

from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from engine.errors.errors import CWIError
from engine.logging.logger import setup_logging

logger = setup_logging()


def generate_proxy(
    source_path: str | Path,
    output_path: str | Path | None = None,
    scale: float = 0.25,
    preset: str = "ultrafast",
) -> dict:
    """Generate a low-resolution proxy video using FFmpeg.

    The source file is NEVER modified. A new proxy file is created.

    Args:
        source_path: Path to the source video file.
        output_path: Where to save the proxy. If None, uses the source stem
            with ``_proxy.mp4`` in the same directory as the source.
        scale: Scale factor (0.25 = 25% of original dimensions).
        preset: FFmpeg encoding preset (ultrafast, superfast, veryfast, etc.).

    Returns:
        Dict with proxy_path, width, height, fps, duration, and ffprobe info.

    Raises:
        FileNotFoundError: If source does not exist.
        CWIError: If FFmpeg fails.
    """
    source = Path(source_path)
    if not source.exists():
        raise FileNotFoundError(f"Source video not found: {source}")

    if output_path is None:
        proxy_name = f"{source.stem}_proxy.mp4"
        output = source.parent / proxy_name
    else:
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)

    # Skip if proxy already exists and is newer than source
    if _is_proxy_fresh(source, output):
        logger.info(
            "Using existing fresh proxy: %s", output, extra={"stage": "proxy_gen"}
        )
        return _proxy_result(str(output))

    # Probe source dimensions via ffprobe
    src_w, src_h = _probe_dimensions(source)

    # Calculate scaled dimensions (even numbers required by h264)
    new_w = max(2, int(src_w * scale) // 2 * 2)
    new_h = max(2, int(src_h * scale) // 2 * 2)

    logger.info(
        "Generating proxy: %dx%d → %dx%d at %s",
        src_w, src_h, new_w, new_h, preset, extra={"stage": "proxy_gen"}
    )

    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(source),
        "-vf",
        f"scale={new_w}:{new_h}",
        "-c:v",
        "libx264",
        "-preset",
        preset,
        "-crf",
        "28",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-movflags",
        "+faststart",
        "-loglevel",
        "quiet",
        str(output),
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if result.returncode != 0:
            raise CWIError(
                f"FFmpeg proxy generation failed: {result.stderr.strip()}",
                category="output_encode_failure",
                recoverable=True,
                stage="proxy_gen",
                details={"source": str(source), "output": str(output)},
            )
    except subprocess.TimeoutExpired:
        raise CWIError(
            f"FFmpeg proxy generation timed out on: {source}",
            category="output_encode_failure",
            recoverable=True,
            stage="proxy_gen",
        )

    logger.info(
        "Proxy generated: %s (%dx%d)", output, new_w, new_h, extra={"stage": "proxy_gen"}
    )

    return _proxy_result(str(output))


def _probe_dimensions(path: Path) -> tuple[int, int]:
    """Use ffprobe to get video dimensions without full decode."""
    cmd = [
        "ffprobe",
        "-v",
        "quiet",
        "-print_format",
        "json",
        "-select_streams",
        "v:0",
        "-show_streams",
        str(path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        return 1920, 1080
    try:
        data = json.loads(result.stdout)
    except Exception:
        return 1920, 1080
    stream = data.get("streams", [{}])[0]
    return (
        int(stream.get("width", 1920)),
        int(stream.get("height", 1080)),
    )


def _is_proxy_fresh(source: Path, proxy: Path) -> bool:
    """Check if proxy exists and is newer than source.

    If source is gone but proxy exists, proxy is considered fresh.
    """
    if not proxy.exists():
        return False
    if not source.exists():
        return True
    return proxy.stat().st_mtime >= source.stat().st_mtime


def _proxy_result(proxy_path: str) -> dict:
    """Run ffprobe on proxy and return structured result."""
    from engine.media.probe import probe_video  # avoid circular import

    try:
        info = probe_video(proxy_path)
    except Exception:
        info = {"width": 0, "height": 0, "fps": 0.0, "duration": 0.0}

    return {
        "proxy_path": proxy_path,
        "width": info.get("width", 0),
        "height": info.get("height", 0),
        "fps": info.get("fps", 0.0),
        "duration": info.get("duration", 0.0),
        "video_codec": info.get("video_codec"),
        "audio_codec": info.get("audio_codec"),
        "audio_sample_rate": info.get("audio_sample_rate"),
        "audio_channels": info.get("audio_channels"),
        "format_name": info.get("format_name"),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def get_proxy_info(proxy_path: str | Path) -> dict:
    """Return basic info about a proxy video.

    Args:
        proxy_path: Path to the proxy file.

    Returns:
        Dict with existence, dimensions, duration, and freshness status.
    """
    proxy = Path(proxy_path)
    if not proxy.exists():
        return {"exists": False, "path": str(proxy)}

    from engine.media.probe import probe_video  # avoid circular import

    info = probe_video(proxy)
    source = proxy.parent / proxy.stem.replace("_proxy", "")
    has_source = source.exists()
    fresh = False
    if has_source:
        fresh = proxy.stat().st_mtime >= source.stat().st_mtime

    return {
        "exists": True,
        "path": str(proxy),
        "width": info.get("width", 0),
        "height": info.get("height", 0),
        "fps": info.get("fps", 0.0),
        "duration": info.get("duration", 0.0),
        "is_fresh": fresh,
    }


def is_proxy_fresh(source_path: str | Path, proxy_path: str | Path) -> bool:
    """Check if a proxy is current relative to its source.

    If source is gone but proxy exists, proxy is considered valid.

    Returns:
        True if proxy exists and is not older than source (or source is gone).
        False if proxy is missing.
    """
    source = Path(source_path)
    proxy = Path(proxy_path)
    if not proxy.exists():
        return False
    if not source.exists():
        return True
    return proxy.stat().st_mtime >= source.stat().st_mtime
