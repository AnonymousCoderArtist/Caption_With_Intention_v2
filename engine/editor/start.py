"""Start the CWI Editor dev server (Python API + Vite frontend)."""

import os
import signal
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def main() -> None:
    print("=" * 60)
    print("  Caption With Intention — Editor Dev Server")
    print("=" * 60)

    def stop(signum, frame):
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, stop)

    api_port = os.environ.get("CWI_PORT", "8080")
    ui_port = os.environ.get("CWI_UI_PORT", "5173")
    # Keep the frontend proxy and API endpoint on the same chosen port.
    print(f"\n[1/2] Starting Python API server on http://localhost:{api_port} ...")
    api_proc = subprocess.Popen(
        [sys.executable, str(PROJECT_ROOT / "engine/editor/server.py")],
        cwd=str(PROJECT_ROOT),
        env={**os.environ, "CWI_PORT": api_port},
    )

    vite_proc = None
    try:
        import time
        time.sleep(0.5)
        if api_proc.poll() is not None:
            raise RuntimeError("API server did not start. Check whether the selected API port is already in use.")

        # Start Vite dev server on port 5173
        print(f"[2/2] Starting Vite dev server on http://localhost:{ui_port} ...")
        print(f"\nOpen http://localhost:{ui_port} in your browser")
        print("Press Ctrl+C to stop both servers\n")

        vite_proc = subprocess.Popen(
            ["node", "node_modules/vite/bin/vite.js", "--port", ui_port, "--strictPort"],
            cwd=str(PROJECT_ROOT / "frontend/editor"),
            env={**os.environ, "CWI_API_PORT": api_port},
        )

        # Stop the other process if either server exits.
        while api_proc.poll() is None and vite_proc.poll() is None:
            time.sleep(0.2)
        raise RuntimeError("An editor server stopped. Both servers have been shut down; check the output above.")

    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        api_proc.terminate()
        try:
            api_proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            api_proc.kill()
            api_proc.wait()
        if vite_proc is not None:
            vite_proc.terminate()
            try:
                vite_proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                vite_proc.kill()
                vite_proc.wait()


if __name__ == "__main__":
    main()
