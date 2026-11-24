"""Make an editable CWI project JSON from a raw video (local speech recognition).

    uv run python scripts/make_project.py my_video.mp4 --output my_video.cwi.json

Then open the JSON in the editor and pick the same video. Speakers are not
reliable: review and rename them by hand. Output is a starting draft only.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from engine.editor.editor import Editor
from engine.media.probe import probe_video
from engine.speech.pipeline import SpeechPipeline


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--asr-model", default="small.en", help="tiny.en, base.en, small.en (default), medium.en")
    parser.add_argument("--detect-sounds", action="store_true")
    args = parser.parse_args()
    pipeline = SpeechPipeline(asr_model=args.asr_model)
    result = pipeline.run_full(str(args.source), detect_sounds=args.detect_sounds)
    payload = pipeline.build_editor_payload(result)
    info = probe_video(str(args.source))
    project = Editor().build_from_transcript(
        payload["transcript"], video_width=info["width"], video_height=info["height"],
        fps=info["fps"], speakers=payload["speakers"],
    )
    args.output.write_text(project.model_dump_json(indent=2))
    print(f"Wrote {args.output}: {len(payload['transcript'])} captions, {len(payload['speakers'])} speakers")


if __name__ == "__main__":
    main()
