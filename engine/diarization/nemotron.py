"""Nemotron 3 Diarization backend — NVIDIA open-weight model via audio.cpp.

Model: ``nvidia/Nemotron-3-Diarization`` (~100M-parameter transformer,
released 2026-09-23).  Open-weights under OpenMDW-1.1, up to eight
speakers, overlap-aware, 16 kHz mono input, real per-turn confidence.

Runtime: the ``audiocpp_cli`` binary from audio.cpp (CPU or GPU).  The
weights are the community GGUF port, downloaded once on first use
(~102 MB, Q8_0) into a local cache; afterwards the backend runs fully
offline.

CPU benchmark on a 4-core i5-class box (8 GB RAM): ~1 minute per
10-minute chunk, peak RSS ~460 MB.  See ``tools/nemotron-bench/RESULTS.md``.

Resolution order
-----------------
CLI binary: ``cli_path`` kwarg -> ``CWI_AUDIOCPP_CLI`` env ->
``PATH`` -> dev build under ``tools/nemotron-bench``.
Model file: ``model_path`` kwarg -> ``CWI_NEMOTRON_MODEL`` env ->
``~/.cache/caption_with_intention/models/``.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import urllib.request
from pathlib import Path

from engine.diarization.models import SpeakerSegment

logger = logging.getLogger("caption_with_intention")

AUDIO_SAMPLE_RATE = 16000
DEFAULT_MODEL_FILENAME = "nemotron-3-diarization-q8_0.gguf"
DEFAULT_MODEL_URL = (
    "https://huggingface.co/audio-cpp/Nemotron-3-Diarization-GGUF"
    f"/resolve/main/{DEFAULT_MODEL_FILENAME}"
)
DEFAULT_MODEL_DIR = Path.home() / ".cache" / "caption_with_intention" / "models"
DEFAULT_ENV_CLI = "CWI_AUDIOCPP_CLI"
DEFAULT_ENV_MODEL = "CWI_NEMOTRON_MODEL"


def repo_root() -> Path:
    """Project root (parent of engine/)."""
    return Path(__file__).resolve().parents[2]


def default_cli_candidates() -> list[Path]:
    """Plausible on-disk locations of a dev-built audiocpp_cli."""
    root = repo_root()
    return [
        root / "tools" / "nemotron-bench" / "audio.cpp" / "build" / "bin" / "audiocpp_cli",
        Path.home() / ".local" / "bin" / "audiocpp_cli",
    ]


def resolve_cli(cli_path: str | None = None) -> Path | None:
    """Locate the audiocpp_cli binary, or None when unavailable.

    Order: explicit kwarg -> CWI_AUDIOCPP_CLI env -> PATH -> dev build.
    """
    if cli_path:
        p = Path(cli_path)
        return p if p.is_file() else None
    env = os.environ.get(DEFAULT_ENV_CLI)
    if env and Path(env).is_file():
        return Path(env)
    found = shutil.which("audiocpp_cli")
    if found:
        return Path(found)
    for cand in default_cli_candidates():
        if cand.is_file():
            return cand
    return None


def default_model_path(model_path: str | None = None) -> Path:
    """Model file to use, honouring kwarg/env overrides."""
    if model_path:
        return Path(model_path)
    env = os.environ.get(DEFAULT_ENV_MODEL)
    if env:
        return Path(env)
    return DEFAULT_MODEL_DIR / DEFAULT_MODEL_FILENAME


def ensure_model(
    model_path: str | None = None,
    auto_download: bool = True,
) -> Path | None:
    """Return the model file path, downloading it once when missing.

    Args:
        model_path: Explicit model file (kwarg/env override).
        auto_download: Download from Hugging Face when the file is
            missing.  When False, a missing file yields None.

    Returns:
        Existing model path, or None when unavailable.
    """
    p = default_model_path(model_path)
    if p.is_file() and p.stat().st_size > 0:
        return p
    if not auto_download:
        return None
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(p.suffix + ".part")
        logger.info("Downloading Nemotron model to %s ...", p)
        with urllib.request.urlopen(DEFAULT_MODEL_URL, timeout=120) as resp, \
                open(tmp, "wb") as f:
            shutil.copyfileobj(resp, f, length=1024 * 1024)
        tmp.replace(p)
        logger.info("Nemotron model ready: %s", p)
        return p
    except Exception as e:  # noqa: BLE001 - any failure means "model unavailable"
        logger.warning("Nemotron model download failed: %s", e)
        return None


def parse_turns_file(path: str | Path) -> list[SpeakerSegment]:
    """Convert an audio.cpp ``--turns-out`` JSON file to segments.

    Turn objects carry ``start_sample``/``end_sample`` in audio samples
    at 16 kHz, an anonymous arrival-ordered ``speaker_id`` and a real
    per-turn ``confidence``.  Malformed rows are skipped, not fatal.
    """
    with open(path) as f:
        data = json.load(f)
    if isinstance(data, dict):
        data = data.get("speaker_turns") or data.get("turns") or []
    segments: list[SpeakerSegment] = []
    for row in data:
        if not isinstance(row, dict):
            continue
        try:
            start = float(row["start_sample"]) / AUDIO_SAMPLE_RATE
            end = float(row["end_sample"]) / AUDIO_SAMPLE_RATE
        except (KeyError, TypeError, ValueError):
            continue
        if end <= start:
            continue
        speaker_id = str(row.get("speaker_id") or row.get("speaker") or "speaker_0")
        confidence = row.get("confidence", 0.0)
        try:
            confidence = max(0.0, min(1.0, float(confidence)))
        except (TypeError, ValueError):
            confidence = 0.0
        segments.append(
            SpeakerSegment(
                speaker_id=speaker_id,
                start=start,
                end=end,
                confidence=confidence,
                source="nemotron",
            )
        )
    return segments


def run_diarization(
    cli: Path,
    model: Path,
    audio_wav: str | Path,
    out_json: str | Path,
    threads: int = 4,
    speaker_threshold: float | None = None,
    timeout: int = 600,
) -> list[SpeakerSegment]:
    """Run offline Nemotron diarization via audiocpp_cli.

    Args:
        cli: Path to the audiocpp_cli binary.
        model: Path to the GGUF weights.
        audio_wav: 16 kHz mono WAV.
        out_json: Where the CLI writes the decoded speaker turns.
        threads: CPU worker threads.
        speaker_threshold: Optional CLI speaker-activity threshold
            (0.0-1.0, default 0.5 inside the CLI).
        timeout: Wall-clock limit in seconds.

    Returns:
        Parsed speaker segments (possibly empty when no speech found).

    Raises:
        RuntimeError: When the CLI exits non-zero or times out.
    """
    cmd = [
        str(cli),
        "--task", "diar",
        "--family", "nemotron_3_diar",
        "--model", str(model),
        "--backend", "cpu",
        "--threads", str(max(1, int(threads))),
        "--audio", str(audio_wav),
        "--turns-out", str(out_json),
    ]
    if speaker_threshold is not None:
        cmd += ["--request-option", f"speaker_threshold={speaker_threshold}"]

    logger.info(
        "Running Nemotron diarization: %s (%s, %d threads)",
        audio_wav, model.name, threads,
    )
    try:
        result = subprocess.run(  # noqa: PLW1510 - returncode checked below
            cmd, capture_output=True, text=True, timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError(
            f"Nemotron diarization timed out after {timeout}s"
        ) from None
    if result.returncode != 0:
        stderr = (result.stderr or "").strip()[-500:]
        raise RuntimeError(f"audiocpp_cli failed (rc={result.returncode}): {stderr}")
    if not Path(out_json).is_file():
        raise RuntimeError(f"Nemotron diarization produced no output file: {out_json}")
    return parse_turns_file(out_json)
