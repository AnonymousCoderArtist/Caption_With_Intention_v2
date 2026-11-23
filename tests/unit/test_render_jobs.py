import io
from pathlib import Path
from unittest.mock import patch

import pytest

from engine.editor.render_jobs import RenderJobs
from schemas.project import Project


@pytest.fixture
def jobs():
    manager = RenderJobs(Path("font.ttf"))
    yield manager
    manager.close()


def test_create_snapshots_project_and_limits_concurrent_jobs(jobs):
    data = Project().model_dump(mode="json")
    job = jobs.create(data)
    assert job["state"] == "uploading"
    with pytest.raises(ValueError):
        jobs.create(data)
    jobs.cancel(job["id"])
    assert jobs.create(data)["state"] == "uploading"


def test_upload_rejects_empty_and_interrupted_source(jobs):
    job = jobs.create(Project().model_dump())
    with pytest.raises(ValueError):
        jobs.upload(job["id"], io.BytesIO(), 0)
    assert jobs.status(job["id"])["state"] == "failed"
    second = jobs.create(Project().model_dump())
    with pytest.raises(ValueError):
        jobs.upload(second["id"], io.BytesIO(b"ab"), 20)
    assert jobs.status(second["id"])["state"] == "failed"
    assert not (jobs.jobs[second["id"]]["folder"] / "source.video").exists()


def test_upload_starts_background_render(jobs):
    job = jobs.create(Project().model_dump())
    with patch("engine.editor.render_jobs.threading.Thread") as worker:
        result = jobs.upload(job["id"], io.BytesIO(b"video"), 5)
        worker.return_value.start.assert_called_once()
    assert result["state"] == "rendering"
    with pytest.raises(ValueError):
        jobs.download(job["id"])


def test_expiry_removes_local_output_and_job(jobs):
    job = jobs.create(Project().model_dump())
    folder = jobs.jobs[job["id"]]["folder"]
    jobs.cancel(job["id"])
    jobs._expire(job["id"])
    assert not folder.exists()
    with pytest.raises(KeyError):
        jobs.status(job["id"])


def test_cancelled_worker_still_blocks_new_encoding_until_it_stops(jobs):
    job = jobs.create(Project().model_dump())
    jobs.jobs[job["id"]].update(state="rendering", worker_active=True)
    jobs.cancel(job["id"])
    with pytest.raises(ValueError):
        jobs.create(Project().model_dump())
    jobs.jobs[job["id"]].pop("worker_active")
    assert jobs.create(Project().model_dump())["state"] == "uploading"


def test_cancel_during_transfer_cleans_source_and_preserves_cancelled(jobs):
    job = jobs.create(Project().model_dump())

    class CancelStream:
        def read(self, size):
            jobs.cancel(job["id"])
            return b""

    result = jobs.upload(job["id"], CancelStream(), 10)
    assert result["state"] == "cancelled"
    assert not jobs.jobs[job["id"]].get("worker_active")
    assert not (jobs.jobs[job["id"]]["folder"] / "source.video").exists()
    assert jobs.create(Project().model_dump())["state"] == "uploading"


def test_retention_counts_from_finished_encode_not_creation(jobs):
    import time

    job = jobs.create(Project().model_dump())
    internal = jobs.jobs[job["id"]]
    internal.update(state="complete", created=time.time() - 4000, finished=time.time())
    jobs._prune()
    assert jobs.status(job["id"])["state"] == "complete"
    internal["finished"] = time.time() - 4000
    jobs._prune()
    with pytest.raises(KeyError):
        jobs.status(job["id"])


def test_close_cancels_expiry_and_rejects_new_jobs(jobs):
    job = jobs.create(Project().model_dump())
    folder = jobs.jobs[job["id"]]["folder"]
    jobs.close()
    assert not folder.exists()
    with pytest.raises(ValueError):
        jobs.create(Project().model_dump())


def test_cancel_after_encoder_exit_does_not_kill_completed_process(jobs):
    from unittest.mock import Mock

    job = jobs.create(Project().model_dump())
    process = Mock()
    process.poll.return_value = 0
    jobs.jobs[job["id"]].update(state="rendering", process=process)
    assert jobs.cancel(job["id"])["state"] == "cancelled"
    process.kill.assert_not_called()


def test_cancel_tolerates_process_exiting_between_poll_and_kill(jobs):
    from unittest.mock import Mock

    job = jobs.create(Project().model_dump())
    process = Mock()
    process.poll.side_effect = [None, 0]
    process.kill.side_effect = ProcessLookupError
    jobs.jobs[job["id"]].update(state="rendering", process=process)
    assert jobs.cancel(job["id"])["state"] == "cancelled"


def test_stalled_transfer_timeout_releases_worker_and_removes_source(jobs):
    job = jobs.create(Project().model_dump())

    class StalledStream:
        def read(self, size):
            raise TimeoutError("idle source")

    with pytest.raises(TimeoutError):
        jobs.upload(job["id"], StalledStream(), 10)
    assert jobs.status(job["id"])["state"] == "failed"
    assert not jobs.jobs[job["id"]].get("worker_active")
    assert not (jobs.jobs[job["id"]]["folder"] / "source.video").exists()
    assert jobs.create(Project().model_dump())["state"] == "uploading"


@pytest.mark.parametrize("mutation", ["video", "event", "word", "syllable"])
def test_bad_project_is_rejected_before_reserving_worker(jobs, mutation):
    from schemas.project import CaptionEvent, Word

    project = Project(events=[CaptionEvent(id="e", start=0, end=2, text="hello", words=[Word(text="hello", start=0, end=1)])])
    data = project.model_dump()
    if mutation == "video":
        data["video"]["fps"] = float("nan")
    elif mutation == "event":
        data["events"][0]["end"] = -1
    elif mutation == "word":
        data["events"][0]["words"][0]["end"] = 5
    else:
        data["events"][0]["words"][0]["syllables"] = [{"text": "hello", "start": 0, "end": 1.5}]
    with pytest.raises(ValueError):
        jobs.create(data)
    assert not jobs.jobs
    assert jobs.create(Project().model_dump())["state"] == "uploading"


def test_retry_create_returns_same_job_and_original_snapshot(jobs):
    data = Project(project_name="original").model_dump()
    first = jobs.create(data, request_key="retry-key")
    data["project_name"] = "changed"
    assert jobs.create(data, request_key="retry-key")["id"] == first["id"]
    assert len(jobs.jobs) == 1
    assert jobs.jobs[first["id"]]["project"].project_name == "original"
    with pytest.raises(ValueError):
        jobs.create(data, request_key="different-key")
