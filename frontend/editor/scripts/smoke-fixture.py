"""Generate a tiny synthetic project/video. No external media required."""

import subprocess
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(root))
from schemas.project import CaptionEvent, Project, Speaker, Style, VideoInfo, Word

folder = Path(sys.argv[1])
folder.mkdir(parents=True, exist_ok=True)
project = Project(
    project_name="Editor smoke test",
    video=VideoInfo(width=640, height=360, fps=30, duration=4),
    speakers=[Speaker(id="s", name="Test speaker", color="#D6BB6E")],
    events=[
        CaptionEvent(
            id="e",
            start=0,
            end=3.8,
            text="Quiet emphasis settles.",
            speaker_id="s",
            speaker_review_required=True,
            speaker_review_reasons=["Synthetic uncertain turn"],
            style=Style(box_opacity=0.3),
            words=[
                Word(text="Quiet", start=0.2, end=0.8),
                Word(text="emphasis", start=1, end=1.8, size_pct=8.5, weight=800),
                Word(text="settles.", start=2, end=2.8),
            ],
        )
    ],
)
(folder / "project.cwi.json").write_text(project.model_dump_json(indent=2))
subprocess.run(
    [
        "ffmpeg",
        "-v",
        "error",
        "-y",
        "-f",
        "lavfi",
        "-i",
        "color=c=0x404040:s=640x360:r=30:d=4",
        "-f",
        "lavfi",
        "-i",
        "sine=frequency=440:sample_rate=48000:duration=4",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-shortest",
        str(folder / "source.mp4"),
    ],
    check=True,
)

portrait = project.model_copy(deep=True)
portrait.video.width, portrait.video.height = 360, 640
portrait.project_name = "Rotated portrait smoke test"
(folder / "portrait.cwi.json").write_text(portrait.model_dump_json(indent=2))
subprocess.run(
    [
        "ffmpeg",
        "-v",
        "error",
        "-y",
        "-i",
        str(folder / "source.mp4"),
        "-c",
        "copy",
        "-metadata:s:v:0",
        "rotate=90",
        str(folder / "portrait.mp4"),
    ],
    check=True,
)
