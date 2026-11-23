"""Bounded audio-window extraction shared by local recognition backends."""

from __future__ import annotations

import math
import os
import subprocess
import tempfile
from collections.abc import Iterator
from pathlib import Path

from engine.asr.models import TranscriptionResult
from engine.media.probe import probe_video

DEFAULT_CHUNK_DURATION = 30.0
DEFAULT_OVERLAP = 2.0


def chunk_windows(
    duration: float,
    chunk_duration: float = DEFAULT_CHUNK_DURATION,
    overlap: float = DEFAULT_OVERLAP,
) -> Iterator[tuple[float, float]]:
    """Finite windows; the last window is yielded exactly once."""
    if not all(math.isfinite(v) for v in (duration, chunk_duration, overlap)):
        raise ValueError("Chunk settings and source duration must be finite")
    if duration <= 0 or chunk_duration <= 0 or not 0 <= overlap < chunk_duration:
        raise ValueError(
            "Positive durations and overlap below chunk duration are required"
        )
    start = 0.0
    while start < duration:
        end = min(start + chunk_duration, duration)
        yield start, end
        if end >= duration:
            return
        start = end - overlap


def extract_audio_chunks(
    source_path: str | Path,
    chunk_duration: float = DEFAULT_CHUNK_DURATION,
    overlap: float = DEFAULT_OVERLAP,
) -> Iterator[tuple[float, str]]:
    """Yield source-offset and owned mono WAV, removing it on advance/close.

    Probe/extraction failures are fatal rather than returning partial success.
    Every source, including short video, is converted to a backend-readable WAV.
    """
    source = Path(source_path)
    info = probe_video(source)
    duration = float(info.get("duration", 0))
    for start, end in chunk_windows(duration, chunk_duration, overlap):
        fd, temporary = tempfile.mkstemp(suffix=".wav")
        os.close(fd)
        try:
            proc = subprocess.run(
                [
                    "ffmpeg",
                    "-v",
                    "error",
                    "-y",
                    "-ss",
                    str(start),
                    "-i",
                    str(source),
                    "-t",
                    str(end - start),
                    "-vn",
                    "-threads",
                    "1",
                    "-ac",
                    "1",
                    "-ar",
                    "16000",
                    temporary,
                ],
                capture_output=True,
                timeout=120,
                check=False,
            )
            if proc.returncode:
                raise RuntimeError(
                    f"Audio extraction failed for source window {start:.3f}-{end:.3f}"
                )
            yield start, temporary
        finally:
            Path(temporary).unlink(missing_ok=True)


def offset_result(result: TranscriptionResult, offset: float) -> None:
    """Shift words once even when segment.words shares the same objects."""
    seen: set[int] = set()
    for word in result.words + [
        word for segment in result.segments for word in segment.words
    ]:
        if id(word) not in seen:
            word.start += offset
            word.end += offset
            seen.add(id(word))
    for segment in result.segments:
        segment.start += offset
        segment.end += offset


def transcribe_chunks(
    transcriber,
    source_path: str | Path,
    chunk_duration: float,
    overlap: float,
    **kwargs,
) -> list[TranscriptionResult]:
    """Compatibility list interface. Fail loudly; do not silently drop windows.

    Returned overlap words are not deduplicated. This is not a resumable runner.
    """
    results = []
    chunks = extract_audio_chunks(source_path, chunk_duration, overlap)
    try:
        for start, path in chunks:
            result = transcriber.transcribe(path, **kwargs)
            offset_result(result, start)
            result.source_path = str(source_path)
            results.append(result)
    finally:
        chunks.close()
    return results
