"""Render a saved editor project: uv run python -m engine.renderer --help."""

from __future__ import annotations

import argparse
import tempfile
from pathlib import Path

from engine.renderer import CwiRenderer
from schemas.project import Project


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Burn a saved CWI project into its source video. Runs locally; no upload."
    )
    parser.add_argument("project", type=Path, help="Editor .cwi.json file")
    parser.add_argument("source", type=Path, help="Matching source video")
    parser.add_argument("output", type=Path, help="Output .mp4 path")
    parser.add_argument(
        "--font",
        type=Path,
        default=Path(__file__).resolve().parents[2] / "Instal Font - RobotoFlex.ttf",
    )
    parser.add_argument(
        "--overwrite", action="store_true", help="Replace an existing output file"
    )
    args = parser.parse_args(argv)
    try:
        if not args.project.is_file() or not args.source.is_file():
            raise ValueError("Project and source video must both be existing files.")
        protected = (args.source, args.project, args.font)
        if args.output.resolve() in {path.resolve() for path in protected} or (
            args.output.exists()
            and any(path.exists() and args.output.samefile(path) for path in protected)
        ):
            raise ValueError("Output must not replace the source video or project.")
        if args.output.suffix.lower() != ".mp4":
            raise ValueError("Choose an .mp4 output path.")
        if args.output.exists() and not args.overwrite:
            raise ValueError("Output exists. Choose another name or use --overwrite.")
        if not args.output.parent.is_dir():
            raise ValueError("Output folder does not exist.")
        if not args.font.is_file():
            raise ValueError("Font not found. Supply --font with a local font file.")
        project = Project.model_validate_json(args.project.read_text(encoding="utf-8"))
        # Keep any old output intact until the new render has succeeded.
        with tempfile.TemporaryDirectory(
            prefix=".cwi-output-", dir=args.output.parent
        ) as temporary:
            staged = Path(temporary) / "captioned.mp4"
            CwiRenderer(project, font_path=args.font, audio_codec="aac").render(
                args.source, staged
            )
            if args.output.exists() and not args.overwrite:
                raise ValueError(
                    "Output appeared during rendering. Choose another name."
                )
            staged.replace(args.output)
        print(f"Rendered {len(project.events)} captions to {args.output}")
        return 0
    except (ValueError, OSError, RuntimeError) as exc:
        parser.exit(1, f"Render failed: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
