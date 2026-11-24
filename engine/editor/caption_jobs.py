"""Local automatic-caption jobs for the editor. Video bytes stay on this machine.

One job at a time: upload the source, run speech recognition in 60 second
windows (real progress, cancel between windows), then build an editable
project. Speaker separation is not promised: unknown speakers stay unassigned.
"""

from __future__ import annotations

import shutil
import tempfile
import threading
import time
import uuid
from pathlib import Path

MAX_SOURCE_BYTES = 2 * 1024**3
# English-only models: smaller and more accurate than the multilingual ones of the same size.
MODELS = {
    "base.en": "Faster, less accurate (about 150 MB download)",
    "small.en": "Better words (about 500 MB download)",
}
ACTIVE = {"uploading", "transferring", "analyzing"}


class CaptionJobs:
    def __init__(self):
        self.jobs: dict[str, dict] = {}
        self.lock = threading.Lock()
        self.closed = False

    def close(self):
        self.closed = True
        for job in list(self.jobs.values()):
            job["state"] = "cancelled"
            shutil.rmtree(job["folder"], ignore_errors=True)
        self.jobs.clear()

    def create(self, data: dict) -> dict:
        model = data.get("model", "base.en")
        if model not in MODELS:
            raise ValueError("Choose one of: " + ", ".join(MODELS))
        if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
            raise ValueError(
                "FFmpeg was not found. Install FFmpeg, add it to PATH, then restart the editor."
            )
        try:
            import faster_whisper  # noqa: F401
        except ImportError as exc:
            raise ValueError(
                "The speech add-on is not installed. In the project folder run: "
                "uv sync --extra dev --extra asr   then restart the editor."
            ) from exc
        with self.lock:
            if self.closed:
                raise ValueError("The local editor is shutting down.")
            self._prune()
            if any(j["state"] in ACTIVE for j in self.jobs.values()):
                raise ValueError("Another caption job is running. Wait for it or cancel it.")
            job_id = uuid.uuid4().hex
            self.jobs[job_id] = {
                "id": job_id,
                "state": "uploading",
                "progress": 0,
                "stage": "Waiting for the video",
                "model": model,
                "created": time.time(),
                "folder": Path(tempfile.mkdtemp(prefix="cwi-editor-captions-")),
            }
            return self.status(job_id)

    def _prune(self):
        for key, job in list(self.jobs.items()):
            if job["state"] not in ACTIVE and time.time() - job.get("finished", job["created"]) > 3600:
                shutil.rmtree(job["folder"], ignore_errors=True)
                del self.jobs[key]

    def status(self, job_id: str) -> dict:
        job = self.jobs[job_id]
        return {k: job[k] for k in ("id", "state", "progress", "stage", "error", "model") if k in job}

    def cancel(self, job_id: str) -> dict:
        with self.lock:
            job = self.jobs[job_id]
            if job["state"] in ACTIVE:
                job["state"] = "cancelled"
                job["stage"] = "Cancelled"
                job["finished"] = time.time()
            return self.status(job_id)

    def result(self, job_id: str) -> dict:
        job = self.jobs[job_id]
        if job["state"] != "complete":
            raise ValueError("Captions are not ready.")
        return job["project"]

    def upload(self, job_id: str, stream, length: int) -> dict:
        with self.lock:
            job = self.jobs[job_id]
            if job["state"] != "uploading":
                raise ValueError("This job is no longer accepting a video.")
            if not 0 < length <= MAX_SOURCE_BYTES:
                job.update(state="failed", error="Choose a source video smaller than 2 GB.", finished=time.time())
                raise ValueError(job["error"])
            job.update(state="transferring", stage="Copying the video to the local engine")
        source = job["folder"] / "source.video"
        try:
            remaining = length
            with source.open("wb") as output:
                while remaining and job["state"] == "transferring":
                    chunk = stream.read(min(1024 * 1024, remaining))
                    if not chunk:
                        raise ValueError("The video upload was interrupted.")
                    output.write(chunk)
                    remaining -= len(chunk)
            with self.lock:
                if job["state"] != "transferring":
                    return self.status(job_id)
                job.update(state="analyzing", stage="Starting", progress=1)
            threading.Thread(target=self._run, args=(job,), daemon=True).start()
            return self.status(job_id)
        except Exception:
            if job["state"] != "cancelled":
                job.update(state="failed", error="The video could not be copied to the local engine.", finished=time.time())
            raise

    def _fail(self, job: dict, message: str):
        if job["state"] != "cancelled":
            job.update(state="failed", error=message, stage="Failed", finished=time.time())

    def _run(self, job: dict):
        try:
            import json

            from engine.editor.editor import Editor
            from engine.media.probe import probe_video
            from engine.speech.long_video import LongVideoRunner
            from engine.speech.pipeline import SpeechPipeline

            source = job["folder"] / "source.video"
            try:
                info = probe_video(str(source))
            except Exception as exc:
                raise ValueError("This video could not be read. Choose a decodable video file.") from exc
            if not info.get("width") or not info.get("height"):
                raise ValueError("The selected file has no video stream.")
            job["stage"] = "Loading the speech model (the first run downloads it, needs internet once)"
            pipeline = SpeechPipeline(asr_model=job["model"], cpu_threads=None, max_workers=1)
            runner = LongVideoRunner(pipeline, chunk_duration=60, overlap=2)

            def progress(event: dict):
                total = max(1, event.get("total", 1))
                chunk = event.get("chunk", 0)
                if event.get("state") in ("running", "cached"):
                    job["progress"] = max(job["progress"], min(95, 2 + int(93 * chunk / total)))
                    job["stage"] = f"Transcribing part {chunk + 1} of {total}"
                    eta = event.get("eta_s")
                    if eta:
                        job["stage"] += f" (about {max(1, round(eta / 60))} min left)"

            payload_path = runner.run(
                source, job["folder"] / "work", progress=progress, cancelled=lambda: job["state"] == "cancelled"
            )
            if job["state"] == "cancelled":
                return
            job.update(stage="Building editable captions", progress=97)
            payload = json.loads(Path(payload_path).read_text())
            transcript = payload.get("transcript", [])
            if not transcript:
                raise ValueError("No speech was found in this video.")
            project = Editor().build_from_transcript(
                transcript,
                video_width=info["width"],
                video_height=info["height"],
                fps=info["fps"],
                speakers=payload.get("speakers", []),
            )
            job["project"] = json.loads(project.model_dump_json())
            if job["state"] != "cancelled":
                job.update(state="complete", progress=100, stage="Done", finished=time.time())
        except InterruptedError:
            pass
        except ValueError as exc:
            self._fail(job, str(exc)[:300])
        except ImportError:
            self._fail(job, "The speech add-on is not installed. Run: uv sync --extra dev --extra asr   then restart the editor.")
        except Exception as exc:  # noqa: BLE001
            self._fail(job, "Captioning stopped. If this is the first run, check your internet connection for the one-time model download. " + type(exc).__name__ + ": " + str(exc)[:160])
        finally:
            shutil.rmtree(job["folder"] / "source.video", ignore_errors=True)
