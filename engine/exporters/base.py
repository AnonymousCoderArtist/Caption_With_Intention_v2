"""Base caption exporter — plugin-registered format writer."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any

from engine.core.registry import Plugin

logger = logging.getLogger("caption_with_intention")


class CaptionExporter(Plugin, ABC):
    """Abstract base for caption format exporters.

    Subclasses must set `name` and implement `export()`.
    Auto-registered via Plugin.__init_subclass__.
    """

    @abstractmethod
    def export(self, events: list[dict], **kwargs: Any) -> str:
        """Export caption events to the target format string.

        Args:
            events: List of caption event dicts (from Project model).
            **kwargs: Format-specific options.

        Returns:
            Formatted caption string in the target format.
        """
        ...
