"""WebVTT subtitle exporter."""

from __future__ import annotations

from typing import Any

from engine.exporters.base import CaptionExporter


class VttExporter(CaptionExporter):
    """Export captions to WebVTT format."""

    name = "vtt"

    def export(self, events: list[dict], **kwargs: Any) -> str:
        """Export caption events to VTT format string.

        Args:
            events: List of caption event dicts with keys:
                id, start, end, speaker_id, text, off_camera, etc.
            **kwargs: Ignored for VTT.

        Returns:
            VTT-formatted string.
        """
        lines: list[str] = ["WEBVTT", ""]
        for event in events:
            start = self._format_ts(event.get("start", 0.0))
            end = self._format_ts(event.get("end", 0.0))
            text = event.get("text", "")
            lines.append(f"{start} --> {end}")
            lines.append(text)
            lines.append("")
        return "\n".join(lines).rstrip() + "\n"

    @staticmethod
    def _format_ts(seconds: float) -> str:
        """Format seconds to VTT timestamp HH:MM:SS.mmm."""
        hrs = int(seconds // 3600)
        mins = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        ms = int((seconds - int(seconds)) * 1000)
        return f"{hrs:02d}:{mins:02d}:{secs:02d}.{ms:03d}"
