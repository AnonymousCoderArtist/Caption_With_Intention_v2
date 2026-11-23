"""Resume safety tests use a diagnostic fake recognizer, not model accuracy."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from engine.speech.long_video import LongVideoRunner


class FakePipeline:
    asr_model = "fixture"

    def __init__(self, fail_at=None):
        self.calls = 0
        self.fail_at = fail_at

    def run_full(self, path, **kwargs):
        self.calls += 1
        if self.calls == self.fail_at:
            raise RuntimeError("injected model crash")
        return {
            "diarization_segments": [
                {"speaker_id": "local", "start": 0, "end": 30, "confidence": 0.8}
            ]
        }

    def build_editor_payload(self, result):
        return {
            "speakers": [{"id": "local", "name": "Test"}],
            "transcript": [
                {
                    "text": "hello there",
                    "start": 0,
                    "end": 30,
                    "speaker_id": "local",
                    "words": [
                        {"text": "hello", "start": 0, "end": 1},
                        {"text": "there", "start": 29, "end": 30},
                    ],
                }
            ],
        }


def source(tmp_path):
    path = tmp_path / "source.mp4"
    path.write_bytes(b"fixture source")
    return path


@pytest.fixture
def fake_media():
    def extract(command, **kwargs):
        Path(command[-1]).write_bytes(b"waveform")
        return SimpleNamespace(returncode=0)

    with (
        patch("engine.speech.long_video.probe_video", return_value={"duration": 58}),
        patch("engine.speech.long_video.subprocess.run", side_effect=extract),
    ):
        yield


def test_crash_resumes_completed_chunks_and_returns_global_timeline(
    tmp_path, fake_media
):
    media = source(tmp_path)
    work = tmp_path / "job"
    pipeline = FakePipeline(fail_at=2)
    runner = LongVideoRunner(
        pipeline, chunk_duration=30, overlap=2, minimum_free_bytes=0
    )
    with pytest.raises(RuntimeError):
        runner.run(media, work)
    assert json.loads((work / "manifest.json").read_text())["state"] == "failed"
    assert (work / "chunk-000000.json").exists()
    assert not (work / "run.lock").exists()
    assert not list(work.glob("audio-*"))
    output = runner.run(media, work)
    assert pipeline.calls == 3  # one cached + only the failed window retried
    data = json.loads(output.read_text())
    assert data["duration"] == 58
    assert [
        word["start"] for event in data["transcript"] for word in event["words"]
    ] == [0, 57]
    assert len(data["speakers"]) == 1  # overlap evidence, not label-number equality
    before = pipeline.calls
    runner.run(media, work)
    assert pipeline.calls == before
    manifest = json.loads((work / "manifest.json").read_text())
    assert manifest["state"] == "completed" and "error" not in manifest


def test_changed_source_and_configuration_reject_stale_resume(tmp_path, fake_media):
    media = source(tmp_path)
    work = tmp_path / "job"
    runner = LongVideoRunner(FakePipeline(), chunk_duration=30, minimum_free_bytes=0)
    runner.run(media, work)
    media.write_bytes(b"changed source")
    with pytest.raises(ValueError, match="changed"):
        runner.run(media, work)
    assert not (work / "run.lock").exists()


def test_corrupt_completed_chunk_is_recomputed(tmp_path, fake_media):
    media = source(tmp_path)
    work = tmp_path / "job"
    pipeline = FakePipeline()
    runner = LongVideoRunner(pipeline, chunk_duration=30, minimum_free_bytes=0)
    runner.run(media, work)
    assert pipeline.calls == 2
    (work / "chunk-000000.json").write_text("{}")
    runner.run(media, work)
    assert pipeline.calls == 3


def test_lock_prevents_second_writer(tmp_path, fake_media):
    media = source(tmp_path)
    work = tmp_path / "job"
    work.mkdir()
    (work / "run.lock").write_text("")
    with pytest.raises(RuntimeError, match="locked"):
        LongVideoRunner(FakePipeline()).run(media, work)
    assert (work / "run.lock").exists()


def test_disk_failure_occurs_before_model_work(tmp_path, fake_media):
    media = source(tmp_path)
    pipeline = FakePipeline()
    with (
        patch(
            "engine.speech.long_video.shutil.disk_usage",
            return_value=SimpleNamespace(free=0),
        ),
        pytest.raises(OSError),
    ):
        LongVideoRunner(pipeline).run(media, tmp_path / "job")
    assert pipeline.calls == 0


def test_cancellation_leaves_checkpoint_and_releases_lock(tmp_path, fake_media):
    media = source(tmp_path)
    pipeline = FakePipeline()
    work = tmp_path / "job"
    with pytest.raises(InterruptedError):
        LongVideoRunner(pipeline).run(media, work, cancelled=lambda: True)
    assert json.loads((work / "manifest.json").read_text())["state"] == "cancelled"
    assert not (work / "run.lock").exists()


def test_runner_rejects_parallel_stages_and_unbounded_windows():
    pipeline = FakePipeline()
    pipeline.max_workers = 2
    with pytest.raises(ValueError, match="max_workers"):
        LongVideoRunner(pipeline)
    pipeline.max_workers = 1
    with pytest.raises(ValueError, match="600"):
        LongVideoRunner(pipeline, chunk_duration=3600)


def test_settings_change_rejects_reuse(tmp_path, fake_media):
    media = source(tmp_path)
    work = tmp_path / "job"
    LongVideoRunner(FakePipeline(), chunk_duration=30, minimum_free_bytes=0).run(
        media, work
    )
    with pytest.raises(ValueError, match="changed"):
        LongVideoRunner(FakePipeline(), chunk_duration=31, minimum_free_bytes=0).run(
            media, work
        )


def test_vad_fallback_is_not_laundered_into_identity_links(tmp_path, fake_media):
    class VadPipeline(FakePipeline):
        def run_full(self, path, **kwargs):
            data = super().run_full(path, **kwargs)
            for segment in data["diarization_segments"]:
                segment["source"] = "ffmpeg_vad"
            return data

    output = LongVideoRunner(
        VadPipeline(), chunk_duration=30, minimum_free_bytes=0
    ).run(source(tmp_path), tmp_path / "job")
    data = json.loads(output.read_text())
    assert data["speakers"] == []
    assert all(
        e["speaker_id"] is None and e["speaker_review_required"]
        for e in data["transcript"]
    )
