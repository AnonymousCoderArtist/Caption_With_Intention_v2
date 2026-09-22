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
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from typing import Any

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from engine.editor.api import EditorAPI  # noqa: E402

logger = logging.getLogger("caption_with_intention")

PORT = int(os.environ.get("CWI_PORT", "8080"))
FRONTEND_DIR = PROJECT_ROOT / "frontend" / "editor"

api = EditorAPI()


class CWIHandler(SimpleHTTPRequestHandler):
    """HTTP handler that serves frontend files + EditorAPI endpoints."""

    def log_message(self, format: str, *args: Any) -> None:
        logger.info(format, *args)

    def do_GET(self) -> None:
        if self.path.startswith("/api/"):
            self.handle_api()
            return
        super().do_GET()

    def do_POST(self) -> None:
        if self.path.startswith("/api/"):
            self.handle_api()
            return
        self.send_error(404)

    def handle_api(self) -> None:
        """Handle API requests by delegating to EditorAPI."""
        # Parse the action from the URL path
        path = self.path[len("/api/") :]
        action = path.split("?")[0]  # Remove query string

        # Read body
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length) if content_length else b""

        params = {}
        if body:
            try:
                params = json.loads(body.decode("utf-8"))
            except json.JSONDecodeError:
                params = {}

        # Call the appropriate method on EditorAPI
        method = getattr(api, action, None)
        if method is None:
            self._json_response(404, {"error": f"Unknown action: {action}"})
            return

        try:
            if params:
                result = method(**params)
            else:
                result = method()
            self._json_response(200, result)
        except Exception as exc:
            self._json_response(500, {"error": str(exc)})

    def _json_response(self, status: int, data: dict) -> None:
        response = json.dumps(data, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(response)

    def do_OPTIONS(self) -> None:
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
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

    server = HTTPServer(("localhost", PORT), CWIHandler)
    logger.info("CWI Editor server starting on http://localhost:%d", PORT)
    logger.info("Press Ctrl+C to stop")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        server.server_close()


if __name__ == "__main__":
    main()
