"""Speaker turns remain distinct during the editor handoff."""
from engine.asr.models import Word

def test_sentence_is_split_at_word_speaker_turns():
    from engine.asr.models import Segment, TranscriptionResult
    from engine.speech.pipeline import SpeechPipeline

    words = [
        Word("Question?", 0.0, 1.0, speaker_id="a"),
        Word("Yes.", 1.0, 1.3, speaker_id="b"),
        Word("Unknown.", 1.3, 1.6, speaker_id=None),
    ]
    result = {"transcription": TranscriptionResult(
        text="Question? Yes. Unknown.", words=words,
        segments=[Segment("Question? Yes. Unknown.", 0.0, 1.6, words=words)],
    )}
    entries = SpeechPipeline().build_editor_payload(result)["transcript"]
    assert [e["speaker_id"] for e in entries] == ["a", "b", None]
    assert [e["text"] for e in entries] == ["Question?", "Yes.", "Unknown."]
    assert [(e["start"], e["end"]) for e in entries] == [
        (0.0, 1.0), (1.0, 1.3), (1.3, 1.6)
    ]


def test_word_only_payload_is_also_split_at_speaker_changes():
    from engine.asr.models import TranscriptionResult
    from engine.speech.pipeline import SpeechPipeline

    result = {"transcription": TranscriptionResult(
        text="Hello there", words=[
            Word("Hello", 0.0, 0.5, speaker_id="a"),
            Word("there", 0.5, 1.0, speaker_id="b"),
        ],
    )}
    entries = SpeechPipeline().build_editor_payload(result)["transcript"]
    assert [e["speaker_id"] for e in entries] == ["a", "b"]
