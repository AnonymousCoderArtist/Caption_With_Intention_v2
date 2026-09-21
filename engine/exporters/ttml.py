"""TTML subtitle exporter."""

from __future__ import annotations

from typing import Any

from engine.exporters.base import CaptionExporter


class TtmlExporter(CaptionExporter):
    """Export captions to TTML (XML) format."""

    name = "ttml"

    def export(self, events: list[dict], **kwargs: Any) -> str:
        """Export caption events to TTML XML format string.

        Args:
            events: List of caption event dicts with keys:
                id, start, end, speaker_id, text, off_camera, etc.
            **kwargs: Ignored for TTML.

        Returns:
            TTML XML-formatted string.
        """
        begin_attr = kwargs.get("begin", "00:00:00.000")
        lines: list[str] = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<tt xmlns="http://www.w3.org/ns/ttml" ',
            '    xmlns:tts="http://www.w3.org/ns/ttml#styling">',
            '  <head>',
            '    <styling>',
            '      <style xml:id="caption" tts:fontFamily="sans-serif"/>',
            '    </styling>',
            '  </head>',
            '  <body>',
        ]

        for event in events:
            start = event.get("start", 0.0)
            end = event.get("end", 0.0)
            text = event.get("text", "")
            speaker = event.get("speaker_id", "")
            begin = self._format_ts(start)
            end_ts = self._format_ts(end)

            attrs = f' begin="{begin}" end="{end_ts}"'
            if speaker:
                attrs += f' xml:lang="{speaker}"'
            lines.append(f'    <div{attrs}>')
            lines.append(f"      <p>{text}</p>")
            lines.append("    </div>")

        lines.extend(["  </body>", "</tt>"])
        return "\n".join(lines) + "\n"

    @staticmethod
    def _format_ts(seconds: float) -> str:
        """Format seconds to TTML timestamp HH:MM:SS.mmm."""
        hrs = int(seconds // 3600)
        mins = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        ms = int((seconds - int(seconds)) * 1000)
        return f"{hrs:02d}:{mins:02d}:{secs:02d}.{ms:03d}"
