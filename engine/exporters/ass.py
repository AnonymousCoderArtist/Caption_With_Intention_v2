"""ASS/SSA subtitle exporter."""

from __future__ import annotations

from typing import Any

from engine.exporters.base import CaptionExporter


class AssExporter(CaptionExporter):
    """Export captions to Advanced SubStation Alpha (ASS/SSA) format."""

    name = "ass"

    # Default ASS style
    _STYLE = "Default: Arial,40,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,1,1,1"

    def export(self, events: list[dict], **kwargs: Any) -> str:
        """Export caption events to ASS format string.

        Args:
            events: List of caption event dicts with keys:
                id, start, end, speaker_id, text, off_camera, etc.
            **kwargs: Format-specific options.

        Returns:
            ASS-formatted string.
        """
        lines: list[str] = [
            "[Script Info]",
            "Title: Caption With Intention",
            "ScriptType: v4.00+",
            "PlayResX: 1920",
            "PlayResY: 1080",
            "",
            "[V4+ Styles]",
            "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
            f"Style: {self._STYLE}",
            "",
            "[Events]",
            "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
        ]

        for event in events:
            start = self._format_ts(event.get("start", 0.0))
            end = self._format_ts(event.get("end", 0.0))
            text = event.get("text", "")
            # Escape backslashes and curly braces for ASS
            text = text.replace("\\", "\\\\").replace("{", "\\{").replace("}", "\\}")
            text = text.replace("\n", "\\N")
            lines.append(
                f"Dialogue: 0,{start},{end},Default,,0,0,0,,{text}"
            )

        lines.append("")
        return "\n".join(lines)

    @staticmethod
    def _format_ts(seconds: float) -> str:
        """Format seconds to ASS timestamp H:MM:SS.cc."""
        hrs = int(seconds // 3600)
        mins = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        cs = int((seconds - int(seconds)) * 100)
        return f"{hrs}:{mins:02d}:{secs:02d}.{cs:02d}"
