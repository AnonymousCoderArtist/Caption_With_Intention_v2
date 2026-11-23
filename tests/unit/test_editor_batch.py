import pytest

from engine.editor.editor import Editor
from schemas.project import CaptionEvent, Project, Word


def editor():
    return Editor(Project(events=[CaptionEvent(id=str(i),start=i*2,end=i*2+1,text='word',words=[Word(text='word',start=i*2,end=i*2+1)])for i in range(3)]))


def test_batch_move_one_undo_retimes_all_words():
    e=editor();before=e.project.model_dump()
    e.batch_events(['0','1'],'move',.5)
    assert [x.start for x in e.project.events]==[.5,2.5,4]
    assert e.project.events[1].words[0].start==2.5
    e.undo();assert e.project.events==Project.model_validate(before).events


def test_ripple_move_shifts_material_after_selection_boundary():
    e=editor();e.batch_events(['0'],'move',1,True)
    assert [x.start for x in e.project.events]==[1,3,5]


def test_ripple_delete_closes_union_not_span_with_gaps():
    e=editor();e.batch_events(['0','1'],'delete',ripple=True)
    assert len(e.project.events)==1
    assert e.project.events[0].start==2
    e.undo();assert len(e.project.events)==3


def test_invalid_batch_is_atomic():
    e=editor();before=e.project.model_dump()
    for ids,delta in [(['0'],-1),(['missing'],1)]:
        with pytest.raises(ValueError):e.batch_events(ids,'move',delta)
    assert e.project.model_dump()==before
    assert not e._undo_stack


def test_batch_speaker_assignment_and_review_is_one_undo():
    e=editor();speaker=e.add_speaker('Speaker')
    before=e.project.model_dump()
    e.assign_speaker_events(['0','1'],speaker.id)
    assert all(x.speaker_id==speaker.id and x.speaker_reviewed for x in e.project.events[:2])
    e.undo();assert e.project.events==Project.model_validate(before).events
