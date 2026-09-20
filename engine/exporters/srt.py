"""SRT subtitle exporter."""

from __future__ import annotations

from typing import Any

from engine.exporters.base import CaptionExporter


class SrtExporter(CaptionExporter):
    """Export captions to SubRip SRT format."""

    name = "srt"

    def export(self, events: list[dict], **kwargs: Any) -> str:
        """Export caption events to SRT format string.

        Args:
            events: List of caption event dicts with keys:
                id, start, end, speaker_id, text, off_camera, etc.
            **kwargs: Ignored for SRT.

        Returns:
            SRT-formatted string.
        """
        lines: list[str] = []
        for i, event in enumerate(events, 1):
            start = self._format_ts(event.get("start", 0.0))
            end = self._format_ts(event.get("end", 0.0))
            text = event.get("text", "")
            lines.append(str(i))
            lines.append(f"{start} --> {end}")
            lines.append(text)
            lines.append("")
        return "\n".join(lines).rstrip() + "\n"

    @staticmethod
    def _format_ts(seconds: float) -> str:
        """Format seconds to SRT timestamp HH:MM:SS,mmm."""
        hrs = int(seconds // 3600)
        mins = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        ms = int((seconds - int(seconds)) * 1000)
        return f"{hrs:02d}:{mins:02d}:{secs:02d},{ms:03d}"
