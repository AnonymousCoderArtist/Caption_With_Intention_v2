"""Shot/scene boundary detection using FFmpeg.

Uses FFmpeg's `select=gt(scene...)` video filter to detect visual
scene changes. Results are returned as shot boundary timestamps.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from engine.core.ffmpeg import run_ffmpeg

logger = logging.getLogger("caption_with_intention")


@dataclass(slots=True)
class ShotBoundary:
    """A detected shot transition point."""

    time_sec: float
    confidence: float = 1.0  # Scene-change score threshold used

    def __repr__(self) -> str:
        return f"ShotBoundary(t={self.time_sec:.3f}s, conf={self.confidence:.4f})"


def detect_shots(
    source_path: str | Path,
    threshold: float = 0.3,
    min_shot_duration: float = 0.5,
) -> list[ShotBoundary]:
    """Detect shot boundaries in a video using FFmpeg scene detection.

    Uses FFmpeg's `select=gt(scene\\,threshold)` filter to find frames
    where the visual change exceeds the threshold.

    Args:
        source_path: Path to the source video.
        threshold: Scene-change threshold (0.0–1.0). Lower = more sensitive.
        min_shot_duration: Minimum duration between shot boundaries.

    Returns:
        List of ShotBoundary objects with timestamps.

    Raises:
        FileNotFoundError: If source does not exist.
        RuntimeError: If FFmpeg fails.
    """
    source = Path(source_path)
    if not source.exists():
        raise FileNotFoundError(f"Source video not found: {source}")

    logger.info("Detecting shots: %s", source, extra={"stage": "shot_detect"})

    # Use FFmpeg's scene detection filter
    # Output frame timestamps where scene change exceeds threshold
    cmd = [
        "ffmpeg",
        "-i",
        str(source),
        "-filter:v",
        f"select=gt(scene\\,{threshold})",
        "-vsync",
        "0",
        "-f",
        "null",
        "-",
    ]

    result = run_ffmpeg(cmd, timeout=600)
    boundaries = _parse_shot_output(result.stderr, source)

    # Filter boundaries that are too close together
    filtered = _filter_short_shots(boundaries, min_shot_duration)

    logger.info(
        "Shot detection complete: %d shots found in %s",
        len(filtered) + 1,
        source,
        extra={"stage": "shot_detect"},
    )

    return filtered


def _parse_shot_output(stderr: str, source: Path) -> list[ShotBoundary]:
    """Parse FFmpeg stderr for scene-change timestamps."""
    boundaries: list[ShotBoundary] = []

    # FFmpeg logs lines like:
    #   [Parsed_select_0 @ ...] n:1234 pts:12345 pts_time:51.42 score:0.45
    # or:
    #   frame=  123 fps=... q=... score=0.45
    #
    # We look for lines containing "score:" or "pts_time:" in filter output.

    for line in stderr.splitlines():
        if "score:" in line.lower() or "pts_time:" in line.lower():
            time_sec = _extract_time_from_line(line)
            if time_sec is not None:
                # Try to extract confidence score
                confidence = _extract_score_from_line(line)
                boundaries.append(
                    ShotBoundary(time_sec=time_sec, confidence=confidence)
                )

    # Sort by time
    boundaries.sort(key=lambda b: b.time_sec)
    return boundaries


def _extract_time_from_line(line: str) -> Optional[float]:
    """Extract timestamp from a FFmpeg filter log line."""
    import re

    # Look for pts_time:XX.XX pattern
    match = re.search(r"pts_time:(\d+\.?\d*)", line)
    if match:
        return float(match.group(1))

    # Fallback: look for frame numbers and convert (less precise)
    match = re.search(r"n:(\d+)", line)
    if match:
        frame_num = int(match.group(1))
        # We can't accurately convert without fps; skip this approach
        return None

    return None


def _extract_score_from_line(line: str) -> float:
    """Extract scene-change score from a FFmpeg filter log line."""
    import re

    match = re.search(r"score:(\d+\.?\d*)", line)
    if match:
        return float(match.group(1))
    return 1.0


def _filter_short_shots(
    boundaries: list[ShotBoundary], min_duration: float
) -> list[ShotBoundary]:
    """Remove shot boundaries that are too close together."""
    if not boundaries:
        return []

    filtered = [boundaries[0]]
    for boundary in boundaries[1:]:
        if boundary.time_sec - filtered[-1].time_sec >= min_duration:
            filtered.append(boundary)

    return filtered


def detect_shots_via_keyframes(
    source_path: str | Path,
) -> list[ShotBoundary]:
    """Alternative shot detection using keyframe timestamps.

    Fallback method: extract keyframe positions from the video stream,
    which approximate scene boundaries (encoders place keyframes at
    scene changes when configured for scene detection).

    Args:
        source_path: Path to the source video.

    Returns:
        List of ShotBoundary objects with timestamps.
    """
    source = Path(source_path)
    if not source.exists():
        raise FileNotFoundError(f"Source video not found: {source}")

    cmd = [
        "ffprobe",
        "-v",
        "quiet",
        "-print_format",
        "json",
        "-select_streams",
        "v:0",
        "-show_entries",
        "packet=pts_time,flags",
        "-read_intervals",
        "%+10",  # Read first 10 packets as a probe
        str(source),
    ]

    try:
        result = run_ffmpeg(cmd, timeout=30)
    except RuntimeError:
        return []

    if result.returncode != 0:
        return []

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        return []

    boundaries: list[ShotBoundary] = []
    for packet in data.get("packets", []):
        flags = packet.get("flags", "")
        pts_time = packet.get("pts_time")
        if "key" in flags and pts_time is not None:
            boundaries.append(
                ShotBoundary(time_sec=float(pts_time), confidence=0.5)
            )

    return boundaries[:50]  # Limit to first 50 keyframes for safety
