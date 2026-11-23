"""CWI Editor Development Server.

Serves the React frontend and exposes the EditorAPI as HTTP endpoints.
Run: python engine/editor/server.py
Then open http://localhost:8080
"""

from __future__ import annotations

import json
import logging
import os
import sys
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from engine.editor.api import EditorAPI
from engine.editor.render_jobs import RenderJobs

logger = logging.getLogger("caption_with_intention")

PORT = int(os.environ.get("CWI_PORT", "8080"))
FRONTEND_DIR = PROJECT_ROOT / "frontend" / "editor"

api = EditorAPI()
api_lock = threading.RLock()
render_jobs = RenderJobs(PROJECT_ROOT / "Instal Font - RobotoFlex.ttf")


class CWIHandler(SimpleHTTPRequestHandler):
    """HTTP handler that serves frontend files + EditorAPI endpoints."""

    def log_message(self, format: str, *args: Any) -> None:
        logger.info(format, *args)

    def do_GET(self) -> None:
        if self.path.startswith("/api/render/"):
            self.handle_render()
            return
        if self.path.startswith("/api/"):
            if not self.local_request():
                return
            self.handle_api()
            return
        super().do_GET()

    def do_POST(self) -> None:
        if self.path.startswith("/api/render/"):
            self.handle_render()
            return
        if self.path.startswith("/api/"):
            if not self.local_request():
                return
            self.handle_api()
            return
        self.send_error(404)

    def local_request(self) -> bool:
        from urllib.parse import urlparse

        local_hosts = {"localhost", "127.0.0.1", "::1"}
        host = urlparse("http://" + self.headers.get("Host", "")).hostname
        origin = self.headers.get("Origin", "")
        if host not in local_hosts or (
            origin and urlparse(origin).hostname not in local_hosts
        ):
            self._json_response(
                403, {"error": "The local API accepts local editor requests only."}
            )
            return False
        return True

    def handle_render(self) -> None:
        """Only local requests can create/read render jobs; IDs are unguessable."""
        if not self.local_request():
            return
        try:
            parts = self.path.split("?", 1)[0].strip("/").split("/")
            if self.command == "POST" and parts == ["api", "render", "create"]:
                length = int(self.headers.get("Content-Length", 0))
                if not 0 < length <= 20 * 1024**2:
                    raise ValueError("Project JSON must be smaller than 20 MB.")
                request_key = self.headers.get("X-CWI-Request-Key")
                if request_key and (len(request_key) > 80 or not all(c.isalnum() or c == "-" for c in request_key)):
                    raise ValueError("Invalid render request key.")
                result = render_jobs.create(json.loads(self.rfile.read(length)), request_key=request_key)
            elif len(parts) == 4 and parts[:2] == ["api", "render"]:
                job_id, action = parts[2:]
                if action == "source" and self.command == "POST":
                    # Bound an abandoned connection so it cannot reserve the
                    # only render worker forever. This is an idle-read limit.
                    self.connection.settimeout(120)
                    result = render_jobs.upload(
                        job_id, self.rfile, int(self.headers.get("Content-Length", 0))
                    )
                elif action == "cancel" and self.command == "POST":
                    result = render_jobs.cancel(job_id)
                elif action == "status" and self.command == "GET":
                    result = render_jobs.status(job_id)
                elif action == "download" and self.command == "GET":
                    file = render_jobs.download(job_id)
                    size = file.stat().st_size
                    first, last = 0, size - 1
                    partial = self.headers.get("Range", "")
                    if partial:
                        import re

                        match = re.fullmatch(r"bytes=(\d*)-(\d*)", partial)
                        if not match or not any(match.groups()):
                            self.send_error(416)
                            return
                        start, end = match.groups()
                        if start:
                            first = int(start)
                            last = min(size - 1, int(end)) if end else size - 1
                        else:
                            first = max(0, size - int(end))
                        if first > last or first >= size:
                            self.send_response(416)
                            self.send_header("Content-Range", f"bytes */{size}")
                            self.end_headers()
                            return
                    self.send_response(206 if partial else 200)
                    self.send_header("Content-Type", "video/mp4")
                    self.send_header("Accept-Ranges", "bytes")
                    self.send_header(
                        "Content-Disposition", 'inline; filename="captioned.mp4"'
                    )
                    self.send_header("Content-Length", str(last - first + 1))
                    if partial:
                        self.send_header(
                            "Content-Range", f"bytes {first}-{last}/{size}"
                        )
                    self.end_headers()
                    with file.open("rb") as source:
                        source.seek(first)
                        remaining = last - first + 1
                        while remaining:
                            chunk = source.read(min(1024 * 1024, remaining))
                            if not chunk:
                                break
                            self.wfile.write(chunk)
                            remaining -= len(chunk)
                    return
                else:
                    raise ValueError("Unknown render action.")
            else:
                raise ValueError("Unknown render endpoint.")
            self._json_response(200, result)
        except KeyError:
            self._json_response(
                404, {"error": "This render expired. Start another render."}
            )
        except (ValueError, OSError) as exc:
            self._json_response(400, {"error": str(exc)[:300]})

    def handle_api(self) -> None:
        """Handle API requests by delegating to EditorAPI."""
        # Parse the action from the URL path
        path = self.path[len("/api/") :]
        action = path.split("?")[0]  # Remove query string

        if self.command != "POST" and action not in {
            "get_project",
            "get_project_summary",
            "get_events",
            "get_speakers",
            "can_undo",
            "can_redo",
        }:
            self._json_response(405, {"error": "Edits require a POST request."})
            return
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            if not 0 <= content_length <= 20 * 1024**2:
                raise ValueError("API request must be smaller than 20 MB.")
            body = self.rfile.read(content_length) if content_length else b""
            params = json.loads(body.decode("utf-8")) if body else {}
            if not isinstance(params, dict):
                raise TypeError("API parameters must be a JSON object.")
        except (ValueError, TypeError, UnicodeDecodeError) as exc:
            self._json_response(400, {"error": str(exc)[:300]})
            return

        # Call the appropriate method on EditorAPI
        method = getattr(api, action, None) if not action.startswith("_") else None
        if method is None or not callable(method):
            self._json_response(404, {"error": f"Unknown action: {action}"})
            return

        try:
            with api_lock:
                if params:
                    result = method(**params)
                else:
                    result = method()
            self._json_response(200, result)
        except Exception as exc:  # noqa: BLE001 - publish API failures without dropping HTTP responses
            self._json_response(500, {"error": str(exc)})

    def _json_response(self, status: int, data: dict) -> None:
        response = json.dumps(data, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response)))
        origin = self.headers.get("Origin", "")
        if origin in {
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            f"http://localhost:{PORT}",
            f"http://127.0.0.1:{PORT}",
        }:
            self.send_header("Access-Control-Allow-Origin", origin)
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(response)

    def do_OPTIONS(self) -> None:
        self.send_response(200)
        origin = self.headers.get("Origin", "")
        if origin in {
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            f"http://localhost:{PORT}",
            f"http://127.0.0.1:{PORT}",
        }:
            self.send_header("Access-Control-Allow-Origin", origin)
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def translate_path(self, path: str) -> str:
        """Serve frontend files from the editor directory."""
        # Remove leading slash
        path = path.lstrip("/")

        # Default to index.html for SPA routing
        if not path or path == "":
            path = "index.html"

        # Security: don't allow ..
        if ".." in path.split("/"):
            return str(FRONTEND_DIR / "index.html")

        file_path = FRONTEND_DIR / path
        if file_path.exists() and file_path.is_file():
            return str(file_path)

        # Fall back to index.html for SPA
        return str(FRONTEND_DIR / "index.html")


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    server = ThreadingHTTPServer(("localhost", PORT), CWIHandler)
    logger.info("CWI Editor server starting on http://localhost:%d", PORT)
    logger.info("Press Ctrl+C to stop")

    import signal

    def stop_server(signum, frame):
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, stop_server)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        render_jobs.close()
        server.server_close()


if __name__ == "__main__":
    main()
