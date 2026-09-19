"""Media probing module — FFmpeg-based video/audio inspection.

Reads media metadata WITHOUT loading the full file into memory.
"""

from __future__ import annotations

import json
import subprocess
import hashlib
from pathlib import Path
from typing import Optional

import logging

logger = logging.getLogger("caption_with_intention")


def probe_video(path: str | Path) -> dict:
    """Probe a video file using ffprobe (part of FFmpeg).

    Args:
        path: Path to video file.

    Returns:
        Dict with video metadata (duration, fps, resolution, audio info).

    Raises:
        FileNotFoundError: If ffprobe or the video is not found.
        RuntimeError: If probing fails.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Video file not found: {path}")

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
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            raise RuntimeError(
                f"ffprobe failed: {result.stderr.strip()}"
            )
        data = json.loads(result.stdout)
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"ffprobe timed out on: {path}")
    except json.JSONDecodeError as e:
        raise RuntimeError(f"ffprobe returned invalid JSON: {e}")

    return parse_probe_data(data)


def parse_probe_data(data: dict) -> dict:
    """Parse ffprobe JSON output into structured metadata.

    Args:
        data: Raw ffprobe JSON output.

    Returns:
        Structured media metadata.
    """
    video_stream = None
    audio_stream = None

    for stream in data.get("streams", []):
        if stream.get("codec_type") == "video" and video_stream is None:
            video_stream = stream
        elif stream.get("codec_type") == "audio" and audio_stream is None:
            audio_stream = stream

    format_data = data.get("format", {})

    # Video info
    width = int(video_stream.get("width", 0)) if video_stream else 0
    height = int(video_stream.get("height", 0)) if video_stream else 0
    fps = _parse_fps(video_stream) if video_stream else 0.0
    video_codec = video_stream.get("codec_name") if video_stream else None

    # Audio info
    audio_codec = audio_stream.get("codec_name") if audio_stream else None
    sample_rate = int(audio_stream.get("sample_rate", 0)) if audio_stream else None
    audio_channels = int(audio_stream.get("channels", 0)) if audio_stream else None
    audio_language = (
        audio_stream.get("tags", {}).get("language")
        if audio_stream
        else None
    )

    # Duration
    duration_str = format_data.get("duration") or video_stream.get("duration")
    duration = float(duration_str) if duration_str else 0.0

    # Pixel aspect ratio (ffprobe uses "W:H" format, e.g., "1:1")
    pixel_aspect_ratio = None
    if video_stream:
        sar = video_stream.get("sample_aspect_ratio", "1:1")
        if ":" in sar:
            num, den = sar.split(":")
            den_val = float(den) if float(den) != 0 else 1.0
            if den_val != 0:
                pixel_aspect_ratio = (float(num) / den_val, 1.0)
        elif "/" in sar:
            num, den = sar.split("/")
            den_val = float(den) if float(den) != 0 else 1.0
            if den_val != 0:
                pixel_aspect_ratio = (float(num) / den_val, 1.0)

    return {
        "width": width,
        "height": height,
        "fps": fps,
        "duration": duration,
        "video_codec": video_codec,
        "audio_codec": audio_codec,
        "audio_sample_rate": sample_rate,
        "audio_channels": audio_channels,
        "audio_language": audio_language,
        "pixel_aspect_ratio": pixel_aspect_ratio,
        "format_name": format_data.get("format_name"),
        "bit_rate": format_data.get("bit_rate"),
    }


def _parse_fps(stream: dict) -> float:
    """Parse average frame rate from ffprobe stream data."""
    r_frame_rate = stream.get("r_frame_rate", "0/0")
    if "/" in r_frame_rate:
        num, den = r_frame_rate.split("/")
        den_val = float(den) if float(den) != 0 else 1.0
        return float(num) / den_val
    return float(r_frame_rate)


def compute_source_hash(path: str | Path, chunk_size: int = 65536) -> str:
    """Compute SHA-256 hash of a source file for integrity verification.

    Args:
        path: Path to file.
        chunk_size: Read chunk size in bytes.

    Returns:
        Hex SHA-256 hash string.
    """
    sha256 = hashlib.sha256()
    path = Path(path)
    with open(path, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            sha256.update(chunk)
    return sha256.hexdigest()


def probe_embedded_captions(path: str | Path) -> list[dict]:
    """Discover embedded subtitle/caption tracks in a video.

    Args:
        path: Path to video file.

    Returns:
        List of subtitle track info dicts.
    """
    cmd = [
        "ffprobe",
        "-v",
        "quiet",
        "-print_format",
        "json",
        "-show_streams",
        "-select_streams",
        "s",
        str(Path(path)),
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        if result.returncode != 0:
            return []
        data = json.loads(result.stdout)
    except Exception:
        return []

    tracks = []
    for stream in data.get("streams", []):
        tracks.append(
            {
                "index": stream.get("index"),
                "codec": stream.get("codec_name"),
                "language": stream.get("tags", {}).get("language"),
                "title": stream.get("tags", {}).get("title"),
                "type": stream.get("codec_type"),
            }
        )
    return tracks
