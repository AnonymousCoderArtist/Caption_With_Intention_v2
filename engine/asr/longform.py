"""Shared long-form audio helpers for ASR backends.

Chunked transcription keeps memory bounded on long videos (spec §9 and
M13): ffmpeg extracts overlapping 16 kHz mono WAV windows, the backend
transcribes each window, and results are returned per chunk.
"""

from __future__ import annotations

import logging
import os
import subprocess
import tempfile
from collections.abc import Iterator
from pathlib import Path

from engine.media.probe import probe_video

logger = logging.getLogger("caption_with_intention")

DEFAULT_CHUNK_DURATION = 30.0
DEFAULT_OVERLAP = 2.0


def extract_audio_chunks(
    source_path: str | Path,
    chunk_duration: float = DEFAULT_CHUNK_DURATION,
    overlap: float = DEFAULT_OVERLAP,
) -> Iterator[tuple[float, str]]:
    """Yield (start_seconds, wav_path) chunks of a source's audio track.

    Each chunk is a freshly extracted 16 kHz mono WAV. The caller owns
    the file and should delete it when done.

    A source shorter than chunk_duration yields the whole file once at
    offset 0. Sources without a probed duration yield the source path
    itself at offset 0 (assumed already backend-readable).
    """
    source = Path(source_path)
    try:
        info = probe_video(source)
        duration = float(info.get("duration", 0.0))
    except Exception as e:  # noqa: BLE001 - probing is best-effort
        logger.debug("Could not probe %s (%s); treating as single chunk", source, e)
        duration = 0.0

    if duration <= chunk_duration:
        yield 0.0, str(source)
        return

    start = 0.0
    while start < duration:
        end = min(start + chunk_duration, duration)
        logger.info("Extracting audio chunk: %.2fs - %.2fs", start, end)

        fd, chunk_path = tempfile.mkstemp(suffix=".wav")
        os.close(fd)
        cmd = [
            "ffmpeg",
            "-y",
            "-ss",
            str(start),
            "-i",
            str(source),
            "-to",
            str(end),
            "-ac",
            "1",
            "-ar",
            "16000",
            chunk_path,
        ]
        proc = subprocess.run(cmd, capture_output=True, timeout=120, check=False)
        if proc.returncode == 0:
            yield start, chunk_path
        else:
            logger.warning(
                "ffmpeg chunk extraction failed at %.2fs: %s",
                start,
                proc.stderr.decode(errors="replace")[-200:],
            )
            try:
                os.remove(chunk_path)
            except OSError:
                pass

        # Overlap for continuity; cap at half the chunk so the loop
        # always advances even with a misconfigured overlap.
        start = end - min(overlap, chunk_duration * 0.5)
