"""Deterministic CI renderer — burns styled captions into video.

Takes a project with caption events and speaker data, generates
styled ASS subtitles with all CWI visual rules applied, and
burns them into the source video via FFmpeg.

Pipeline:
    project → plain text + tag metadata → ASS export → inject ASS tags → burned video

ASS control tags (color, font, italic, pop scale) are injected AFTER
the AssExporter produces output, because the exporter escapes all
backslashes which would break ASS override commands.
"""

from __future__ import annotations

import logging
import re
import subprocess
from pathlib import Path
from typing import Any, Optional

from engine.core.ffmpeg import run_ffmpeg
from engine.renderer.styles import (
    BLACK_90_PCT,
    BLACK_SOLID,
    WHITE_90_PCT,
    WHITE_SOLID,
    compute_work_area_position,
    hex_to_ass_color,
)
from engine.rules.profile_loader import get_exceptions_profile
from schemas.project import Project, Speaker, CaptionEvent, EventType

logger = logging.getLogger("caption_with_intention")

# ASS dialogue line prefix
ASS_DIALOGUE_PREFIX = "Dialogue: 0,"


def _compute_opacity_color(opacity: float, base_hex: str = "#E6E6E6") -> str:
    """Compute ASS color string from opacity value.

    Args:
        opacity: Alpha as 0.0-1.0 (e.g., 0.90 = 90% opaque).
        base_hex: Base color in #RRGGBB format (default 90% white).

    Returns:
        ASS color in &HAABBGGRR format.
    """
    alpha = int(opacity * 255)
    hex_color = base_hex.lstrip("#")
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    return f"&H{b:02X}{g:02X}{r:02X}{alpha:02X}"


def _format_pop_scale(scale: float) -> str:
    """Format a pop scale multiplier as an ASS scale tag.

    Args:
        scale: Scale multiplier (e.g., 1.15 = 15% increase).

    Returns:
        ASS \\fscx/\\fscy tag string.
    """
    pct = int(round(scale * 100))
    return f"\\fscx{pct}\\fscy{pct}"


def _build_syllable_overlays(
    event: CaptionEvent,
    speaker: Optional[Speaker],
    speaker_color_ass: str,
    pop_tag: str,
    font_tag: str,
) -> list[dict]:
    """Build per-syllable overlay lines when syllable_mode is enabled.

    Args:
        event: The caption event containing words with syllable data.
        speaker: Speaker object (may be None).
        speaker_color_ass: ASS color string for the speaker.
        pop_tag: ASS pop scale tag (e.g., '\\fscx115\\fscy115').
        font_tag: ASS font tag (e.g., '\\fnRoboto Flex').

    Returns:
        List of syllable overlay line dicts.
    """
    lines: list[dict] = []
    for word in event.words:
        syllables = word.syllables if hasattr(word, "syllables") else None
        if not syllables:
            # Fall back to word-level overlay if no syllable data
            tags: dict[str, str] = {
                "color": speaker_color_ass,
                "font": font_tag,
                "pop": pop_tag,
            }
            if speaker and speaker.off_camera:
                tags["italic"] = "\\i1"
            lines.append(
                {
                    "start": word.start,
                    "end": word.end,
                    "text": word.text,
                    "type": "word_overlay",
                    "word_start": word.start,
                    "word_end": word.end,
                    "word_index": 0,
                    "speaker_id": event.speaker_id,
                    "tags": tags,
                }
            )
            continue

        for syl in syllables:
            syl_text = syl.get("text", "")
            syl_start = syl.get("start", word.start)
            syl_end = syl.get("end", word.end)
            tags: dict[str, str] = {
                "color": speaker_color_ass,
                "font": font_tag,
                "pop": pop_tag,
            }
            if speaker and speaker.off_camera:
                tags["italic"] = "\\i1"
            lines.append(
                {
                    "start": syl_start,
                    "end": syl_end,
                    "text": syl_text,
                    "type": "word_overlay",
                    "word_start": syl_start,
                    "word_end": syl_end,
                    "word_index": -1,
                    "speaker_id": event.speaker_id,
                    "tags": tags,
                }
            )

    return lines


class CwiRenderer:
    """Renders Caption With Intention captions burned into video.

    Takes a project with caption events and speaker data, generates
    styled ASS subtitles with all CWI visual rules applied, and
    burns them into the source video via FFmpeg.

    Pipeline:
        project → ASS styles → ASS subtitles → burned video

    Args:
        project: The project containing events, speakers, and metadata.
        font_path: Path to Roboto Flex variable font (.ttf). If None,
            uses system sans-serif.
        scale: Output video scale (width, height). If None, uses source.
        preserve_audio: Whether to copy audio stream from source.
    """

    def __init__(
        self,
        project: Project,
        font_path: Optional[str | Path] = None,
        scale: Optional[tuple[int, int]] = None,
        preserve_audio: bool = True,
    ) -> None:
        self.project = project
        self.font_path = Path(font_path) if font_path else None
        self.scale = scale
        self.preserve_audio = preserve_audio

    def render(
        self,
        source_path: str | Path,
        output_path: str | Path,
    ) -> Path:
        """Render captions into video.

        Args:
            source_path: Path to source video file.
            output_path: Path for output video (burned-in captions).

        Returns:
            Path to the output video file.
        """
        source_path = Path(source_path)
        output_path = Path(output_path)

        if not source_path.exists():
            raise FileNotFoundError(f"Source video not found: {source_path}")

        logger.info(
            "Rendering %s → %s with %d caption events",
            source_path,
            output_path,
            len(self.project.events),
        )

        # Generate styled ASS subtitles
        ass_path = self._generate_ass(source_path)

        # Build FFmpeg command to burn ASS into video
        cmd = self._build_ffmpeg_command(source_path, ass_path, output_path)

        logger.info("Running FFmpeg: %s", " ".join(cmd[:6]) + "...")
        run_ffmpeg(cmd, timeout=600)

        # Clean up temporary ASS file
        try:
            ass_path.unlink()
        except OSError:
            pass

        logger.info("Render complete: %s", output_path)
        return output_path

    def _generate_ass(self, source_path: Path) -> Path:
        """Generate a CWI-styled ASS subtitle file.

        Args:
            source_path: Source video path (for resolution detection).

        Returns:
            Path to the generated .ass file.
        """
        from engine.exporters.ass import AssExporter

        # Build CWI-styled events from project data (plain text + tag metadata)
        cwi_events = self._build_cwi_events()

        exporter = AssExporter()
        ass_content = exporter.export(cwi_events)

        # Inject ASS override tags into dialogue lines
        ass_content = self._inject_ass_tags(ass_content, cwi_events)

        # Inject CWI-specific header overrides
        ass_content = self._inject_cwi_overrides(ass_content, source_path)

        ass_path = source_path.parent / "captions.cwi.ass"
        ass_path.write_text(ass_content, encoding="utf-8")
        return ass_path

    def _build_cwi_events(self) -> list[dict]:
        """Convert project events to CWI renderable format.

        Each event produces one or more dialogue lines, each with:
        - start, end: timing
        - text: plain caption text (ASS tags injected later)
        - type: read_ahead, word_overlay, sfx, or music
        - tags: dict of ASS override tags to inject into the dialogue line

        Generates multiple ASS dialogue lines per event:
        - Read-ahead line (full sentence, white 90% opacity)
        - Word overlay lines (per word, speaker-colored, with pop animation)
        - SFX line (white text with brackets, no color animation)
        - Music line (white text with music symbol, no word animation)
        """
        speaker_map: dict[str, Speaker] = {
            spk.id: spk for spk in self.project.speakers
        }

        events: list[dict] = []
        for event in self.project.events:
            event_type = (
                event.type.value if isinstance(event.type, EventType) else str(event.type)
            )

            if event_type == "sound_effect":
                events.append(self._build_sfx_line(event))
            elif event_type == "music":
                events.append(self._build_music_line(event))
            else:
                speaker = None
                if event.speaker_id and event.speaker_id in speaker_map:
                    speaker = speaker_map[event.speaker_id]
                elif event.speaker_id:
                    logger.warning(
                        "Event %s references unknown speaker %s",
                        event.id,
                        event.speaker_id,
                    )

                # Apply exception profile to determine rendering behavior
                toggles = self._get_exception_toggles(event)

                speaker_color_ass = "#FFFFFF"
                if speaker and toggles.get("attribution_colors_on_off", True):
                    from engine.rules.colors import assign_speaker_color
                    color = assign_speaker_color(speaker)
                    speaker_color_ass = hex_to_ass_color(color)

                # Read-ahead: use event style opacity (default 90%)
                read_ahead_opacity = event.style.read_ahead_opacity
                read_ahead_color = _compute_opacity_color(read_ahead_opacity)

                events.append(
                    self._build_read_ahead_line(
                        event, speaker, speaker_color_ass, read_ahead_color, toggles
                    )
                )

                # Word overlays: use event style pop_scale (default 1.15)
                if event.words and toggles.get("synchronization_color_layer_on_off", True):
                    pop_tag = _format_pop_scale(event.style.pop_scale)
                    font_tag = "\\fnRoboto Flex"

                    if event.style.syllable_mode:
                        events.extend(
                            _build_syllable_overlays(
                                event, speaker, speaker_color_ass, pop_tag, font_tag
                            )
                        )
                    else:
                        events.extend(
                            self._build_word_overlay_lines(
                                event, speaker, speaker_color_ass, pop_tag, font_tag, toggles
                            )
                        )

        return events

    def _build_read_ahead_line(
        self,
        event: CaptionEvent,
        speaker: Optional[Speaker],
        speaker_color_ass: str,
        read_ahead_color: str,
        toggles: dict[str, bool],
    ) -> dict:
        """Build a read-ahead dialogue line (full sentence, configurable opacity)."""
        tags: dict[str, str] = {}
        tags["color"] = read_ahead_color
        if speaker and speaker.off_camera and toggles.get("attribution_colors_on_off", True):
            tags["italic"] = "\\i1"

        return {
            "start": event.start,
            "end": event.end,
            "text": event.text or "",
            "type": "read_ahead",
            "parent_event_id": event.id,
            "tags": tags,
        }

    def _build_word_overlay_lines(
        self,
        event: CaptionEvent,
        speaker: Optional[Speaker],
        speaker_color_ass: str,
        pop_tag: str,
        font_tag: str,
        toggles: dict[str, bool],
    ) -> list[dict]:
        """Build word overlay dialogue lines (per word, speaker-colored, with pop)."""
        lines: list[dict] = []

        for idx, word in enumerate(event.words):
            tags: dict[str, str] = {
                "color": speaker_color_ass,
                "font": font_tag,
                "pop": pop_tag,
            }
            if speaker and speaker.off_camera and toggles.get("attribution_colors_on_off", True):
                tags["italic"] = "\\i1"

            lines.append(
                {
                    "start": word.start,
                    "end": event.end,
                    "text": word.text,
                    "type": "word_overlay",
                    "word_start": word.start,
                    "word_end": word.end,
                    "word_index": idx,
                    "speaker_id": event.speaker_id,
                    "tags": tags,
                }
            )

        return lines

    def _get_exception_toggles(self, event: CaptionEvent) -> dict[str, bool]:
        """Get rendering toggles for an event based on its exception profile.

        Reads the exception profile from the event and maps it to
        rendering toggles per spec §6.1. If no profile is set, all
        toggles default to True (full CI rendering).

        Returns:
            Dict of toggle name → enabled state.
        """
        default_toggles = {
            "attribution_colors_on_off": True,
            "synchronization_color_layer_on_off": True,
            "pop_animation_on_off": True,
            "variable_size_on_off": True,
            "pitch_weight_mapping_on_off": True,
            "harmonic_width_mapping_on_off": True,
            "sound_effect_animation_on_off": True,
            "caption_box_breakout_permission": False,
            "roman_italic_override": False,
        }

        profile_name = event.exception_profile
        if not profile_name:
            return default_toggles

        try:
            profile = get_exceptions_profile()
            profiles = profile.get("profiles", {})
            profile_config = profiles.get(profile_name, {})
            toggles = profile_config.get("toggles", {})
            # Merge: profile toggles override defaults
            merged = {**default_toggles, **toggles}
            return merged
        except Exception:
            logger.debug(
                "Could not load exception profile %s, using defaults",
                profile_name,
            )
            return default_toggles

    def _build_sfx_line(self, event: CaptionEvent) -> dict:
        """Build an SFX dialogue line (white text with brackets, no color animation)."""
        return {
            "start": event.start,
            "end": event.end,
            "text": event.text or "",
            "type": "sfx",
            "tags": {"color": WHITE_90_PCT, "font": "\\fnRoboto Flex"},
        }

    def _build_music_line(self, event: CaptionEvent) -> dict:
        """Build a music dialogue line (white text with music symbol, no word animation)."""
        return {
            "start": event.start,
            "end": event.end,
            "text": event.text or "",
            "type": "music",
            "tags": {"color": WHITE_90_PCT, "font": "\\fnRoboto Flex"},
        }

    def _inject_ass_tags(
        self, ass_content: str, cwi_events: list[dict]
    ) -> str:
        """Inject ASS override tags into dialogue lines.

        Runs AFTER AssExporter.export() so tags appear as raw ASS commands
        in the final file (not double-escaped).

        Tags are injected at the start of each dialogue's text portion,
        right after the last comma in the Dialogue header.

        ASS format for dialogue line:
            Dialogue: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text

        Tags go before the Text portion. For multiple tags, the order is:
            {color}{font}{pop}{italic}
        """
        lines = ass_content.split("\n")
        result: list[str] = []
        event_idx = 0

        for line in lines:
            if line.startswith(ASS_DIALOGUE_PREFIX) and event_idx < len(cwi_events):
                evt = cwi_events[event_idx]
                event_idx += 1

                tags = evt.get("tags", {})
                if not tags:
                    result.append(line)
                    continue

                # Build the tag prefix in the correct order
                tag_str = "".join(tags.values())
                tag_brace = f"{{{tag_str}}}"

                # Inject tag prefix into the dialogue line
                # Format: Dialogue: 0,start,end,style,name,margins,,effect,text
                # We insert the tag before the text (after the last comma)
                # The text is everything after the 9th comma (index 9)
                parts = line.split(",", 9)
                if len(parts) == 10:
                    # Reconstruct with tag prefix
                    line = ",".join(parts[:9]) + "," + tag_brace + parts[9]
                result.append(line)
            else:
                result.append(line)

        return "\n".join(result)

    def _inject_cwi_overrides(
        self,
        ass_content: str,
        source_path: Path,
    ) -> str:
        """Inject CWI-specific ASS overrides.

        Modifies the ASS header for:
        - Work area positioning (bottom 20%)
        - Caption box background (90% black)
        - Default style with proper scaling
        - Roboto Flex font if available
        """
        lines = ass_content.split("\n")
        result: list[str] = []

        # Get work area position
        screen_height = 1080
        screen_width = 1920
        try:
            from engine.media.probe import probe_video
            info = probe_video(str(source_path))
            screen_width = info.get("width", 1920)
            screen_height = info.get("height", 1080)
        except Exception:
            pass

        work_area = compute_work_area_position(screen_height=screen_height, screen_width=screen_width)
        box_y = work_area["box_y"]

        # Build CWI style
        font_name = "Roboto Flex"
        if self.font_path and self.font_path.exists():
            font_name = self.font_path.name

        cwi_style = (
            f"Default: {font_name},"
            f"{40},"  # font size (will be overridden per-event via ASS tags)
            f"{WHITE_90_PCT},"  # PrimaryColour (90% white for read-ahead)
            f"{WHITE_SOLID},"   # SecondaryColour
            f"{BLACK_90_PCT},"  # OutlineColour (not used)
            f"{BLACK_90_PCT},"  # BackColour (90% black caption box)
            f"0,0,0,0,"          # Bold, Italic, Underline, StrikeOut
            f"100,100,0,0,"      # ScaleX, ScaleY, Spacing, Angle
            f"1,0,0,2,"          # BorderStyle=1 (outline), Outline=0, Shadow=0, Alignment=2 (center)
            f"0,0,{int(box_y)},"  # MarginL, MarginR, MarginV (bottom)
            f"1"                  # Encoding
        )

        for line in lines:
            if line.startswith("Style: Default"):
                result.append(cwi_style)
            elif line.startswith("PlayResX:"):
                result.append(f"PlayResX: {screen_width}")
            elif line.startswith("PlayResY:"):
                result.append(f"PlayResY: {screen_height}")
            else:
                result.append(line)

        return "\n".join(result)

    def _build_ffmpeg_command(
        self,
        source_path: Path,
        ass_path: Path,
        output_path: Path,
    ) -> list[str]:
        """Build the FFmpeg command to burn ASS into video.

        Uses the subtitles filter for ASS rendering and
        stream copy for audio when preserve_audio is True.
        """
        if self.scale:
            vf_filter = (
                f"subtitles={ass_path}:"
                f"force_style='BorderStyle=1,Outline=2,Shadow=0',"
                f"scale={self.scale[0]}:{self.scale[1]}"
            )
        else:
            vf_filter = (
                f"subtitles={ass_path}:"
                f"force_style='BorderStyle=1,Outline=2,Shadow=0'"
            )
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            str(source_path),
            "-vf",
            vf_filter,
        ]

        if self.preserve_audio:
            cmd.extend(["-c:a", "copy"])

        cmd.append(str(output_path))
        return cmd

    def render_ass(
        self,
        source_path: str | Path,
    ) -> str:
        """Generate ASS subtitle content without burning into video.

        Useful for preview or export.

        Args:
            source_path: Source video path (for resolution detection).

        Returns:
            ASS subtitle content as string.
        """
        source_path = Path(source_path)
        ass_path = self._generate_ass(source_path)
        return ass_path.read_text(encoding="utf-8")
