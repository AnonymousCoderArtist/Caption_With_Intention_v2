"""Caption With Intention — Structured logging module."""

from __future__ import annotations

import logging
import logging.handlers
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class JSONFormatter(logging.Formatter):
    """JSON-formatted log records for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        entry: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(
                record.created, tz=timezone.utc
            ).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        if record.exc_info and record.exc_info[0] is not None:
            entry["exception"] = self.formatException(record.exc_info)
        if hasattr(record, "stage"):
            entry["stage"] = record.stage
        if hasattr(record, "project"):
            entry["project"] = record.project
        if hasattr(record, "event_id"):
            entry["event_id"] = record.event_id
        return json.dumps(entry, default=str)


class StageAdapter(logging.LoggerAdapter):
    """Logger adapter that injects the current pipeline stage."""

    def process(self, msg: str, kwargs: dict) -> tuple[str, dict]:
        return f"[{self.extra.get('stage', 'init')}] {msg}", kwargs


def setup_logging(
    log_dir: str | Path = "logs",
    level: int = logging.INFO,
    json_format: bool = True,
) -> logging.Logger:
    """Set up the structured logging system.

    Args:
        log_dir: Directory where log files are written.
        level: Minimum logging level.
        json_format: If True, use JSON format; otherwise plain text.

    Returns:
        The root logger instance.
    """
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    root = logging.getLogger("caption_with_intention")
    root.setLevel(level)

    # Console handler
    console = logging.StreamHandler()
    console.setLevel(level)
    if json_format:
        console.setFormatter(JSONFormatter())
    else:
        console.setFormatter(
            logging.Formatter(
                "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
            )
        )
    root.addHandler(console)

    # File handler — all logs
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    file_handler = logging.handlers.RotatingFileHandler(
        log_path / f"cwi_{timestamp}.log",
        maxBytes=50 * 1024 * 1024,  # 50 MB
        backupCount=10,
    )
    file_handler.setLevel(logging.DEBUG)
    if json_format:
        file_handler.setFormatter(JSONFormatter())
    else:
        file_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
            )
        )
    root.addHandler(file_handler)

    return root
