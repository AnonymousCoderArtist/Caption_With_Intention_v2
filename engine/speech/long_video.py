"""Sequential resumable speech analysis with bounded audio windows.

Checkpoint JSON contains caption/turn metadata, never raw audio. Global turn
metadata grows with source duration; this is not constant-memory in transcript
length. Model objects are reused across windows. Unknown cross-chunk speaker
links remain separate, reviewable identities, never guessed by label number.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

from engine.asr.longform import chunk_windows
from engine.diarization.models import SpeakerSegment
from engine.diarization.reconcile import reconcile_speakers
from engine.media.probe import probe_video

RUNNER_VERSION = 1


def atomic_json(path: Path, data) -> None:
    """Publish complete JSON only; an interruption cannot truncate old state."""
    fd, temporary = tempfile.mkstemp(prefix=".pending-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as output:
            json.dump(data, output, ensure_ascii=False, allow_nan=False)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def source_signature(source: Path) -> dict:
    """Full streaming SHA256 validates resume, even after same-size edits."""
    digest = hashlib.sha256()
    with source.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return {
        "path": str(source.resolve()),
        "size": source.stat().st_size,
        "sha256": digest.hexdigest(),
    }


class LongVideoRunner:
    """One writer per work directory; failures leave completed chunks reusable."""

    def __init__(
        self,
        pipeline,
        *,
        chunk_duration: float = 60,
        overlap: float = 2,
        detect_sounds: bool = False,
        minimum_free_bytes: int = 256 * 1024 * 1024,
    ):
        # Configuration errors are caught before touching any source or directory.
        list(chunk_windows(1, chunk_duration, overlap))
        if chunk_duration > 600:
            raise ValueError("Analysis windows must not exceed600seconds")
        if getattr(pipeline, "max_workers", 1) != 1:
            raise ValueError(
                "Long-video mode requires pipeline max_workers=1 to avoid stage oversubscription"
            )
        if minimum_free_bytes < 0:
            raise ValueError("Minimum free disk space must be non-negative")
        self.pipeline = pipeline
        self.chunk_duration = chunk_duration
        self.overlap = overlap
        self.detect_sounds = detect_sounds
        self.minimum_free_bytes = minimum_free_bytes

    def _configuration(self):
        names = [
            "asr_model",
            "asr_backend",
            "asr_device",
            "asr_compute_type",
            "diarize_backend",
            "diarize_confidence",
            "align_mode",
            "language",
            "correct_transcript",
            "min_confidence",
            "cpu_threads",
            "max_workers",
        ]
        return {
            "version": RUNNER_VERSION,
            "chunk_duration": self.chunk_duration,
            "overlap": self.overlap,
            "detect_sounds": self.detect_sounds,
            "pipeline": {name: getattr(self.pipeline, name, None) for name in names},
        }

    def run(
        self,
        source_path: str | Path,
        work_path: str | Path,
        *,
        progress=None,
        cancelled=None,
    ) -> Path:
        source = Path(source_path).resolve()
        if not source.is_file():
            raise FileNotFoundError(source)
        work = Path(work_path).resolve()
        if work == source or source.parent == work:
            raise ValueError("Use a separate work directory, not the source folder")
        work.mkdir(parents=True, exist_ok=True)
        lock = work / "run.lock"
        try:
            fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError as exc:
            raise RuntimeError(
                "Work directory is locked. Confirm no runner is active before removing run.lock after a hard crash."
            ) from exc
        os.close(fd)
        try:
            return self._run(source, work, progress, cancelled)
        finally:
            lock.unlink(missing_ok=True)

    def _run(self, source, work, progress, cancelled):
        signature = source_signature(source)
        info = probe_video(source)
        duration = float(info.get("duration", 0))
        windows = list(chunk_windows(duration, self.chunk_duration, self.overlap))
        manifest_path = work / "manifest.json"
        identity = {"source": signature, "configuration": self._configuration()}
        if manifest_path.exists():
            manifest = json.loads(manifest_path.read_text())
            if manifest.get("identity") != identity:
                raise ValueError(
                    "Source or analysis settings changed. Choose a new work directory."
                )
        else:
            manifest = {
                "identity": identity,
                "duration": duration,
                "chunks": {},
                "state": "pending",
            }
        elapsed = []
        try:
            for index, (start, end) in enumerate(windows):
                if cancelled and cancelled():
                    manifest["state"] = "cancelled"
                    atomic_json(manifest_path, manifest)
                    raise InterruptedError(
                        "Analysis cancelled between chunks; completed chunks can resume"
                    )
                target = work / f"chunk-{index:06d}.json"
                record = manifest["chunks"].get(str(index), {})
                reusable = False
                if record.get("state") == "completed" and target.is_file():
                    reusable = hashlib.sha256(
                        target.read_bytes()
                    ).hexdigest() == record.get("sha256")
                if reusable:
                    if progress:
                        progress(
                            {"state": "cached", "chunk": index, "total": len(windows)}
                        )
                    continue
                required = max(
                    self.minimum_free_bytes, int((end - start) * 16000 * 4 * 3)
                )
                if shutil.disk_usage(work).free < required:
                    raise OSError(
                        "Not enough free disk space for the next audio window"
                    )
                manifest["state"] = "running"
                manifest["chunks"][str(index)] = {"state": "running"}
                atomic_json(manifest_path, manifest)
                if progress:
                    progress(
                        {
                            "state": "running",
                            "chunk": index,
                            "total": len(windows),
                            "eta_s": sum(elapsed)
                            / len(elapsed)
                            * (len(windows) - index)
                            if elapsed
                            else None,
                        }
                    )
                clock = time.monotonic()
                with tempfile.TemporaryDirectory(
                    prefix="audio-", dir=work
                ) as temporary:
                    wav = Path(temporary) / "source.wav"
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
                            str(wav),
                        ],
                        capture_output=True,
                        timeout=120,
                        check=False,
                    )
                    if proc.returncode:
                        raise RuntimeError(f"Audio extraction failed for chunk {index}")
                    result = self.pipeline.run_full(
                        wav, detect_sounds=self.detect_sounds
                    )
                    data = {
                        "start": start,
                        "end": end,
                        "payload": self.pipeline.build_editor_payload(result),
                        "diarization_segments": result.get("diarization_segments", []),
                    }
                    atomic_json(target, data)
                    del result, data
                digest = hashlib.sha256(target.read_bytes()).hexdigest()
                elapsed.append(time.monotonic() - clock)
                manifest["chunks"][str(index)] = {
                    "state": "completed",
                    "sha256": digest,
                    "elapsed_s": elapsed[-1],
                }
                atomic_json(manifest_path, manifest)
                if progress:
                    progress(
                        {"state": "completed", "chunk": index, "total": len(windows)}
                    )
            output = self._assemble(work, windows, duration)
            manifest.pop("error", None)
            manifest["state"] = "completed"
            manifest["output"] = output.name
            atomic_json(manifest_path, manifest)
            return output
        except BaseException as exc:
            if manifest.get("state") != "cancelled":
                manifest["state"] = "failed"
            manifest["error"] = type(exc).__name__
            atomic_json(manifest_path, manifest)
            raise

    def _assemble(self, work, windows, duration):
        # Only turn metadata from all windows is retained; caption payloads are
        # loaded one window at a time and streamed into the final JSON file.
        turns = []
        for index in range(len(windows)):
            data = json.loads((work / f"chunk-{index:06d}.json").read_text())
            offset = data["start"]
            turns.append(
                [
                    SpeakerSegment(
                        seg["speaker_id"],
                        max(offset, seg["start"] + offset),
                        min(duration, seg["end"] + offset),
                        seg.get("confidence", 0),
                        seg.get("source", ""),
                    )
                    for seg in data["diarization_segments"]
                    if seg.get("speaker_id")
                    and seg["end"] > seg["start"]
                    and seg.get("source")
                    not in ("ffmpeg_vad", "hardcoded_fallback", "diarize_fallback")
                ]
            )
        reconciled = reconcile_speakers(turns)
        atomic_json(work / "speaker-review.json", reconciled.to_dict())
        output = work / "payload.json"
        fd, temp = tempfile.mkstemp(prefix=".payload-", dir=work)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                stream.write('{"transcript":[')
                first = True
                for index, (start, end) in enumerate(windows):
                    data = json.loads((work / f"chunk-{index:06d}.json").read_text())
                    left = 0 if index == 0 else (windows[index - 1][1] + start) / 2
                    right = (
                        duration
                        if index == len(windows) - 1
                        else (end + windows[index + 1][0]) / 2
                    )
                    for entry in data["payload"]["transcript"]:
                        words = entry.get("words") or []
                        kept = []
                        for word in words:
                            midpoint = start + (word["start"] + word["end"]) / 2
                            if not left <= midpoint < right:
                                continue
                            word["start"] = max(start, word["start"] + start)
                            word["end"] = min(end, word["end"] + start)
                            for syllable in word.get("syllables") or []:
                                syllable["start"] = max(
                                    word["start"], syllable["start"] + start
                                )
                                syllable["end"] = min(
                                    word["end"], syllable["end"] + start
                                )
                            if word.get("syllables"):
                                word["syllables"] = [
                                    s
                                    for s in word["syllables"]
                                    if s["end"] > s["start"]
                                ]
                            if word.get("source_timestamp") is not None:
                                word["source_timestamp"] += start
                            if word["end"] > word["start"]:
                                kept.append(word)
                        if not kept:
                            continue
                        if len(kept) != len(words):
                            entry["text"] = " ".join(w["text"].strip() for w in kept)
                        entry["words"] = kept
                        entry["start"] = min(w["start"] for w in kept)
                        entry["end"] = max(w["end"] for w in kept)
                        if entry.get("source_timestamp") is not None:
                            entry["source_timestamp"] += start
                        local = entry.get("speaker_id")
                        if local:
                            entry["speaker_id"] = reconciled.speaker_map.get(
                                (index, local)
                            )
                            if (index, local) in reconciled.unmatched or not entry[
                                "speaker_id"
                            ]:
                                entry["speaker_review_required"] = True
                                entry.setdefault("speaker_review_reasons", []).append(
                                    "No reliable cross-chunk identity link; confirm by listening."
                                )
                        entry["notes"] = (
                            entry.get("notes", "")
                            + " Chunk boundary ownership uses word midpoint; inspect seam timing/text."
                        ).strip()
                        if not first:
                            stream.write(",")
                        json.dump(entry, stream, ensure_ascii=False, allow_nan=False)
                        first = False
                stream.write('],"speakers":')
                json.dump(
                    [
                        {"id": sid, "name": f"Speaker {i + 1}", "category": "main"}
                        for i, sid in enumerate(reconciled.global_speakers)
                    ],
                    stream,
                )
                stream.write(',"duration":' + str(duration) + "}")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temp, output)
        finally:
            Path(temp).unlink(missing_ok=True)
        return output
