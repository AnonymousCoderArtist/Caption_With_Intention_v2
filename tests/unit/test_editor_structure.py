import pytest

from engine.editor.editor import Editor
from schemas.project import CaptionEvent, Project, Word


def editor():
    return Editor(
        Project(
            events=[
                CaptionEvent(
                    id="e",
                    start=0,
                    end=3,
                    text="One two",
                    words=[
                        Word(text="One", start=0.1, end=1),
                        Word(text="two", start=1.5, end=2.5),
                    ],
                )
            ]
        )
    )


def test_split_merge_preserve_word_timing_and_one_undo():
    e = editor()
    before = e.project.model_dump()
    e.structure_events(["e"], "split", 1.2)
    assert [x.text for x in e.project.events] == ["One", "two"]
    assert e.project.events[1].words[0].start == 1.5
    e.structure_events([x.id for x in e.project.events], "merge")
    assert e.project.events[0].text == "One two"
    assert e.project.events[0].words == Project.model_validate(before).events[0].words
    e.undo()
    assert len(e.project.events) == 2
    e.undo()
    assert e.project.events == Project.model_validate(before).events


def test_split_inside_word_is_rejected_atomically():
    e = editor()
    before = e.project.model_dump()
    with pytest.raises(ValueError):
        e.structure_events(["e"], "split", 0.5)
    assert e.project.model_dump() == before
    assert not e._undo_stack


def test_merge_different_style_or_overlap_rejected():
    e = editor()
    e.structure_events(["e"], "split", 1.2)
    e.project.events[1].style.italic = True
    with pytest.raises(ValueError):
        e.structure_events([x.id for x in e.project.events], "merge")
    e.project.events[1].style.italic = False
    e.project.events[1].start = 0.5
    with pytest.raises(ValueError):
        e.structure_events([x.id for x in e.project.events], "merge")


def test_untimed_first_caption_merge_is_rejected_without_mutating():
    e = editor()
    e.structure_events(["e"], "split", 1.2)
    e.project.events[0].words = []
    before = e.project.model_dump()
    with pytest.raises(ValueError):
        e.structure_events([x.id for x in e.project.events], "merge")
    assert e.project.model_dump() == before


def test_merge_preserves_notes_and_unresolved_review():
    e = editor()
    e.structure_events(["e"], "split", 1.2)
    e.project.events[0].notes = "first"
    e.project.events[1].notes = "second"
    e.project.events[0].speaker_reviewed = True
    e.project.events[1].speaker_review_required = True
    e.project.events[1].speaker_review_reasons = ["short turn"]
    e.structure_events([x.id for x in e.project.events], "merge")
    result = e.project.events[0]
    assert result.notes == "first\n\nsecond"
    assert not result.speaker_reviewed
    assert result.speaker_review_required
    assert result.speaker_review_reasons == ["short turn"]


def test_split_preserves_punctuation_outside_word_tokens():
    e = editor()
    e.project.events[0].text = "One,  two!"
    e.structure_events(["e"], "split", 1.2)
    assert [x.text for x in e.project.events] == ["One,", "two!"]
    e.undo()
    assert e.project.events[0].text == "One,  two!"
