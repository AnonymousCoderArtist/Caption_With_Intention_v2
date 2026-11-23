"""Bounded local render jobs. Source bytes and output stay on this machine."""

from __future__ import annotations

import math
import shutil
import subprocess
import tempfile
import threading
import time
import uuid
from pathlib import Path

from engine.core.ffmpeg import get_ffprobe_metadata
from engine.editor.editor import Editor
from engine.renderer import CwiRenderer
from schemas.project import Project

MAX_SOURCE_BYTES = 2 * 1024**3


class RenderJobs:
    def __init__(self, font: Path):
        self.font = font
        self.jobs: dict[str, dict] = {}
        self.lock = threading.Lock()
        self.closed = False

    def close(self):
        self.closed = True
        for job in list(self.jobs.values()):
            if job.get("expiry_timer"):
                job["expiry_timer"].cancel()
            job["state"] = "cancelled"
            process = job.get("process")
            if process is not None and process.poll() is None:
                process.kill()
                process.wait(timeout=5)
            shutil.rmtree(job["folder"], ignore_errors=True)
        self.jobs.clear()

    def create(self, data: dict, request_key: str | None = None) -> dict:
        project = Project.model_validate(data)
        if (project.video.width <= 0 or project.video.height <= 0
                or not math.isfinite(project.video.fps) or project.video.fps <= 0
                or not math.isfinite(project.video.duration) or project.video.duration < 0):
            raise ValueError("Video dimensions, frame rate and duration must be valid.")
        for event in project.events:
            Editor._validate_event_timing(event)
        with self.lock:
            if self.closed:
                raise ValueError("The local renderer is shutting down.")
            self._prune()
            if request_key:
                existing = next((j for j in self.jobs.values() if j.get("request_key") == request_key), None)
                if existing is not None:
                    return self.status(existing["id"])
            if any(
                j["state"] in {"uploading", "transferring", "rendering"}
                or j.get("worker_active")
                for j in self.jobs.values()
            ):
                raise ValueError("Another local render is active. Finish it first.")
            job_id = uuid.uuid4().hex
            folder = Path(tempfile.mkdtemp(prefix="cwi-editor-render-"))
            self.jobs[job_id] = {
                "id": job_id,
                "state": "uploading",
                "progress": 0,
                "created": time.time(),
                "folder": folder,
                "project": project,
                "request_key": request_key,
            }
            expiry = threading.Timer(3600, self._expire, args=(job_id,))
            expiry.daemon = True
            expiry.start()
            self.jobs[job_id]["expiry_timer"] = expiry
            return self.status(job_id)

    def _expire(self, job_id: str):
        with self.lock:
            job = self.jobs.get(job_id)
            if (
                job is not None
                and job["state"] not in {"rendering", "transferring"}
                and not job.get("worker_active")
            ):
                shutil.rmtree(job["folder"], ignore_errors=True)
                del self.jobs[job_id]

    def _prune(self):
        for key, job in list(self.jobs.items()):
            if (
                time.time() - job.get("finished", job["created"])
                > (600 if job["state"] == "uploading" else 3600)
                and job["state"] not in {"rendering", "transferring"}
                and not job.get("worker_active")
            ):
                shutil.rmtree(job["folder"], ignore_errors=True)
                del self.jobs[key]

    def cancel(self, job_id: str) -> dict:
        with self.lock:
            job = self.jobs[job_id]
            if job["state"] in {"complete", "failed", "cancelled"}:
                return self.status(job_id)
            job["state"] = "cancelled"
            process = job.get("process")
            if process is not None and process.poll() is None:
                try:
                    process.kill()
                except ProcessLookupError:
                    # The encoder can exit between poll and kill.
                    pass
            return self.status(job_id)

    def status(self, job_id: str) -> dict:
        job = self.jobs[job_id]
        return {k: job[k] for k in ("id", "state", "progress", "error") if k in job}

    def upload(self, job_id: str, stream, length: int) -> dict:
        with self.lock:
            job = self.jobs[job_id]
            if job["state"] != "uploading":
                raise ValueError("This render is no longer accepting a video.")
            if not 0 < length <= MAX_SOURCE_BYTES:
                job.update(
                    state="failed", error="Choose a source video smaller than 2 GB."
                )
                raise ValueError(job["error"])
            job["state"] = "transferring"
            job["worker_active"] = True
        source = job["folder"] / "source.video"
        try:
            remaining = length
            with source.open("wb") as output:
                while remaining:
                    if job["state"] == "cancelled":
                        break
                    chunk = stream.read(min(1024 * 1024, remaining))
                    if not chunk:
                        raise ValueError("Source upload was interrupted.")
                    output.write(chunk)
                    remaining -= len(chunk)
            with self.lock:
                if job["state"] == "cancelled":
                    source.unlink(missing_ok=True)
                    job.pop("worker_active", None)
                    return self.status(job_id)
                job["state"] = "rendering"
                job["worker_active"] = True
            threading.Thread(target=self._render, args=(job,), daemon=True).start()
            return self.status(job_id)
        except Exception:
            job.pop("worker_active", None)
            source.unlink(missing_ok=True)
            if job["state"] == "cancelled":
                return self.status(job_id)
            job["state"] = "failed"
            job["error"] = "The source video could not be copied to the local renderer."
            raise

    def _render(self, job: dict):
        try:
            source = job["folder"] / "source.video"
            try:
                metadata = get_ffprobe_metadata(source)
            except RuntimeError as exc:
                raise ValueError(
                    "This video could not be read. Choose a decodable local video file."
                ) from exc
            if not any(
                s.get("codec_type") == "video" for s in metadata.get("streams", [])
            ):
                raise ValueError("The selected file has no video stream.")
            duration = float(metadata.get("format", {}).get("duration", 0))
            renderer = CwiRenderer(
                job["project"], font_path=self.font, audio_codec="aac"
            )
            ass = renderer._generate_ass(source, output_dir=job["folder"])
            if job["state"] == "cancelled":
                return
            output = job["folder"] / "captioned.mp4"
            command = renderer._build_ffmpeg_command(source, ass, output)
            command[1:1] = ["-nostdin", "-progress", "pipe:1", "-nostats"]
            with (job["folder"] / "encoding.log").open("w") as errors:
                process = subprocess.Popen(
                    command, stdout=subprocess.PIPE, stderr=errors, text=True
                )
                job["process"] = process
                if job["state"] == "cancelled":
                    process.kill()
                timer = threading.Timer(1800, process.kill)
                timer.start()
                try:
                    for line in process.stdout:
                        if line.startswith("out_time_us=") and duration > 0:
                            job["progress"] = min(
                                99,
                                max(
                                    0,
                                    int(
                                        float(line.split("=", 1)[1])
                                        / (duration * 10000)
                                    ),
                                ),
                            )
                    code = process.wait()
                finally:
                    timer.cancel()
                if code != 0 or not output.exists():
                    raise RuntimeError(
                        "Encoding failed. Check the source format and available disk space."
                    )
            with self.lock:
                if job["state"] != "cancelled":
                    job.update(state="complete", progress=100)
        except Exception as exc:  # noqa: BLE001 - background worker must publish failures
            if job["state"] != "cancelled":
                job.update(state="failed", error=str(exc)[:300])
        finally:
            job.pop("process", None)
            job.pop("worker_active", None)
            if job.get("expiry_timer"):
                job["expiry_timer"].cancel()
            job["finished"] = time.time()
            if not self.closed:
                expiry = threading.Timer(3600, self._expire, args=(job["id"],))
                expiry.daemon = True
                job["expiry_timer"] = expiry
                expiry.start()
            (job["folder"] / "source.video").unlink(missing_ok=True)
            if job["state"] != "complete":
                (job["folder"] / "captioned.mp4").unlink(missing_ok=True)

    def download(self, job_id: str) -> Path:
        job = self.jobs[job_id]
        if job["state"] != "complete":
            raise ValueError("The video is not ready yet.")
        return job["folder"] / "captioned.mp4"
