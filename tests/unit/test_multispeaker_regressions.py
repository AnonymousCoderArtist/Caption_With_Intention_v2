"""Regressions found by the multi-speaker end-to-end run."""
import numpy as np

from engine.alignment.aligner import Aligner
from engine.asr.models import Word
from engine.diarization.diarizer import Diarizer
from engine.editor.editor import Editor
from engine.rules.colors import assign_speaker_color
from schemas.project import EventType, Speaker


def test_fingerprint_is_callable_outside_vad_loader():
    fingerprint = Diarizer._compute_fingerprint(np.ones(16000, dtype=np.float32), 16000)
    assert fingerprint.shape == (5,)
    assert np.isfinite(fingerprint).all()


def test_vad_timestamps_are_audio_samples():
    audio = np.ones(32000, dtype=np.float32)
    segments = Diarizer(backend="diarize")._fingerprint_diarize(
        audio, 16000, [{"start": 8000, "end": 24000}], 2
    )
    assert len(segments) == 1
    assert segments[0].start == 0.5
    assert segments[0].end == 1.5


def test_hash_collision_does_not_reuse_main_speaker_color():
    assigned = {}
    for i in range(6):
        assign_speaker_color(Speaker(id=f"SPEAKER_{i:02d}"), assigned)
    assert len(assigned) == 6
    assert len(set(assigned.values())) == 6


def test_editor_preserves_sound_effect_event_type():
    editor = Editor()
    project = editor.build_from_transcript([
        {"text": "[CLANG]", "start": 0.2, "end": 1.0, "type": "sound_effect"}
    ])
    assert project.events[0].type == EventType.sound_effect


def test_editor_add_event_respects_music_type():
    event = Editor().add_event("[MUSIC]", 0.0, 2.0, event_type="music")
    assert event.type == EventType.music


def test_alignment_zero_duration_asr_word_gets_positive_window(tmp_path):
    import soundfile as sf

    path = tmp_path / "audio.wav"
    sf.write(path, np.zeros(32000, dtype=np.float32), 16000)
    result = Aligner(audio_path=str(path)).align(
        asr_words=[Word("the", 0.5, 0.5)]
    )
    assert result.words[0].end > result.words[0].start
