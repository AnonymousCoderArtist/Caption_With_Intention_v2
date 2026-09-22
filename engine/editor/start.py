#!/usr/bin/env python3
"""Start the CWI Editor dev server (Python API + Vite frontend)."""

import subprocess
import sys
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def main() -> None:
    print("=" * 60)
    print("  Caption With Intention — Editor Dev Server")
    print("=" * 60)

    # Start Python API server on port 8080
    print("\n[1/2] Starting Python API server on http://localhost:8080 ...")
    api_proc = subprocess.Popen(
        [sys.executable, str(PROJECT_ROOT / "engine/editor/server.py")],
        cwd=str(PROJECT_ROOT),
        env={**os.environ, "CWI_PORT": "8080"},
    )

    try:
        import time
        time.sleep(2)

        # Start Vite dev server on port 5173
        print("[2/2] Starting Vite dev server on http://localhost:5173 ...")
        print("\nOpen http://localhost:5173 in your browser")
        print("Press Ctrl+C to stop both servers\n")

        vite_proc = subprocess.Popen(
            ["npx", "vite", "--port", "5173"],
            cwd=str(PROJECT_ROOT / "frontend/editor"),
        )

        # Wait for either to exit
        api_proc.wait()
        vite_proc.wait()

    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        api_proc.terminate()
        try:
            api_proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            api_proc.kill()
        vite_proc.terminate()
        try:
            vite_proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            vite_proc.kill()


if __name__ == "__main__":
    main()
