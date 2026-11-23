"""Reactive editor regressions: nested undo, text synchronization and retiming."""
import pytest

from engine.editor.editor import Editor
from schemas.project import CaptionEvent, Project, Style, Word


def editor():
    event = CaptionEvent(id="evt_001", text="go go", start=1, end=3,
                         words=[Word(text="go", start=1, end=1.5), Word(text="go", start=2, end=2.5)])
    return Editor(Project(events=[event]))


def test_event_text_updates_words_and_undo_keeps_models():
    e = editor()
    e.update_event("evt_001", text="stay here")
    assert [w.text for w in e.project.events[0].words] == ["stay", "here"]
    e.undo()
    assert isinstance(e.project.events[0].words[0], Word)
    assert isinstance(e.project.events[0].style, Style)
    assert e.project.events[0].text == "go go"
    e.redo()
    assert e.project.events[0].words[1].text == "here"


def test_word_count_change_redistributes_timing():
    e = editor()
    e.update_event("evt_001", text="a b c d")
    assert [(w.start, w.end) for w in e.project.events[0].words] == [(1, 1.5), (1.5, 2), (2, 2.5), (2.5, 3)]


def test_event_move_and_trim_retime_words_and_syllables():
    e = editor()
    e.project.events[0].words[0].syllables = [{"text": "go", "start": 1, "end": 1.5}]
    e.update_event("evt_001", start=2, end=6)
    assert e.project.events[0].words[0].start == 2
    assert e.project.events[0].words[0].end == 3
    assert e.project.events[0].words[0].syllables[0]["end"] == 3
    e.undo()
    assert e.project.events[0].words[0].start == 1


def test_word_edit_sync_and_repeat_safe_remove_undo():
    e = editor()
    before = e.project.events[0].model_dump()
    e.remove_word("evt_001", 1)
    assert len(e.project.events[0].words) == 1
    assert e.project.events[0].text == "go"
    e.undo()
    assert e.project.events[0].model_dump() == before
    e.redo()
    assert len(e.project.events[0].words) == 1
    e.update_word("evt_001", 0, text="stop")
    assert e.project.events[0].text == "stop"


def test_invalid_word_edit_is_atomic():
    e = editor()
    before = e.project.events[0].model_dump()
    with pytest.raises(ValueError):
        e.update_word("evt_001", 0, end=20)
    assert e.project.events[0].model_dump() == before
    assert not e.undo()


def test_style_undo_targets_style_not_event():
    e = editor()
    e.set_typography("evt_001", size_pct=9, size_mode="manual", read_ahead_opacity=.5)
    assert e.project.events[0].style.read_ahead_opacity == .5
    e.undo()
    assert e.project.events[0].style.size_pct == 5
    e.redo()
    assert e.project.events[0].style.size_pct == 9
    e.set_box_properties("evt_001", box_opacity=.2)
    e.undo()
    assert e.project.events[0].style.box_opacity == .9


def test_style_validation_is_atomic():
    e = editor()
    with pytest.raises(ValueError):
        e.set_box_properties('evt_001', box_opacity=2)
    assert e.project.events[0].style.box_opacity == .9
    assert not e.undo()


def test_project_metadata_undo():
    from engine.editor.api import EditorAPI

    e = editor()
    api = EditorAPI(e)
    assert api.update_project(project_name='Renamed', video={'width': 1280})['success']
    assert e.project.project_name == 'Renamed'
    assert e.project.video.width == 1280
    e.undo()
    assert e.project.video.width == 1920
    e.redo()
    assert e.project.project_name == 'Renamed'
    assert 'error' in api.update_project(video={'fps': 0})


def test_new_speaker_is_undoable_and_ids_do_not_collide():
    e = editor()
    first = e.add_speaker('One')
    second = e.add_speaker('Two')
    e.undo()
    assert [s.id for s in e.project.speakers] == [first.id]
    e.redo()
    assert len(e.project.speakers) == 2
    e.remove_speaker(first.id)
    new = e.add_speaker('Three')
    assert new.id != second.id


def test_delete_speaker_undo_restores_event_assignment():
    e = editor()
    speaker = e.add_speaker('One')
    e.project.events[0].speaker_id = speaker.id
    e.remove_speaker(speaker.id)
    assert e.project.events[0].speaker_id is None
    e.undo()
    assert e.project.events[0].speaker_id == speaker.id
    assert e.project.speakers[0].id == speaker.id


def test_cross_panel_style_paste_is_one_atomic_undo():
    e = editor()
    old = e.project.events[0].style.model_dump()
    e.set_style('evt_001', size_mode='manual', size_pct=9, pop_scale=1.4, box_opacity=.3)
    e.undo()
    assert e.project.events[0].style.model_dump() == old
    e.redo()
    assert e.project.events[0].style.box_opacity == .3
    assert e.project.events[0].style.size_pct == 9
    with pytest.raises(ValueError):
        e.set_style('evt_001', size_pct=7, box_opacity=5)
    assert e.project.events[0].style.size_pct == 9


def test_syllable_api_is_validated_and_undoable():
    e = editor()
    assert e.add_syllable('evt_001', 0, 'go', 1, 1.5)
    assert e.project.events[0].words[0].syllables[0]['text'] == 'go'
    e.undo()
    assert e.project.events[0].words[0].syllables is None
    e.redo()
    assert e.update_syllable('evt_001', 0, 0, pitch_hz=150)
    assert e.project.events[0].words[0].syllables[0]['pitch_hz'] == 150
    with pytest.raises(ValueError):
        e.update_syllable('evt_001', 0, 0, end=.5)
    assert e.project.events[0].words[0].syllables[0]['end'] == 1.5
    assert not e.add_syllable('evt_001', -1, 'wrong', 1, 2)


def test_invalid_word_typography_is_atomic():
    editor = Editor()
    event = editor.add_event(text="One", start=0, end=2)
    editor.update_event(event.id, text="One")
    before = editor.project.model_dump()
    count = len(editor._undo_stack)
    for values in [{"opacity": 2}, {"pitch_hz": -1}, {"weight": 0}, {"size_pct": float("nan")}]:
        with pytest.raises(ValueError):
            editor.update_word(event.id, 0, **values)
    assert editor.project.model_dump() == before
    assert len(editor._undo_stack) == count


def test_speaker_update_cannot_change_id_and_validates_before_mutating():
    e = Editor()
    speaker = e.add_speaker(name="Speaker")
    old_id = speaker.id
    e.update_speaker(old_id, id="other", name="Renamed")
    assert speaker.id == old_id
    before = e.project.model_dump()
    count = len(e._undo_stack)
    with pytest.raises(ValueError):
        e.update_speaker(old_id, color="invalid")
    assert e.project.model_dump() == before
    assert len(e._undo_stack) == count


def test_word_retime_scales_syllable_times_and_undo_restores():
    from engine.editor.editor import Editor
    from schemas.project import CaptionEvent, Project, Word
    editor=Editor(Project(events=[CaptionEvent(id='e',start=0,end=5,text='hello',words=[Word(text='hello',start=1,end=2,syllables=[{'text':'hel','start':1,'end':1.5},{'text':'lo','start':1.5,'end':2}])])]))
    before=editor.project.events[0].model_dump()
    editor.update_word('e',0,start=2,end=4)
    assert editor.project.events[0].words[0].syllables==[{'text':'hel','start':2,'end':3},{'text':'lo','start':3,'end':4}]
    editor.undo();assert editor.project.events[0].model_dump()==before


def test_malformed_syllable_pitch_is_rejected_without_history():
    editor = Editor(Project(events=[CaptionEvent(id="e", start=0, end=2, text="hello", words=[Word(text="hello", start=0, end=1)])]))
    before = editor.project.model_dump()
    for pitch in [-1, "bad", float("nan")]:
        with pytest.raises(ValueError, match="Syllable pitch"):
            editor.update_word("e", 0, syllables=[{"text": "hello", "start": 0, "end": 1, "pitch_hz": pitch}])
        assert editor.project.model_dump() == before
        assert not editor._undo_stack


def test_syllable_outside_word_is_rejected_without_history():
    editor = Editor(Project(events=[CaptionEvent(id="e", start=0, end=3, text="hello", words=[Word(text="hello", start=1, end=2)])]))
    before = editor.project.model_dump()
    for start, end in [(0.5, 2), (1, 2.5)]:
        with pytest.raises(ValueError, match="inside their word"):
            editor.update_word("e", 0, syllables=[{"text": "hello", "start": start, "end": end}])
        assert editor.project.model_dump() == before
        assert not editor._undo_stack


def test_word_typography_and_timing_keep_event_only_punctuation():
    e = editor()
    e.project.events[0].text = '"go go!"'
    e.update_word("evt_001", 0, weight=800)
    assert e.project.events[0].text == '"go go!"'
    e.update_word("evt_001", 0, start=1.1)
    assert e.project.events[0].text == '"go go!"'


def test_word_text_replaces_selected_repeat_and_keeps_mapped_punctuation():
    e = editor()
    e.project.events[0].text = '"go, go!"'
    e.update_word("evt_001", 1, text="stay")
    assert e.project.events[0].text == '"go, stay!"'
    e.undo()
    assert e.project.events[0].text == '"go, go!"'


def test_deleting_speaker_reopens_checked_event_review_and_undo_restores():
    e = editor()
    speaker = e.add_speaker(name="Speaker")
    event = e.project.events[0]
    event.speaker_id = speaker.id
    event.speaker_reviewed = True
    e.remove_speaker(speaker.id)
    assert event.speaker_id is None
    assert not event.speaker_reviewed
    e.undo()
    assert e.project.events[0].speaker_id == speaker.id
    assert e.project.events[0].speaker_reviewed


def test_word_text_change_clears_character_overrides_and_undo_restores():
    e = editor()
    e.project.events[0].words[0].character_colors = ["#ff0000"]
    e.update_word("evt_001", 0, text="changed")
    assert e.project.events[0].words[0].character_colors is None
    e.undo()
    assert e.project.events[0].words[0].character_colors == ["#ff0000"]
