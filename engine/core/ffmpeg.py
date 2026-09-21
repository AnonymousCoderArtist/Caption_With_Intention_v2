"""Shared FFmpeg / ffprobe subprocess utility.

Centralises all media-tool invocations so error handling, timeouts, and
metadata caching live in one place instead of being duplicated across
engine modules.
"""

from __future__ import annotations

import json
import logging
import subprocess
from pathlib import Path
from typing import Optional

logger = logging.getLogger("caption_with_intention")

# In-memory metadata cache: filepath (str) → (mtime, metadata_dict)
_metadata_cache: dict[str, tuple[float, dict]] = {}


def run_ffmpeg(cmd: list[str], timeout: int = 600) -> subprocess.CompletedProcess:
    """Run an FFmpeg command with standardised error handling.

    Returns the :class:`subprocess.CompletedProcess` on success.

    Raises
    ------
    RuntimeError
        If the process exits non-zero or times out.
    """
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError(
            f"FFmpeg timed out after {timeout}s: {' '.join(cmd[:4])}..."
        ) from None

    if result.returncode != 0:
        raise RuntimeError(
            f"FFmpeg failed: {result.stderr.strip()[:500]}"
        )
    return result


def run_ffprobe(path: str | Path, timeout: int = 30) -> subprocess.CompletedProcess:
    """Run ffprobe with standardised options.

    Returns :class:`subprocess.CompletedProcess`. Callers parse ``stdout``.
    """
    cmd = [
        "ffprobe",
        "-v",
        "quiet",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        str(path),
    ]
    try:
        return subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"ffprobe timed out on: {path}") from None


def get_ffprobe_metadata(path: str | Path) -> dict:
    """Probe a media file and return structured metadata dict.

    Results are cached in-memory keyed by absolute path; the cache is
    invalidated when the file's mtime changes.
    """
    path_str = str(Path(path).resolve())
    try:
        current_mtime = Path(path).stat().st_mtime
    except OSError:
        current_mtime = -1.0

    cached = _metadata_cache.get(path_str)
    if cached is not None and cached[0] == current_mtime:
        return cached[1]

    result = run_ffprobe(path)
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed: {result.stderr.strip()[:500]}")
    data = json.loads(result.stdout)

    _metadata_cache[path_str] = (current_mtime, data)
    return data


def clear_ffmpeg_cache() -> None:
    """Purge the in-memory ffprobe metadata cache."""
    _metadata_cache.clear()
