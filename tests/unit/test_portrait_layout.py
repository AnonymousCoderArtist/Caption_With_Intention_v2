"""Portrait layout pages read-ahead instead of letting libass wrap oversized lines."""
from itertools import pairwise

from engine.renderer.renderer import CwiRenderer
from schemas.project import CaptionEvent, Project, Word


def test_portrait_pages_preserve_words_absolute_times_and_nonoverlap():
    words = [Word(text='emphasis', start=i, end=i + .8) for i in range(20)]
    event = CaptionEvent(id='portrait', start=0, end=20,
                         text=' '.join(w.text for w in words), words=words)
    pages = CwiRenderer(Project(events=[event]))._split_event_lines(event, 540, 960)
    assert len(pages) > 2
    assert [w for child, _ in pages for w in child.words] == words
    assert pages[0][0].start == 0 and pages[-1][0].end == 20
    assert all(extra == 0 for _, extra in pages)
    for (a, _), (b, _) in pairwise(pages):
        assert a.end == b.start == b.words[0].start
    assert event.words == words and event.end == 20
