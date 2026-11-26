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


def test_build_project_from_browser_transcript():
    from engine.editor.caption_jobs import build_project

    project = build_project(
        {
            "transcript": [
                {"text": "Hello there", "start": 0.5, "end": 2.0, "confidence": 0.9},
                {"text": "Second line", "start": 2.5, "end": 4.0},
            ],
            "width": 1280,
            "height": 720,
            "fps": 30,
        }
    )
    assert project["video"]["width"] == 1280
    assert project["video"]["height"] == 720
    assert len(project["events"]) == 2
    first = project["events"][0]
    assert first["text"] == "Hello there"
    assert first["source_model"] == "web-speech-api"
    assert first["confidence"] == 0.9
    # No word timings from the browser: words are spread evenly inside the entry.
    assert [w["text"] for w in first["words"]] == ["Hello", "there"]


def test_build_project_rejects_bad_input():
    from engine.editor.caption_jobs import build_project

    with pytest.raises(ValueError, match="did not send a transcript"):
        build_project({})
    with pytest.raises(ValueError, match="No speech was found"):
        build_project({"transcript": [{"text": "  ", "start": 0, "end": 1}]})
    with pytest.raises(ValueError, match="invalid timings"):
        build_project({"transcript": [{"text": "hi", "start": 3, "end": 2}]})
    with pytest.raises(ValueError, match="invalid timings"):
        build_project({"transcript": [{"text": "hi", "start": -1, "end": 2}]})
    with pytest.raises(ValueError, match="too long"):
        build_project({"transcript": [{"text": "x" * 3000, "start": 0, "end": 1}]})


def test_build_project_bounds_video_info():
    from engine.editor.caption_jobs import build_project

    project = build_project(
        {
            "transcript": [{"text": "hi", "start": 0, "end": 1}],
            "width": "not a number",
            "height": 999999,
            "fps": 0,
        }
    )
    assert project["video"]["width"] == 1920
    assert project["video"]["height"] == 16384
    assert project["video"]["fps"] == 1
