"""Local sequential long-video/batch analysis. No video rendering or uploads."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sources", nargs="+", type=Path)
    parser.add_argument("--work-dir", required=True, type=Path)
    parser.add_argument(
        "--backend", choices=["faster_whisper", "parakeet"], default="faster_whisper"
    )
    parser.add_argument(
        "--model",
        default="base",
        help="Explicit low-memory diagnostic default; not the highest-accuracy model",
    )
    parser.add_argument(
        "--cpu-threads", type=int, default=max(1, min(4, (os.cpu_count() or 2) - 1))
    )
    parser.add_argument("--chunk-seconds", type=float, default=60)
    parser.add_argument("--overlap", type=float, default=2)
    parser.add_argument("--detect-sounds", action="store_true")
    args = parser.parse_args(argv)
    if args.cpu_threads < 1:
        parser.error("CPU thread count must be positive")
    # Set before importing NumPy/recognition runtimes in this entry point.
    for name in [
        "OMP_NUM_THREADS",
        "OPENBLAS_NUM_THREADS",
        "MKL_NUM_THREADS",
        "NUMEXPR_NUM_THREADS",
    ]:
        os.environ[name] = str(args.cpu_threads)
    from engine.speech.long_video import LongVideoRunner
    from engine.speech.pipeline import SpeechPipeline

    model = args.model
    if args.backend == "parakeet" and model == "base":
        model = "nemo-parakeet-tdt-0.6b-v3"
    pipeline = SpeechPipeline(
        asr_model=model,
        asr_backend=args.backend,
        cpu_threads=args.cpu_threads,
        max_workers=1,
    )
    runner = LongVideoRunner(
        pipeline,
        chunk_duration=args.chunk_seconds,
        overlap=args.overlap,
        detect_sounds=args.detect_sounds,
    )
    try:
        # One source at a time and one analysis stage at a time. The same lazy
        # model instance survives across files, no queue of decoded waveforms.
        for source in args.sources:
            key = hashlib.sha256(str(source.resolve()).encode()).hexdigest()[:12]
            work = args.work_dir / (source.stem + "-" + key)
            output = runner.run(
                source,
                work,
                progress=lambda event: print(json.dumps(event), flush=True),
            )
            print(
                json.dumps(
                    {
                        "state": "source_completed",
                        "source": str(source),
                        "payload": str(output),
                    }
                ),
                flush=True,
            )
    except (OSError, ValueError, RuntimeError, InterruptedError) as exc:
        parser.exit(
            1, f"Analysis stopped: {exc}\nCompleted checkpoints are preserved.\n"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
