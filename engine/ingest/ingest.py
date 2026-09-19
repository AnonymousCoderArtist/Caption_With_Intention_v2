"""Media ingest orchestrator — full pipeline from source video to project metadata.

Combines probing, hashing, caption discovery, and proxy generation into a
single ingest step that populates a project's VideoInfo.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from pydantic import BaseModel

from engine.errors.errors import CWIError, ErrorCategory
from engine.logging.logger import setup_logging
from engine.media.probe import (
    probe_video,
    compute_source_hash,
    probe_embedded_captions,
)
from engine.ingest.proxy import generate_proxy
from schemas.project import Project, VideoInfo

logger = setup_logging()


# ─── Data Model ───────────────────────────────────────────────────────────────

class MediaIngestResult(BaseModel):
    """Result of a complete media ingest operation."""

    source_path: str
    source_hash: str
    video_width: int
    video_height: int
    fps: float
    duration: float
    video_codec: Optional[str] = None
    audio_codec: Optional[str] = None
    audio_sample_rate: Optional[int] = None
    audio_channels: Optional[int] = None
    audio_language: Optional[str] = None
    embedded_captions: list[dict] = []
    proxy_path: Optional[str] = None
    format_name: Optional[str] = None
    bit_rate: Optional[str] = None
    proxy_generated: bool = False


# ─── Main Ingest ──────────────────────────────────────────────────────────────

def ingest_media(
    source_path: str | Path,
    project_dir: str | Path | None = None,
) -> MediaIngestResult:
    """Run the full media ingest pipeline.

    1. Probe video/audio metadata (no full decode)
    2. Compute source integrity hash
    3. Discover embedded subtitle tracks
    4. Generate analysis proxy

    Args:
        source_path: Path to source video file.
        project_dir: Optional project directory for proxy placement.
            If None, proxy goes next to the source.

    Returns:
        MediaIngestResult with all gathered metadata.

    Raises:
        CWIError: If any ingest step fails.
        FileNotFoundError: If source doesn't exist.
    """
    source = Path(source_path)
    if not source.exists():
        raise FileNotFoundError(f"Source video not found: {source}")

    logger.info(
        "Starting media ingest: %s", source, extra={"stage": "media_ingest"}
    )

    # --- Step 1: Probe metadata ---
    logger.info("Probing video metadata...", extra={"stage": "media_ingest"})
    try:
        probe = probe_video(source)
    except Exception as e:
        raise CWIError(
            f"Media probe failed: {e}",
            category=ErrorCategory.unsupported_codec,
            recoverable=True,
            stage="media_ingest",
            details={"path": str(source)},
        ) from e

    # --- Step 2: Source hash ---
    logger.info("Computing source integrity hash...", extra={"stage": "media_ingest"})
    try:
        source_hash = compute_source_hash(source)
    except Exception as e:
        raise CWIError(
            f"Source hash computation failed: {e}",
            category=ErrorCategory.fatal,
            recoverable=False,
            stage="media_ingest",
            details={"path": str(source)},
        ) from e

    # --- Step 3: Embedded captions ---
    logger.info(
        "Discovering embedded captions...", extra={"stage": "media_ingest"}
    )
    try:
        captions = probe_embedded_captions(source)
    except Exception:
        captions = []

    # --- Step 4: Proxy generation ---
    proxy_path: Optional[str] = None
    if project_dir is not None:
        project_dir = Path(project_dir)
        proxy_dir = project_dir / "cache" / "proxies"
        proxy_dir.mkdir(parents=True, exist_ok=True)
        proxy_file = proxy_dir / "proxy.mp4"
    else:
        proxy_file = source.parent / "proxy.mp4"
    try:
        proxy_result = generate_proxy(source, output_path=proxy_file, scale=0.25)
        proxy_path = proxy_result.get("proxy_path")
    except Exception as e:
        logger.warning(
            "Proxy generation skipped: %s — continuing without proxy",
            e,
            extra={"stage": "media_ingest"},
        )

    # --- Build result ---
    result = MediaIngestResult(
        source_path=str(source),
        source_hash=source_hash,
        video_width=probe.get("width", 0),
        video_height=probe.get("height", 0),
        fps=probe.get("fps", 0.0),
        duration=probe.get("duration", 0.0),
        video_codec=probe.get("video_codec"),
        audio_codec=probe.get("audio_codec"),
        audio_sample_rate=probe.get("audio_sample_rate"),
        audio_channels=probe.get("audio_channels"),
        audio_language=None,
        embedded_captions=captions,
        proxy_path=proxy_path,
        format_name=probe.get("format_name"),
        bit_rate=probe.get("bit_rate"),
        proxy_generated=proxy_path is not None,
    )

    logger.info(
        "Media ingest complete: %dx%d @ %.3f fps, %.2fs, hash=%s",
        result.video_width,
        result.video_height,
        result.fps,
        result.duration,
        result.source_hash[:16],
        extra={"stage": "media_ingest"},
    )

    return result


# --- Project Integration ---

def ingest_and_update_project(
    source_path: str | Path,
    project: Project,
    project_dir: str | Path | None = None,
) -> MediaIngestResult:
    """Ingest media and update a Project object's VideoInfo in place.

    Args:
        source_path: Path to the source video.
        project: The project to update.
        project_dir: Optional project directory for proxy placement.

    Returns:
        The MediaIngestResult (also stored in project metadata).
    """
    result = ingest_media(source_path, project_dir=project_dir)

    # Update project VideoInfo
    project.video.width = result.video_width
    project.video.height = result.video_height
    project.video.fps = result.fps
    project.video.duration = result.duration
    project.video.codec = result.video_codec
    project.video.audio_codec = result.audio_codec
    project.video.audio_sample_rate = result.audio_sample_rate
    project.video.audio_channels = result.audio_channels
    project.video.source_hash = result.source_hash
    project.video.language = result.audio_language
    project.video.proxy_path = result.proxy_path

    project.modified_at = datetime.now(timezone.utc).isoformat()

    logger.info(
        "Project VideoInfo updated from ingest result",
        extra={"stage": "media_ingest"},
    )

    return result


# --- Quick Probe ---

def quick_probe(source_path: str | Path) -> dict:
    """Lightweight probe: metadata + source hash only.

    Skips proxy generation and embedded caption discovery for fast checks.

    Args:
        source_path: Path to the source video.

    Returns:
        Dict with probe results and source_hash.
    """
    source = Path(source_path)
    if not source.exists():
        raise FileNotFoundError(f"Source video not found: {source}")

    probe = probe_video(source)
    source_hash = compute_source_hash(source)

    return {
        "source_path": str(source),
        "source_hash": source_hash,
        "video_width": probe.get("width", 0),
        "video_height": probe.get("height", 0),
        "fps": probe.get("fps", 0.0),
        "duration": probe.get("duration", 0.0),
        "video_codec": probe.get("video_codec"),
        "audio_codec": probe.get("audio_codec"),
        "audio_sample_rate": probe.get("audio_sample_rate"),
        "audio_channels": probe.get("audio_channels"),
        "format_name": probe.get("format_name"),
        "bit_rate": probe.get("bit_rate"),
    }