"""Inspector edits must survive the final-render path, not only browser preview."""
from engine.renderer.renderer import CwiRenderer
from schemas.project import CaptionEvent, Project, Speaker, Style, Word


def make_event(**style):
    return CaptionEvent(id="e", start=0, end=3, text="One word", speaker_id="s",
                        style=Style(**style), words=[Word(text="One", start=.1, end=1.2, source_model="test", size_pct=6), Word(text="word", start=1.3, end=2.4)])


def test_manual_typography_overrides_automatic_measurements():
    event = make_event(size_mode="manual", size_pct=8, weight_mode="manual", weight=900, width_mode="manual", width=120)
    _, spans = CwiRenderer(Project(events=[event]))._compose_word_spans(event, 1000)
    assert all(span["size_px"] == 80 for span in spans)
    assert all(span["bold"] == "\\b1" for span in spans)
    assert all(span["width"] == 120 for span in spans)


def test_word_manual_override_bypasses_automatic_size_stabilizer():
    event = make_event()
    event.words[0].manual_override = True
    _, spans = CwiRenderer(Project(events=[event]))._compose_word_spans(event, 1000)
    assert spans[0]["size_px"] == 60


def test_box_opacity_padding_and_italic_reach_ass():
    event = make_event(box_opacity=.3, box_padding=24, italic=True)
    project = Project(events=[event], speakers=[Speaker(id="s", name="Speaker", color="#E5E517")])
    renderer = CwiRenderer(project)
    lines = renderer._build_cwi_events()
    boxes = [line for line in lines if line.get("type") == "box"]
    assert boxes
    assert all("\\1a&HB2&" in line["tags"]["box"] for line in boxes)
    assert all("\\p1" in line["tags"]["box"] for line in boxes)
    ass = renderer.render_ass("not-a-video.mp4")
    assert "\\i1" in ass
    assert "\\p1" in ass


def test_custom_vector_box_uses_libass_real_dim_font_metrics():
    from pathlib import Path
    font = Path(__file__).resolve().parents[2] / "Instal Font - RobotoFlex.ttf"
    event = make_event(box_opacity=.3, box_padding=12)
    renderer = CwiRenderer(Project(events=[event]), font_path=font)
    lines = renderer._build_cwi_events(1280, 720)
    box = next(line for line in lines if line.get("type") == "box")
    assert renderer._ass_em_scale == 2048 / 3061
    # Before speech: nominal em advance must shrink to libass REAL_DIM.
    expected_width = round(renderer._estimate_span_width("One word", 36, 100) * 2048 / 3061 + 24)
    assert box["text"] == f"m 0 0 l {expected_width} 0 l {expected_width} 60 l 0 60"


def test_custom_vector_box_includes_manual_word_width():
    from pathlib import Path
    font = Path(__file__).resolve().parents[2] / 'Instal Font - RobotoFlex.ttf'
    event = make_event(box_opacity=.3)
    event.words[0].width = 150
    event.words[1].width = 150
    renderer = CwiRenderer(Project(events=[event]), font_path=font)
    boxes = [line for line in renderer._build_cwi_events(1280, 720) if line.get('type') == 'box']
    before = boxes[0]
    during = next(line for line in boxes if .3 <= line['start'] < .5)
    assert int(during['text'].split()[4]) > int(before['text'].split()[4])


def test_metadata_exception_profile_does_not_log_false_render_failure():
    event = make_event()
    event.exception_profile = 'project'
    toggles = CwiRenderer(Project(events=[event]))._get_exception_toggles(event)
    assert toggles['attribution_colors_on_off'] is True


def test_wrapped_caption_keeps_punctuation_outside_word_tokens():
    words = [Word(text="emphasis", start=i, end=i + .8) for i in range(12)]
    event = CaptionEvent(id="punctuation", start=0, end=12,
                         text=", ".join(w.text for w in words) + "!", words=words)
    lines = CwiRenderer(Project(events=[event]))._split_event_lines(event, 640, 480)
    assert len(lines) == 2
    assert lines[0][0].text.endswith(",")
    assert lines[1][0].text.endswith("!")
    assert sum(child.text.count(",") for child, _ in lines) == 11
