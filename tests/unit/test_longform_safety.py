"""Long-source helpers must terminate, retain source timing and fail honestly."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from engine.asr.longform import (
    chunk_windows,
    extract_audio_chunks,
    offset_result,
    transcribe_chunks,
)
from engine.asr.models import Segment, TranscriptionResult, Word
from engine.asr.parakeet import ParakeetTranscriber
from engine.asr.transcriber import Transcriber


@pytest.mark.parametrize(
    "duration,expected",
    [
        (5, [(0, 5)]),
        (30, [(0, 30)]),
        (31, [(0, 30), (28, 31)]),
        (58, [(0, 30), (28, 58)]),
    ],
)
def test_terminal_overlap_is_not_repeated(duration, expected):
    assert list(chunk_windows(duration)) == expected


@pytest.mark.parametrize(
    "args", [(0, 30, 2), (50, 0, 2), (50, 30, -1), (50, 30, 30), (float("nan"), 30, 2)]
)
def test_invalid_chunk_configuration_fails(args):
    with pytest.raises(ValueError):
        list(chunk_windows(*args))


def test_two_hour_plan_is_finite_and_bounded():
    windows = list(chunk_windows(7200, 60, 2))
    assert len(windows) == 125
    assert windows[-1][1] == 7200
    assert all(0 < end - start <= 60 for start, end in windows)


def test_shared_words_offset_once_and_distinct_word_copies_also_shift():
    shared = Word("hello", 1, 2)
    copy = Word("hello", 1, 2)
    result = TranscriptionResult(
        "hello", words=[shared], segments=[Segment("hello", 1, 2, words=[shared, copy])]
    )
    offset_result(result, 28)
    assert shared.start == copy.start == result.segments[0].start == 29
    assert shared.end == copy.end == result.segments[0].end == 30


def test_extraction_uses_window_duration_and_cleans_all_temporary_files():
    commands = []
    paths = []

    def run(command, **kwargs):
        commands.append(command)
        Path(command[-1]).write_bytes(b"audio")
        return SimpleNamespace(returncode=0)

    with (
        patch("engine.asr.longform.probe_video", return_value={"duration": 31}),
        patch("engine.asr.longform.subprocess.run", side_effect=run),
    ):
        for start, path in extract_audio_chunks("source.mp4"):
            assert Path(path).exists()
            paths.append(path)
    assert [command[command.index("-t") + 1] for command in commands] == ["30.0", "3.0"]
    assert all(not Path(path).exists() for path in paths)


def test_extraction_failure_is_not_silently_skipped():
    paths = []

    def run(command, **kwargs):
        paths.append(command[-1])
        return SimpleNamespace(returncode=1)

    with (
        patch("engine.asr.longform.probe_video", return_value={"duration": 31}),
        patch("engine.asr.longform.subprocess.run", side_effect=run),
        pytest.raises(RuntimeError),
    ):
        list(extract_audio_chunks("source.mp4"))
    assert all(not Path(path).exists() for path in paths)


def test_failed_recognition_closes_extractor_without_partial_success():
    closed = []

    def chunks(*args):
        try:
            yield 0, "first.wav"
            yield 28, "second.wav"
        finally:
            closed.append(True)

    class Recognizer:
        def transcribe(self, path, **kwargs):
            if path == "second.wav":
                raise RuntimeError("decode failed")
            return TranscriptionResult("hello", words=[Word("hello", 0, 1)])

    with (
        patch("engine.asr.longform.extract_audio_chunks", side_effect=chunks),
        pytest.raises(RuntimeError),
    ):
        transcribe_chunks(Recognizer(), "source.mp4", 30, 2)
    assert closed == [True]


@pytest.mark.parametrize("backend", [Transcriber, ParakeetTranscriber])
def test_both_backends_use_shared_source_timeline_contract(backend):
    engine = backend()
    with patch(
        "engine.asr.longform.transcribe_chunks", return_value=["sentinel"]
    ) as shared:
        assert engine.transcribe_stream("source.mp4", chunk_duration=60, overlap=1) == [
            "sentinel"
        ]
    shared.assert_called_once_with(engine, "source.mp4", 60, 1)


def test_pipeline_cpu_budget_reaches_asr_and_diarizer():
    from engine.speech.pipeline import SpeechPipeline

    pipeline = SpeechPipeline(cpu_threads=2, max_workers=1)
    with patch(
        "engine.asr.backends.create_asr_engine", return_value="engine"
    ) as factory:
        assert pipeline.transcriber == "engine"
        assert factory.call_args.kwargs["cpu_threads"] == 2
    assert pipeline.diarizer._backend_config["threads"] == 2
