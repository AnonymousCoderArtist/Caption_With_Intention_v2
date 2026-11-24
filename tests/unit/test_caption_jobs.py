"""Caption job input checks. No speech model or video is needed."""

import io

import pytest

from engine.editor.caption_jobs import MODELS, CaptionJobs


def test_rejects_unknown_model():
    with pytest.raises(ValueError, match="Choose one of"):
        CaptionJobs().create({"model": "large-v3"})


def test_missing_ffmpeg_message(monkeypatch):
    monkeypatch.setattr("engine.editor.caption_jobs.shutil.which", lambda name: None)
    with pytest.raises(ValueError, match="FFmpeg was not found"):
        CaptionJobs().create({"model": next(iter(MODELS))})


def test_upload_size_limit_and_single_job(monkeypatch):
    pytest.importorskip("faster_whisper")
    jobs = CaptionJobs()
    status = jobs.create({"model": "base.en"})
    with pytest.raises(ValueError, match="Another caption job"):
        jobs.create({"model": "base.en"})
    with pytest.raises(ValueError, match="smaller than 2 GB"):
        jobs.upload(status["id"], io.BytesIO(b""), 0)
    assert jobs.status(status["id"])["state"] == "failed"
    jobs.close()


def test_cancel_marks_job_cancelled():
    pytest.importorskip("faster_whisper")
    jobs = CaptionJobs()
    job = jobs.create({"model": "base.en"})
    assert jobs.cancel(job["id"])["state"] == "cancelled"
    jobs.close()
