"""Deterministic CI renderer — burns styled captions into video.

Takes a project with caption events and speaker data, generates
styled ASS subtitles implementing the Caption With Intention design
system (V1.0), and burns them into the source video via FFmpeg.

CWI design rules implemented here (Design System V1.0):
    - Read-ahead: the full sentence appears first in white at 90%
      opacity, so viewers can read at their own pace (spec section 2.2.1).
    - Color sync: each word turns the speaker's attribution color the
      moment its sound BEGINS, and stays colored once spoken
      (spec section 2.2.2).
    - Pop: the word undergoing the color change briefly grows by 15%
      and returns to its original size (spec section 2.2.3).
    - Syllable variation: in syllable mode, the current word colors in
      syllable by syllable as heard (spec section 2.2.4).
    - Work area: captions sit in the lower 20% of the frame, baseline
      5% from the bottom edge (spec section 3).
    - Caption box: 90% black box behind the caption text.
    - Off-camera speakers keep their attribution color in italic.

Rendering model: the read-ahead line and every sync overlay line carry
the SAME full sentence with identical per-word geometry tags, so the
colored overlay words land exactly on their white counterparts. Unspoken
words in an overlay line are drawn fully transparent; the white base
shows through beneath them.

Pipeline:
    project -> plain text + tag metadata -> ASS export -> inject ASS tags
    -> inject CWI header + embedded font -> burned video

ASS control tags are injected AFTER AssExporter.export(), because the
exporter escapes backslashes and braces, which would break ASS override
commands. Inline (mid-line) tags use private-use marker characters that
survive the exporter and are replaced during injection.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Optional

from engine.core.ffmpeg import run_ffmpeg
from engine.renderer.styles import (
    BLACK_90_PCT,
    DEFAULT_BASELINE_SIZE_PCT,
    compute_work_area_position,
    hex_to_ass_color,
)
from engine.rules.colors import assign_speaker_color
from engine.rules.profile_loader import get_exceptions_profile
from schemas.project import CaptionEvent, EventType, Project, Speaker

logger = logging.getLogger("caption_with_intention")

# ASS dialogue line prefix
ASS_DIALOGUE_PREFIX = "Dialogue: 0,"

# CWI typeface (spec section 2.3): Roboto Flex variable font.
CWI_FONT_FAMILY = "Roboto Flex"

# Private-use markers delimiting inline tag slots inside dialogue text.
# They survive AssExporter's escaping and are replaced with real ASS
# override tags in _inject_ass_tags.
_MARK_OPEN = ""
_MARK_CLOSE = ""

# Pop animation timing (ms), per spec section 2.2.3: grow 15%, then return.
POP_IN_MS = 120
POP_OUT_MS = 180

def _opacity_to_alpha(opacity: float) -> int:
    """Convert opacity (0.0-1.0) to an ASS alpha byte.

    ASS alpha is inverted: 0x00 is fully opaque, 0xFF fully transparent.
    """
    opacity = max(0.0, min(1.0, opacity))
    return round((1.0 - opacity) * 255)


def _compute_opacity_color(opacity: float, base_hex: str = "#FFFFFF") -> str:
    """Compute an ASS color string from an opacity value.

    Args:
        opacity: Opacity as 0.0-1.0 (e.g., 0.90 = 90% opaque).
        base_hex: Base color in #RRGGBB format.

    Returns:
        ASS color in &HAABBGGRR format (ASS alpha is inverted:
        0x00 opaque, 0xFF transparent).
    """
    alpha = _opacity_to_alpha(opacity)
    hex_color = base_hex.lstrip("#")
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    return f"&H{alpha:02X}{b:02X}{g:02X}{r:02X}"


def _format_pop_scale(scale: float) -> str:
    """Format a pop scale multiplier as an ASS scale tag.

    Args:
        scale: Scale multiplier (e.g., 1.15 = 15% increase).

    Returns:
        ASS \\fscx/\\fscy tag string.
    """
    pct = round(scale * 100)
    return f"\\fscx{pct}\\fscy{pct}"


def _probe_dimensions(source_path: Path) -> tuple[int, int]:
    """Probe source video dimensions, falling back to 1920x1080."""
    try:
        from engine.media.probe import probe_video

        info = probe_video(str(source_path))
        return int(info.get("width", 1920)), int(info.get("height", 1080))
    except Exception:  # noqa: BLE001 - probe failure falls back to 1080p
        return 1920, 1080


def _emit_span(span_tags: list[str], parts: list[str], span_text: str, tag: str) -> None:
    """Append a marked span: tag slot marker followed by the span text."""
    span_tags.append(tag)
    parts.append(f"{_MARK_OPEN}{len(span_tags) - 1}{_MARK_CLOSE}{span_text}")


def _encode_ass_attachment(data: bytes) -> str:
    """Encode binary data in SSA/ASS attachment (uudecode-style) format.

    Each group of 3 bytes becomes 4 characters, each character holding
    6 bits offset by 33. A final partial group emits one more character
    than it has bytes.
    """
    out: list[str] = []
    for i in range(0, len(data), 3):
        chunk = data[i : i + 3]
        padded = chunk + b"\x00" * (3 - len(chunk))
        n = (padded[0] << 16) | (padded[1] << 8) | padded[2]
        chars = [chr(((n >> shift) & 63) + 33) for shift in (18, 12, 6, 0)]
        out.append("".join(chars[: len(chunk) + 1]))
    return "".join(out)


class CwiRenderer:
    """Renders Caption With Intention captions burned into video.

    Takes a project with caption events and speaker data, generates
    styled ASS subtitles with all CWI visual rules applied, and
    burns them into the source video via FFmpeg.

    Pipeline:
        project → ASS styles → ASS subtitles → burned video

    Args:
        project: The project containing events, speakers, and metadata.
        font_path: Path to Roboto Flex variable font (.ttf). If given and
            it exists, the font is embedded into the ASS file and used as
            the caption typeface. If None, falls back to Arial.
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

        screen_width, screen_height = _probe_dimensions(source_path)

        # Build CWI-styled events from project data (plain text + tag metadata)
        cwi_events = self._build_cwi_events(screen_width, screen_height)

        exporter = AssExporter()
        ass_content = exporter.export(cwi_events)

        # Inject ASS override tags into dialogue lines
        ass_content = self._inject_ass_tags(ass_content, cwi_events)

        # Inject CWI-specific header overrides (style, work area, font)
        ass_content = self._inject_cwi_overrides(
            ass_content, screen_width, screen_height
        )

        ass_path = source_path.parent / "captions.cwi.ass"
        ass_path.write_text(ass_content, encoding="utf-8")
        return ass_path

    # ─── Event building ───────────────────────────────────────────

    def _build_cwi_events(
        self, screen_width: int = 1920, screen_height: int = 1080
    ) -> list[dict]:
        """Convert project events to CWI renderable format.

        Each event produces one or more dialogue lines, each with:
        - start, end: timing
        - text: plain caption text (with inline tag markers)
        - type: read_ahead, sync_overlay, sfx, or music
        - tags: dict of ASS override tags injected at the line start
        - span_tags: list of ASS tag strings replacing inline markers

        Generates per dialogue event:
        - Read-ahead line (full sentence, white 90% opacity)
        - Sync overlay lines (one per word/syllable onset; spoken words in
          the speaker's attribution color, current word popping, unspoken
          words transparent so the white read-ahead shows through)
        Plus single lines for SFX and music events.
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

                speaker_color = hex_to_ass_color("#FFFFFF")
                if speaker and toggles.get("attribution_colors_on_off", True):
                    speaker_color = hex_to_ass_color(assign_speaker_color(speaker))

                off_camera = bool(
                    (speaker and speaker.off_camera) or event.off_camera
                )
                italic_tag = (
                    "\\i1"
                    if off_camera and toggles.get("attribution_colors_on_off", True)
                    else ""
                )

                # One caption line per onset interval: spoken words in the
                # speaker color, current word/syllable popping, unspoken
                # words in read-ahead white. A single line is visible at
                # any moment, so colored words never double with white.
                events.extend(
                    self._build_timed_lines(
                        event,
                        speaker_color,
                        screen_height,
                        italic_tag,
                        sync_enabled=toggles.get(
                            "synchronization_color_layer_on_off", True
                        ),
                    )
                )

        return events

    def _compose_word_spans(
        self, event: CaptionEvent, screen_height: int
    ) -> tuple[str, list[dict]]:
        """Compose the sentence text and per-word typography spans.

        The sentence is rebuilt from the word list (single spaces) so the
        read-ahead line and every sync overlay line lay out identically.

        Returns:
            (sentence_text, spans) where each span has: text (including
            the trailing space), size_px, bold tag, width pct, word, index.
        """
        words = event.words
        event_text = event.text or ""

        # Locate each word in the event text so the composed sentence keeps
        # the original spacing and punctuation. Fall back to single-space
        # joining when a word cannot be found.
        positions: list[tuple[int, int]] = []
        cursor = 0
        located = bool(words) and bool(event_text)
        if located:
            for word in words:
                idx = event_text.find(word.text, cursor)
                if idx < 0:
                    located = False
                    break
                positions.append((idx, idx + len(word.text)))
                cursor = idx + len(word.text)

        if located:
            sentence = event_text
            span_texts: list[str] = []
            for i, (start, end) in enumerate(positions):
                seg_start = positions[i - 1][1] if i > 0 else 0
                seg = event_text[seg_start:end]
                if i == len(positions) - 1:
                    seg += event_text[end:]  # trailing punctuation
                span_texts.append(seg)
        else:
            sentence = (
                " ".join(w.text for w in words) if words else event_text
            )
            span_texts = [
                w.text + (" " if i < len(words) - 1 else "")
                for i, w in enumerate(words)
            ]

        spans: list[dict] = []
        for i, word in enumerate(words):
            spans.append(
                {
                    "text": span_texts[i],
                    "size_px": max(
                        1, round(screen_height * word.size_pct / 100.0)
                    ),
                    "bold": "\\b1" if word.weight >= 700 else "\\b0",
                    "width": int(word.width),
                    "word": word,
                    "index": i,
                }
            )
        return sentence, spans

    def _geometry_tags(self, span: dict) -> str:
        """ASS tags pinning a span to its read-ahead geometry."""
        tags = f"\\fs{span['size_px']}{span['bold']}"
        if span["width"] != 100:
            tags += f"\\fscx{span['width']}"
        return tags

    def _pop_tags(self, span: dict, pop_scale: float, duration_ms: float) -> str:
        """Pop animation tags for the word/syllable at its onset.

        Grows the unit by pop_scale (default 15%) over POP_IN_MS, then
        returns it to its original size (spec section 2.2.3).
        """
        if duration_ms <= 0:
            return ""
        t1 = int(min(POP_IN_MS, duration_ms / 2))
        t2 = int(min(POP_IN_MS + POP_OUT_MS, duration_ms))
        if t1 <= 0 or t2 <= t1:
            return ""
        popx = round(span["width"] * pop_scale)
        popy = round(100 * pop_scale)
        return (
            f"\\t(0,{t1},\\fscx{popx}\\fscy{popy})"
            f"\\t({t1},{t2},\\fscx{span['width']}\\fscy100)"
        )

    def _sync_points(self, event: CaptionEvent) -> list[tuple[float, int, Optional[int]]]:
        """Sorted (time, word_index, syllable_index) onset points.

        Syllable onsets are only included for words carrying syllable
        data when the event's syllable_mode is enabled.
        """
        syllable_mode = bool(getattr(event.style, "syllable_mode", False))
        points: list[tuple[float, int, Optional[int]]] = []
        for i, word in enumerate(event.words):
            syllables = word.syllables if (syllable_mode and word.syllables) else None
            if syllables:
                for j, syl in enumerate(syllables):
                    points.append((float(syl.get("start", word.start)), i, j))
            else:
                points.append((word.start, i, None))
        points.sort(key=lambda p: p[0])
        deduped: list[tuple[float, int, Optional[int]]] = []
        for point in points:
            if deduped and abs(point[0] - deduped[-1][0]) < 1e-6:
                continue
            deduped.append(point)
        return deduped

    def _build_timed_lines(
        self,
        event: CaptionEvent,
        speaker_color: str,
        screen_height: int,
        italic_tag: str,
        sync_enabled: bool = True,
    ) -> list[dict]:
        """Build the caption lines for a dialogue event.

        Emits one line per word/syllable onset interval (plus an optional
        pre-onset read-ahead interval). Every line carries the full
        sentence at identical geometry: words already spoken are drawn in
        the speaker's attribution color and stay colored, the word or
        syllable at its onset additionally pops, and unspoken words stay
        in the read-ahead white (spec sections 2.2.1-2.2.4). Exactly one
        line is visible at any moment, so a colored word never doubles
        with white text underneath it.
        """
        sentence, spans = self._compose_word_spans(event, screen_height)
        alpha = _opacity_to_alpha(event.style.read_ahead_opacity)
        white = f"\\c&HFFFFFF&\\alpha&H{alpha:02X}&"

        if not spans:
            tags: dict[str, str] = {"color": white}
            if italic_tag:
                tags["italic"] = italic_tag
            return [
                {
                    "start": event.start,
                    "end": event.end,
                    "text": sentence,
                    "type": "dialogue",
                    "parent_event_id": event.id,
                    "tags": tags,
                }
            ]

        points = self._sync_points(event) if sync_enabled else []
        intervals: list[tuple[float, float, Optional[int], Optional[int]]] = []
        if not points:
            intervals.append((event.start, event.end, None, None))
        else:
            if points[0][0] > event.start:
                # Read-ahead interval before the first word onset.
                intervals.append((event.start, points[0][0], None, None))
            for k, (start, cur_word, cur_syl) in enumerate(points):
                end = points[k + 1][0] if k + 1 < len(points) else event.end
                intervals.append((start, end, cur_word, cur_syl))

        lines: list[dict] = []
        for start, end, cur_word, cur_syl in intervals:
            if end - start <= 0:
                continue
            duration_ms = (end - start) * 1000.0

            span_tags: list[str] = []
            parts: list[str] = []

            def _emit(
                span_text: str,
                tag: str,
                st: list[str] = span_tags,
                pt: list[str] = parts,
            ) -> None:
                _emit_span(st, pt, span_text, tag)

            for i, span in enumerate(spans):
                geometry = self._geometry_tags(span)
                if cur_word is None or i > cur_word:
                    # Unspoken (or pre-onset): read-ahead white.
                    _emit(span["text"], white + geometry)
                elif i < cur_word:
                    # Already spoken: solid speaker color, no pop.
                    _emit(span["text"], f"\\c{speaker_color}&{geometry}")
                else:
                    # Current word at its onset.
                    word = span["word"]
                    syllables = (
                        word.syllables
                        if (cur_syl is not None and word.syllables)
                        else None
                    )
                    if not syllables:
                        tag = (
                            f"\\c{speaker_color}&{geometry}"
                            + self._pop_tags(
                                span, event.style.pop_scale, duration_ms
                            )
                        )
                        _emit(span["text"], tag)
                    else:
                        # Syllable variation: color in syllable by syllable,
                        # unspoken syllables stay read-ahead white.
                        k = span["text"].find(word.text)
                        if k >= 0:
                            prefix = span["text"][:k]
                            suffix = span["text"][k + len(word.text):]
                        else:
                            prefix, suffix = "", ""
                        for j, syl in enumerate(syllables):
                            syl_text = syl.get("text", "")
                            if j == 0:
                                syl_text = prefix + syl_text
                            if j == len(syllables) - 1:
                                syl_text += suffix
                            if j < cur_syl:
                                _emit(
                                    syl_text,
                                    f"\\c{speaker_color}&{geometry}",
                                )
                            elif j == cur_syl:
                                _emit(
                                    syl_text,
                                    f"\\c{speaker_color}&{geometry}"
                                    + self._pop_tags(
                                        span, event.style.pop_scale, duration_ms
                                    ),
                                )
                            else:
                                _emit(syl_text, white + geometry)

            tags = {"font": f"\\fn{CWI_FONT_FAMILY}"}
            if italic_tag:
                tags["italic"] = italic_tag

            lines.append(
                {
                    "start": start,
                    "end": end,
                    "text": "".join(parts),
                    "type": "dialogue",
                    "parent_event_id": event.id,
                    "word_index": cur_word,
                    "syllable_index": cur_syl,
                    "speaker_id": event.speaker_id,
                    "tags": tags,
                    "span_tags": span_tags,
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
        except Exception:  # noqa: BLE001 - unknown profile must not break render
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
            "tags": {
                "color": "\\c&HFFFFFF&\\alpha&H1A&",
                "font": f"\\fn{CWI_FONT_FAMILY}",
            },
        }

    def _build_music_line(self, event: CaptionEvent) -> dict:
        """Build a music dialogue line (white text with music symbol, no word animation)."""
        return {
            "start": event.start,
            "end": event.end,
            "text": event.text or "",
            "type": "music",
            "tags": {
                "color": "\\c&HFFFFFF&\\alpha&H1A&",
                "font": f"\\fn{CWI_FONT_FAMILY}",
            },
        }

    # ─── ASS post-processing ──────────────────────────────────────

    def _inject_ass_tags(
        self, ass_content: str, cwi_events: list[dict]
    ) -> str:
        """Inject ASS override tags into dialogue lines.

        Runs AFTER AssExporter.export() so tags appear as raw ASS commands
        in the final file (not double-escaped).

        Two kinds of tags are injected:
        - Line-prefix tags (event "tags" dict), wrapped in one override
          block at the start of the text.
        - Inline span tags (event "span_tags" list), replacing the
          private-use markers embedded in the text.

        ASS format for dialogue line:
            Dialogue: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text
        """
        marker_re = re.compile(
            re.escape(_MARK_OPEN) + r"(\d+)" + re.escape(_MARK_CLOSE)
        )
        lines = ass_content.split("\n")
        result: list[str] = []
        event_idx = 0

        for line in lines:
            if line.startswith(ASS_DIALOGUE_PREFIX) and event_idx < len(cwi_events):
                evt = cwi_events[event_idx]
                event_idx += 1

                # The text is everything after the 9th comma (index 9)
                parts = line.split(",", 9)
                if len(parts) == 10:
                    text = parts[9]

                    span_tags = evt.get("span_tags")
                    if span_tags:
                        text = marker_re.sub(
                            lambda m, st=span_tags: "{"
                            + st[int(m.group(1))]
                            + "}",
                            text,
                        )

                    prefix = "".join(evt.get("tags", {}).values())
                    if prefix:
                        text = f"{{{prefix}}}" + text

                    line = ",".join(parts[:9]) + "," + text
                result.append(line)
            else:
                result.append(line)

        return "\n".join(result)

    def _build_fonts_section(self) -> str:
        """Build an ASS [Fonts] section embedding the CWI typeface."""
        data = self.font_path.read_bytes()
        encoded = _encode_ass_attachment(data)
        wrapped = "\n".join(
            encoded[i : i + 80] for i in range(0, len(encoded), 80)
        )
        return f"[Fonts]\nfontname: {self.font_path.name}\n{wrapped}\n"

    def _inject_cwi_overrides(
        self,
        ass_content: str,
        screen_width: int,
        screen_height: int,
    ) -> str:
        """Inject CWI-specific ASS header overrides.

        Modifies the ASS header for:
        - Default style: Roboto Flex (embedded when a font file is given),
          baseline size 5% of screen height (spec section 3.2).
        - Work area positioning (lower 20% of frame, baseline 5% from
          the bottom edge; spec section 3.1).
        - Caption box: 90% black box behind the text (BorderStyle=3 with
          BackColour at 90% opacity; spec section 3.3).
        - PlayRes matching the source resolution.
        """
        work_area = compute_work_area_position(
            screen_height=screen_height, screen_width=screen_width
        )
        base_fs = max(
            1, round(screen_height * DEFAULT_BASELINE_SIZE_PCT / 100.0)
        )
        box_padding = max(8, round(base_fs * 0.45))

        font_name = CWI_FONT_FAMILY
        embed_font = bool(self.font_path and self.font_path.exists())
        if not embed_font:
            font_name = "Arial"

        cwi_style = (
            f"Style: Default,{font_name},"
            f"{base_fs},"
            "&H00FFFFFF,"        # PrimaryColour (solid white)
            "&H00FFFFFF,"        # SecondaryColour
            "&H00000000,"        # OutlineColour
            f"{BLACK_90_PCT},"   # BackColour (90% black caption box)
            "0,0,0,0,"           # Bold, Italic, Underline, StrikeOut
            "100,100,0,0,"       # ScaleX, ScaleY, Spacing, Angle
            f"3,{box_padding},0,2,"  # BorderStyle=3 (box), Outline=padding,
                                     # Shadow=0, Alignment=2 (bottom center)
            f"{work_area['margin_left']},{work_area['margin_right']},"
            f"{screen_height - work_area['box_y']},"  # MarginV (from bottom)
            "1"                  # Encoding
        )

        fonts_section = self._build_fonts_section() if embed_font else None

        result: list[str] = []
        fonts_inserted = False
        for line in ass_content.split("\n"):
            if line.startswith("Style: Default"):
                result.append(cwi_style)
            elif line.startswith("PlayResX:"):
                result.append(f"PlayResX: {screen_width}")
            elif line.startswith("PlayResY:"):
                result.append(f"PlayResY: {screen_height}")
            elif line.startswith("[Events]") and fonts_section and not fonts_inserted:
                result.append(fonts_section)
                fonts_inserted = True
                result.append(line)
            else:
                result.append(line)

        return "\n".join(result)

    # ─── FFmpeg ───────────────────────────────────────────────────

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
                f"scale={self.scale[0]}:{self.scale[1]}"
            )
        else:
            vf_filter = f"subtitles={ass_path}"
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
