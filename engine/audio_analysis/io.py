"""Load mono analysis audio without retaining temporary extracted files."""
from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path

import numpy as np
import soundfile as sf


def load_analysis_audio(source_path: str | Path, target_rate: int = 16000) -> tuple[np.ndarray, int]:
    """Keep WAV sample rate; decode other containers to target-rate mono once."""
    source = Path(source_path)
    temporary = None
    try:
        audio_path = source
        if source.suffix.lower() != ".wav":
            fd, temporary = tempfile.mkstemp(suffix=".wav")
            os.close(fd)
            proc = subprocess.run(
                ["ffmpeg", "-y", "-i", str(source), "-vn", "-ac", "1", "-ar", str(target_rate), temporary],
                capture_output=True, timeout=120, check=False,
            )
            if proc.returncode:
                raise RuntimeError(f"ffmpeg audio extraction failed for {source}")
            audio_path = Path(temporary)
        audio, sample_rate = sf.read(str(audio_path), dtype="float32")
        if audio.ndim > 1:
            audio = audio.mean(axis=1)
        if not np.isfinite(audio).all():
            raise ValueError("Analysis audio contains non-finite samples")
        return audio, sample_rate
    finally:
        if temporary:
            Path(temporary).unlink(missing_ok=True)
