"""M6 — Integration: ASR + correction → editor → renderer.

Proves the M6 exit criteria end-to-end without heavy AI dependencies
(ASR and diarization are stubbed): auto-generated word timelines are
editable and can drive the CWI renderer accurately enough for review.
"""

from __future__ import annotations

import pytest

from engine.asr.models import Segment, TranscriptionResult, Word
from engine.diarization.models import SpeakerSegment
from engine.editor.editor import Editor
from engine.renderer.renderer import CwiRenderer
from engine.speech.pipeline import SpeechPipeline
from schemas.project import Project, VideoInfo


def _asr_result() -> TranscriptionResult:
    """Fake whisper output with one ASR stutter ('world world')."""
    words = [
        Word("Hello", 0.0, 0.4, confidence=0.95),
        Word("world", 0.4, 0.9, confidence=0.88),
        Word("world", 0.9, 1.3, confidence=0.95),  # stutter
        Word("Goodbye", 1.5, 2.2, confidence=0.92),
    ]
    return TranscriptionResult(
        text="Hello world. Goodbye.",
        segments=[
            Segment(
                "Hello world.",
                0.0,
                1.3,
                confidence=0.9,
                words=[Word("Hello", 0.0, 0.4, confidence=0.95),
                       Word("world", 0.4, 0.9, confidence=0.88),
                       Word("world", 0.9, 1.3, confidence=0.95)],
            ),
            Segment(
                "Goodbye.",
                1.5,
                2.2,
                confidence=0.9,
                words=[Word("Goodbye", 1.5, 2.2, confidence=0.92)],
            ),
        ],
        words=words,
        language="en",
        model="large-v3-turbo",
        source_path="video.mp4",
        duration=3.0,
    )


def _diarization() -> list[SpeakerSegment]:
    return [
        SpeakerSegment("spk_1", 0.0, 1.4, confidence=0.9),
        SpeakerSegment("spk_2", 1.5, 2.5, confidence=0.9),
    ]


@pytest.fixture
def pipeline(monkeypatch) -> SpeechPipeline:
    p = SpeechPipeline()
    monkeypatch.setattr(p, "_run_asr", lambda source: _asr_result())
    monkeypatch.setattr(
        p,
        "_run_diarization",
        lambda source, min_speaker_duration: _diarization(),
    )
    return p


def test_pipeline_result_is_corrected_and_attributed(pipeline):
    result = pipeline.run("video.mp4")
    words = result["transcription"].words
    # Stutter collapsed, speakers attributed
    assert [w.text for w in words] == ["Hello", "world", "Goodbye"]
    assert result["corrections"]["summary"]["removed"] == 1
    assert words[0].speaker_id == "spk_1"
    assert words[2].speaker_id == "spk_2"


def test_word_timeline_is_editable(pipeline):
    """M6 exit criteria — the generated timeline lands in the editor and
    can be inspected/edited through the editor API."""
    result = pipeline.run("video.mp4")
    payload = pipeline.build_editor_payload(result)

    project = Project(
        project_name="M6",
        video=VideoInfo(width=1920, height=1080, fps=23.976, duration=3.0),
    )
    editor = Editor(project=project)
    editor.build_from_transcript(
        payload["transcript"],
        speakers=payload["speakers"],
    )

    assert len(editor.project.events) == 2
    event = editor.project.events[0]
    # Precise word timing survived the whole chain
    assert event.words[0].start == 0.0
    assert event.words[0].end == 0.4
    assert event.words[1].start == 0.4
    assert event.words[1].end == 0.9
    # Provenance (spec §2.2)
    assert event.source_model == "large-v3-turbo"
    assert event.words[0].source_model == "large-v3-turbo"
    assert event.speaker_id == "spk_1"
    assert [s.id for s in editor.project.speakers] == ["spk_1", "spk_2"]

    # Editable: word-level edits work on the generated timeline
    editor.update_word(event.id, 0, text="Howdy")
    assert editor.project.events[0].words[0].text == "Howdy"


def test_word_timeline_drives_renderer(pipeline, tmp_path):
    """M6 exit criteria — auto-generated words drive the CWI renderer."""
    result = pipeline.run("video.mp4")
    payload = pipeline.build_editor_payload(result)

    project = Project(
        project_name="M6",
        video=VideoInfo(width=1920, height=1080, fps=23.976, duration=3.0),
    )
    editor = Editor(project=project)
    editor.build_from_transcript(
        payload["transcript"],
        speakers=payload["speakers"],
    )

    ass = CwiRenderer(editor.project).render_ass(tmp_path / "video.mp4")

    # Corrected text only — the ASR stutter never reaches the render
    assert "world world" not in ass
    assert "Hello" in ass
    assert "Goodbye" in ass
    # Per-word overlay line for 'world' starts at its precise onset
    assert "Dialogue: 0,0:00:00.40," in ass
