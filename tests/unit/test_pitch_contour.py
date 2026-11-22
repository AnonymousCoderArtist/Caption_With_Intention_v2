"""Per-syllable/per-letter pitch contour feed (M9/M10, 2026-11-22)."""

import numpy as np

from engine.audio_analysis.pitch_contour import (
    attach_syllable_pitch,
    letter_pitches_for_word,
    span_pitch,
)

SR = 16000


def _tone(hz, seconds, amp=0.4):
    t = np.arange(int(seconds * SR)) / SR
    # voiced-like: fundamental + a few harmonics
    return (amp * np.sin(2 * np.pi * hz * t)
            + amp * 0.3 * np.sin(2 * np.pi * 2 * hz * t)).astype(np.float32)


class TestSpanPitch:
    def test_recovers_voiced_pitch(self):
        audio = _tone(200.0, 0.4)
        p = span_pitch(audio, SR, 0.0, 0.4)
        assert p is not None
        assert abs(p - 200.0) < 8.0

    def test_low_pitch(self):
        audio = _tone(110.0, 0.4)
        p = span_pitch(audio, SR, 0.0, 0.4)
        assert p is not None
        assert abs(p - 110.0) < 6.0

    def test_silence_returns_none(self):
        audio = np.zeros(int(0.4 * SR), dtype=np.float32)
        assert span_pitch(audio, SR, 0.0, 0.4) is None

    def test_too_short_returns_none(self):
        audio = _tone(200.0, 0.02)
        assert span_pitch(audio, SR, 0.0, 0.02) is None


class TestAttachSyllablePitch:
    def test_voiced_syllables_get_pitch_hz(self):
        audio = np.concatenate([_tone(250.0, 0.5), _tone(120.0, 0.5)])
        syls = [
            {"text": "Un", "start": 0.0, "end": 0.5},
            {"text": "be", "start": 0.5, "end": 1.0},
        ]
        out = attach_syllable_pitch(audio, SR, syls)
        assert abs(out[0]["pitch_hz"] - 250.0) < 10.0
        assert abs(out[1]["pitch_hz"] - 120.0) < 7.0
        # originals untouched
        assert "pitch_hz" not in syls[0]

    def test_unvoiced_syllable_carries_no_key(self):
        audio = np.zeros(int(0.5 * SR), dtype=np.float32)
        out = attach_syllable_pitch(audio, SR, [{"text": "h", "start": 0.0, "end": 0.5}])
        assert "pitch_hz" not in out[0]


class TestLetterPitches:
    def test_loud_held_word_gets_per_letter_pitch(self):
        # 200Hz for the first half of the word, 140Hz for the second.
        audio = np.concatenate([_tone(200.0, 0.6), _tone(140.0, 0.6)])
        lp = letter_pitches_for_word(
            audio, SR, 0.0, 1.2, "WHOA", size_pct=9.0, syllable_count=1
        )
        assert lp is not None and len(lp) == 4
        assert abs(lp[0] - 200.0) < 10.0
        assert abs(lp[3] - 140.0) < 8.0

    def test_quiet_word_rejected(self):
        audio = _tone(200.0, 1.2)
        assert letter_pitches_for_word(
            audio, SR, 0.0, 1.2, "WHOA", size_pct=5.0, syllable_count=1
        ) is None

    def test_short_word_rejected(self):
        # 0.2s hold is under the 4-letter sweep minimum (0.24s).
        audio = _tone(200.0, 0.2)
        assert letter_pitches_for_word(
            audio, SR, 0.0, 0.2, "WHOA", size_pct=9.0, syllable_count=1
        ) is None

    def test_multi_syllable_word_rejected(self):
        audio = _tone(200.0, 1.2)
        assert letter_pitches_for_word(
            audio, SR, 0.0, 1.2, "WHOOOAAAH", size_pct=9.0, syllable_count=2
        ) is None

    def test_fully_unvoiced_returns_none(self):
        audio = np.zeros(int(1.2 * SR), dtype=np.float32)
        assert letter_pitches_for_word(
            audio, SR, 0.0, 1.2, "WHOA", size_pct=9.0, syllable_count=1
        ) is None


class TestPipelineContourWiring:
    """SpeechPipeline.attach_pitch_contours -> build_editor_payload ->
    Editor.build_from_transcript: the data feed lands on schema Words."""

    def _result(self, tmp_path):
        import soundfile as sf

        from engine.asr.models import Segment, TranscriptionResult, Word
        # "running" 250Hz then 120Hz (two syllables), "WHOA" held loud,
        # gliding 200 -> 140Hz.
        # 40ms energy dip between the "running" syllables so the
        # audio-refined boundary snap fires (M10 animation rule).
        dip = np.full(int(0.04 * SR), 1e-4, dtype=np.float32)
        audio = np.concatenate([
            _tone(250.0, 0.23), dip, _tone(120.0, 0.23),
            _tone(200.0, 0.6), _tone(140.0, 0.6),
        ])
        wav = tmp_path / "src.wav"
        sf.write(str(wav), audio, SR)
        words = [
            Word(text="running", start=0.0, end=0.5, confidence=0.9),
            Word(text="WHOA", start=0.5, end=1.7, confidence=0.9),
        ]
        seg = Segment(text="running WHOA", start=0.0, end=1.7, words=words)
        result = {
            "transcription": TranscriptionResult(
                text="running WHOA", segments=[seg], words=words,
                model="test", source_path=str(wav), duration=1.7,
            ),
            "diarization_segments": [],
            "intonation": {
                "words": [
                    {"text": "running", "start": 0.0, "end": 0.5,
                     "typography": {"size_pct": 5.0, "weight": 400, "width": 100}},
                    {"text": "WHOA", "start": 0.5, "end": 1.7,
                     "typography": {"size_pct": 9.0, "weight": 500, "width": 110}},
                ],
            },
        }
        return result, wav

    def test_payload_carries_syllable_pitch_and_letter_pitches(self, tmp_path):
        from engine.speech.pipeline import SpeechPipeline
        result, wav = self._result(tmp_path)
        pipe = SpeechPipeline()
        pipe.attach_pitch_contours(result, wav)
        contours = result["contours"]
        assert len(contours) == 2
        # "running": two syllables (>=0.2s word, audio-refined) animated
        syls = contours[0]["syllables"]
        assert syls and len(syls) == 2
        assert abs(syls[0]["pitch_hz"] - 250.0) < 12.0
        assert abs(syls[1]["pitch_hz"] - 120.0) < 8.0
        # "WHOA": single syllable + loud + held -> per-letter pitches
        lp = contours[1]["letter_pitches"]
        assert lp is not None and len(lp) == 4
        assert abs(lp[0] - 200.0) < 12.0
        assert abs(lp[3] - 140.0) < 8.0

        payload = pipe.build_editor_payload(result)
        w0, w1 = payload["transcript"][0]["words"]
        assert w0["size_pct"] == 5.0 and w0["weight"] == 400
        assert w0["syllables"][0]["pitch_hz"] is not None
        assert w1["size_pct"] == 9.0
        assert len(w1["letter_pitches"]) == 4

        from engine.editor.editor import Editor
        from schemas.project import Project, VideoInfo
        editor = Editor(project=Project(info=VideoInfo(title="t")))
        project = editor.build_from_transcript(
            payload["transcript"], speakers=payload["speakers"]
        )
        words = project.events[0].words
        assert words[0].syllables[0]["pitch_hz"] is not None
        assert words[1].letter_pitches is not None
        assert words[1].size_pct == 9.0

    def test_asr_leading_space_ignored(self):
        """ASR word texts carry a leading space; pitches align to the
        word's actual letters, matching the renderer's sweep units."""
        audio = _tone(200.0, 1.2)
        lp = letter_pitches_for_word(
            audio, SR, 0.0, 1.2, " WHOA", size_pct=9.0, syllable_count=1
        )
        assert lp is not None and len(lp) == 4


class TestSmoothWave:
    def test_octave_spike_removed_edge_glide_kept(self):
        from engine.audio_analysis.pitch_contour import smooth_wave

        contours = [
            {"pitch_hz": 150.0},
            {"pitch_hz": 310.0},  # octave-up spike
            {"pitch_hz": 148.0},
            {"pitch_hz": 146.0},
            {"pitch_hz": 100.0},  # edge: genuine glide down, must survive
        ]
        smooth_wave(contours)
        assert contours[1]["pitch_hz"] < 200.0  # spike pulled to neighbors
        assert contours[4]["pitch_hz"] == 100.0  # edge untouched
        assert contours[0]["pitch_hz"] == 150.0  # edge untouched

    def test_unvoiced_points_stay_none(self):
        from engine.audio_analysis.pitch_contour import smooth_wave

        contours = [{"pitch_hz": 150.0}, {"pitch_hz": None}, {"pitch_hz": 160.0}]
        smooth_wave(contours)
        assert contours[1]["pitch_hz"] is None

    def test_syllable_points_smoothed_in_place(self):
        from engine.audio_analysis.pitch_contour import smooth_wave

        contours = [
            {"syllables": [{"text": "a", "pitch_hz": 150.0},
                           {"text": "b", "pitch_hz": 300.0},
                           {"text": "c", "pitch_hz": 150.0}]},
            {"pitch_hz": 148.0},
        ]
        smooth_wave(contours)
        syls = contours[0]["syllables"]
        assert syls[1]["pitch_hz"] < 200.0
