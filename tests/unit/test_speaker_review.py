from engine.asr.models import Word
from engine.diarization.review import attribution_review
from engine.editor.editor import Editor


def test_ambiguous_overlap_is_exposed_without_changing_identity():
    words = [Word("yes", 0, 1, speaker_id="a")]
    review = attribution_review(
        words,
        [
            {"speaker_id": "a", "start": 0, "end": 1},
            {"speaker_id": "b", "start": 0, "end": 0.9},
        ],
        "a",
    )
    assert review["speaker_review_required"]
    assert any("Competing" in reason for reason in review["speaker_review_reasons"])
    assert review["speaker_coverage"] == 1
    assert words[0].speaker_id == "a"


def test_clear_coverage_is_not_identity_confidence():
    review = attribution_review(
        [Word("hello", 0, 1)], [{"speaker_id": "a", "start": 0, "end": 1}], "a"
    )
    assert not review["speaker_review_required"]
    assert "confidence" not in review


def test_review_metadata_survives_payload_to_editor():
    p = Editor().build_from_transcript(
        [
            {
                "text": "yes",
                "start": 0,
                "end": 1,
                "speaker_review_required": True,
                "speaker_review_reasons": ["Competing segments"],
                "speaker_coverage": 0.4,
            }
        ]
    )
    assert p.events[0].speaker_review_required
    assert p.events[0].speaker_coverage == 0.4


def test_adjacent_same_speaker_segments_count_union_coverage():
    review = attribution_review(
        [Word("hello", 0, 1)],
        [
            {"speaker_id": "a", "start": 0, "end": 0.5},
            {"speaker_id": "a", "start": 0.5, "end": 1},
        ],
        "a",
    )
    assert review["speaker_coverage"] == 1
    assert not review["speaker_review_required"]


def test_duplicate_segments_do_not_inflate_coverage():
    review = attribution_review(
        [Word("hello", 0, 1)],
        [
            {"speaker_id": "a", "start": 0, "end": 0.4},
            {"speaker_id": "a", "start": 0, "end": 0.4},
        ],
        "a",
    )
    assert review["speaker_coverage"] == 0.4
    assert review["speaker_review_required"]
