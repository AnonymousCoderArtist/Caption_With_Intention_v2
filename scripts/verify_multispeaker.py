"""Run the real speech-to-caption path on a local multi-speaker clip.

Example (Python 3.10-3.12 with the ASR extra installed)::

    CWI_AUDIOCPP_CLI=/path/to/audiocpp_cli uv run python \
        scripts/verify_multispeaker.py clip.mp4 --output /tmp/cwi-review

The Nemotron CLI must be built with the nemotron_3_diar model enabled.
No speaker labels, timings, words or sound effects are injected. The output
is diagnostic, not a claim that recognition or attribution is correct.
Review the video and payload against the source before accepting it.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from engine.editor.editor import Editor
from engine.media.probe import probe_video
from engine.renderer.renderer import CwiRenderer
from engine.speech.pipeline import SpeechPipeline


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--asr-model", default="small.en")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    pipeline = SpeechPipeline(asr_model=args.asr_model, diarize_backend="nemotron")
    result = pipeline.run_full(str(args.source))
    payload = pipeline.build_editor_payload(result)
    (args.output / "payload.json").write_text(json.dumps(payload, indent=2))
    info = probe_video(str(args.source))
    project = Editor().build_from_transcript(
        payload["transcript"],
        video_width=info["width"],
        video_height=info["height"],
        fps=info["fps"],
        speakers=payload["speakers"],
    )
    (args.output / "project.json").write_text(project.model_dump_json(indent=2))
    font = Path(__file__).resolve().parents[1] / "Instal Font - RobotoFlex.ttf"
    CwiRenderer(project, font_path=str(font)).render(
        str(args.source), str(args.output / "captioned.mp4")
    )
    entries = payload["transcript"]
    report = {
        "events": len(entries),
        "speaker_identities": len(payload["speakers"]),
        "unassigned_events": sum(e.get("speaker_id") is None for e in entries),
        "invalid_word_windows": int(sum(
            w["end"] <= w["start"] for e in entries for w in e.get("words", [])
        )),
        "manual_review_required": True,
    }
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
