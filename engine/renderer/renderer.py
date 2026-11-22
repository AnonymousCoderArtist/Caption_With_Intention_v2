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
import math
import re
import shutil
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
# Mid-word pitch contour (launch film: syllables ride the voice pitch).
# A syllable carrying pitch_hz is offset vertically around the
# 160-200Hz speech baseline (spec section 2.3.8), by up to
# PITCH_RISE_MAX of its type height at the span edges.
PITCH_BASELINE_HZ = 180.0
PITCH_SPAN_HZ = 70.0
PITCH_RISE_MAX = 0.25

# Traveling-wave tail (his rule 2026-11-22: "as the speaker is
# speaking the words come up with synchronisation and then come down
# and the next comes up, like a wave"): a spoken word keeps this
# fraction of its wave offset one word back, then the smaller step
# two words back, then returns to the baseline.
WAVE_TAIL_STEP_1 = 0.6
WAVE_TAIL_STEP_2 = 0.3
# Motion easing (his note 2026-11-22: the render feels stepped next to
# their film's smooth motion). libass \t accel: <1 eases out (fast
# start, soft landing), >1 eases in. Rises ease out; settles and tail
# glides run as S-curves (slow start AND soft landing) via two chained
# transforms, so no motion ever starts or stops abruptly.
EASE_OUT = 0.45
EASE_IN = 2.2
# Tail glide: a spoken word's wave offset decays 60% -> 30% -> flat as
# the following words rise; each step is an eased glide of this length
# (capped to half the interval), not a jump at the next word's onset.
TAIL_GLIDE_MS = 240
# Dock-magnification wave (his rule 2026-11-22: "just like the
# MacBook dock" - each letter's lift falls off smoothly with its
# distance from the spoken position, so the ripple flows letter by
# letter, never in word or syllable chunks): letters within this many
# letter-positions of the speech cursor join the wave crest.
DOCK_SPREAD_LETTERS = 3.0


def _dock_falloff(distance: float) -> float:
    """Smooth cosine-squared falloff from the wave crest, 0 at the
    spread edge - the macOS dock magnification curve."""
    if distance >= DOCK_SPREAD_LETTERS:
        return 0.0
    return math.cos(distance / DOCK_SPREAD_LETTERS * math.pi / 2.0) ** 2


# Sustained loud words (escalation gate, launch film WHOOOOOA): the
# sync keeps sweeping through the word while it is held scaled up
# (user rule 2026-11-22: "the synchronisation of scaled up word
# should also continue"). Letters color in one by one across the
# spoken window so the coloring always tracks the sound's progress.
LETTER_SWEEP_FADE_MS = 40
LETTER_SWEEP_MIN_PER_LETTER_S = 0.06


def _pitch_offset_px(pitch_hz: float, size_px: int) -> float:
    """Vertical pixel offset for a pitch, relative to the baseline."""
    rel = max(-1.0, min(1.0, (pitch_hz - PITCH_BASELINE_HZ) / PITCH_SPAN_HZ))
    return rel * PITCH_RISE_MAX * size_px


def _glide_frz(t0_ms: float, t1_ms: float, theta0: float, theta1: float) -> str:
    """S-curved rotation transform from theta0 to theta1 degrees.

    Two chained transforms - ease-in to the midpoint, then ease-out to
    the target - so the motion starts and lands softly instead of the
    abrupt linear ramp that reads as a jump on film.
    """
    t0 = int(max(0, t0_ms))
    t1 = int(max(t0 + 1, t1_ms))
    if t1 - t0 < 4:
        return f"\\t({t0},{t1},\\frz{theta1:.5f})"
    mid_t = (t0 + t1) // 2
    mid = (theta0 + theta1) / 2.0
    return (
        f"\\t({t0},{mid_t},{EASE_IN},\\frz{mid:.5f})"
        f"\\t({mid_t},{t1},{EASE_OUT},\\frz{theta1:.5f})"
    )


# Spec section 2.4.1: very loud or sudden bursts of speech may break out
# of the captions box. Threshold: a word at or above this type size (% of
# screen height) renders WITHOUT the box.
BREAKOUT_SIZE_PCT = 10.0
# Sound effects break out at a lower size than speech. Launch film
# evidence: the loud [GASP] has no box at ~6.7% of screen height while
# small SFX ([Beep], the small white [GASP]) keep theirs at ~4%.
SFX_BREAKOUT_SIZE_PCT = 6.0

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
        self._advances: Optional[dict[str, float]] = None
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
        # Pre-assign every speaker a distinct palette color for this
        # render; the shared map keeps assignments unique and stable
        # regardless of event order.
        color_assignments: dict[str, str] = {
            spk.id: spk.color
            for spk in self.project.speakers
            if "color" in spk.model_fields_set or spk.color != "#E5E517"
        }
        for spk in self.project.speakers:
            assign_speaker_color(spk, color_assignments)

        events: list[dict] = []
        for event in self.project.events:
            event_type = (
                event.type.value if isinstance(event.type, EventType) else str(event.type)
            )

            if event_type == "sound_effect":
                # Launch film: an SFX made by a character takes that
                # character's attribution color ([GASP] in Slinky's
                # pink); unattributed sounds stay white.
                sfx_color = "&HFFFFFF&"
                sfx_speaker = (
                    speaker_map.get(event.speaker_id) if event.speaker_id else None
                )
                if sfx_speaker and self._get_exception_toggles(event).get(
                    "attribution_colors_on_off", True
                ):
                    sfx_color = hex_to_ass_color(
                        assign_speaker_color(sfx_speaker, color_assignments)
                    )
                events.extend(
                    self._build_sfx_line(
                        event,
                        screen_width,
                        screen_height,
                        sfx_color,
                        margin_v_extra=self._dialogue_stack_height(
                            event, screen_width, screen_height
                        ),
                    )
                )
            elif event_type == "music":
                base_margin_v = screen_height - compute_work_area_position(
                    screen_height=screen_height, screen_width=screen_width
                )["box_y"]
                events.extend(
                    self._build_music_line(
                        event,
                        margin_v=base_margin_v
                        + self._dialogue_stack_height(
                            event, screen_width, screen_height
                        ),
                    )
                )
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
                    speaker_color = hex_to_ass_color(
                        assign_speaker_color(speaker, color_assignments)
                    )

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
                # Spec 2.4.2: a caption too wide for the work area splits
                # into two stacked caption lines, each with its own box.
                sim_lift = self._simultaneous_dialogue_lift(
                    event, screen_width, screen_height
                )
                for child, extra in self._split_event_lines(
                    event, screen_width, screen_height
                ):
                    events.extend(
                        self._build_timed_lines(
                            child,
                            speaker_color,
                            screen_height,
                            italic_tag,
                            sync_enabled=toggles.get(
                                "synchronization_color_layer_on_off", True
                            ),
                            screen_width=screen_width,
                            margin_v_extra=extra + sim_lift,
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
        tags = f"\\fs{span['size_px']}{span['bold']}\\frz0"
        if span["width"] != 100:
            tags += f"\\fscx{span['width']}"
        return tags

    def _box_geometry_tags(
        self, span: dict, base_fs: int, size_px: int = 0
    ) -> str:
        """ASS tags for a box-companion span: constant baseline HEIGHT,
        horizontally matching the word it backs (user rule 2026-11-22:
        the box never grows vertically, it scales horizontally to fit
        big loud words, and the word may poke out top/bottom).

        The box span renders at baseline \\fs (constant height) and
        widens with \\fsp letter-spacing so it still covers the full
        word width. (\\fscy was rejected: this libass also shrinks the
        box horizontally with it.) size_px overrides the word's loud
        size (escalation).
        """
        width = span["width"]
        size = size_px if size_px > 0 else span["size_px"]
        text_w = self._estimate_span_width(span["text"], size, width)
        box_w = self._estimate_span_width(span["text"], base_fs, width)
        fsp = max(0.0, (text_w - box_w) / max(1, len(span["text"])))
        # \\fscx scales the spacing along with the glyphs; compensate.
        if width != 100:
            fsp = fsp * 100.0 / width
        tags = f"\\fs{base_fs}\\b0\\frz0"
        if width != 100:
            tags += f"\\fscx{width}"
        if fsp >= 0.5:
            tags += f"\\fsp{fsp:.1f}"
        return tags

    def _pulse_up_tags(
        self,
        span: dict,
        base_fs: int,
        duration_ms: float,
        first_of_word: bool = True,
        grow_from: int = 0,
        grow_to: int = 0,
        grow_ms: int = 0,
    ) -> str:
        """Scale-up transform from baseline to the word's intonation
        geometry at the spoken moment (loud-word pulse, user rule
        2026-11-22). On later syllable intervals of the same word the
        word is already big, so the geometry is static.

        Sustained-loud escalation (launch film WHOOOOOA): when the
        word keeps growing while held, grow_from/grow_to carry the
        escalated type sizes at this interval's start and at the
        word's end and the ramp continues over grow_ms.
        """
        width_tag = f"\\fscx{span['width']}" if span["width"] != 100 else ""
        if not first_of_word:
            start_fs = grow_from if grow_from > 0 else span["size_px"]
            loud = f"\\fs{start_fs}{span['bold']}{width_tag}"
            if grow_to > start_fs and grow_ms > 0:
                return f"{loud}\\frz0\\t(0,{grow_ms},\\fs{grow_to})"
            return loud + "\\frz0"
        loud = f"\\fs{span['size_px']}{span['bold']}{width_tag}"
        t1 = int(min(POP_IN_MS, max(1.0, duration_ms / 2)))
        tags = f"\\fs{base_fs}\\b0\\frz0\\t(0,{t1},{EASE_OUT},{loud})"
        if grow_to > span["size_px"] and grow_ms > t1:
            tags += f"\\t({t1},{grow_ms},\\fs{grow_to})"
        return tags

    def _pulse_down_tags(
        self, span: dict, base_fs: int, duration_ms: float, from_size: int = 0
    ) -> str:
        """Scale-down transform back to baseline geometry right after
        the word's spoken window (user rule: the loud word comes back
        to its original position/size after it is spoken). from_size
        is the escalated type size reached at the word's end."""
        size = from_size if from_size > 0 else span["size_px"]
        loud = f"\\fs{size}{span['bold']}\\frz0"
        if span["width"] != 100:
            loud += f"\\fscx{span['width']}"
        settle = f"\\fs{base_fs}\\b0"
        if span["width"] != 100:
            settle += "\\fscx100"
        t2 = int(min(POP_OUT_MS, max(1.0, duration_ms / 2)))
        half = max(1, t2 // 2)
        mid = f"\\fs{round((size + base_fs) / 2)}"
        if span["width"] != 100:
            mid += f"\\fscx{round((span['width'] + 100) / 2)}"
        # S-curve: ease in to the midpoint, ease out onto the baseline.
        return (
            f"{loud}\\t(0,{half},{EASE_IN},{mid})"
            f"\\t({half},{t2},{EASE_OUT},{settle})"
        )

    def _pulse_down_box_tags(
        self, span: dict, base_fs: int, duration_ms: float, from_size: int = 0
    ) -> str:
        """Box narrowing transform after a loud word's window (the box
        widened with \\fsp while the word was big). from_size is the
        escalated type size the box currently covers."""
        width = span["width"]
        size = from_size if from_size > 0 else span["size_px"]
        text_w = self._estimate_span_width(span["text"], size, width)
        box_w = self._estimate_span_width(span["text"], base_fs, width)
        fsp = (text_w - box_w) / max(1, len(span["text"]))
        if width != 100:
            fsp = fsp * 100.0 / width
        if fsp < 0.5:
            return ""
        t2 = int(min(POP_OUT_MS, max(1.0, duration_ms / 2)))
        return f"\\t(0,{t2},{EASE_OUT},\\fsp0)"

    def _pop_tags(
        self,
        span: dict,
        pop_scale: float,
        duration_ms: float,
        org_y: int,
        org_distance: float,
        pitch_hz: Optional[float] = None,
    ) -> str:
        """Rise animation tags for the word/syllable at its onset.

        The unit RISES by (pop_scale - 1) of its type height over
        POP_IN_MS and STAYS elevated for the rest of its spoken window;
        the settle back to baseline happens in the following interval
        (see _settle_tags), matching their showcase videos: a word goes
        up when spoken and comes back to its original position right
        after (spec section 2.2.3: "25% elevation"; the words come up,
        they do not scale - size changes belong to the intonation
        pulse).

        libass has no per-span translate, so the rise is a tiny rotation
        around an origin far to the left (org_distance px): the radius is
        near-horizontal, so the arc is a vertical lift to sub-pixel
        precision and the 0.00X° tilt is imperceptible.
        """
        elevation_px = (pop_scale - 1.0) * span["size_px"] if pop_scale > 1.0 else 0.0
        if pitch_hz:
            # Mid-word pitch contour (launch film): the syllable rides
            # the voice pitch on top of the pop elevation.
            elevation_px += _pitch_offset_px(pitch_hz, span["size_px"])
        if duration_ms <= 0 or abs(elevation_px) < 0.5:
            return ""
        t1 = int(min(POP_IN_MS, duration_ms / 2))
        if t1 <= 0:
            return ""
        theta_deg = math.degrees(elevation_px / org_distance)
        # org sits a fixed 100000px left of the line start; org_distance
        # (100000 + half screen width) approximates the span radius.
        return (
            f"\\org(-100000,{org_y})"
            f"\\t(0,{t1},{EASE_OUT},\\frz{theta_deg:.5f})"
        )

    def _settle_tags(
        self,
        span: dict,
        pop_scale: float,
        duration_ms: float,
        org_y: int,
        org_distance: float,
        pitch_hz: Optional[float] = None,
        tail_scale: float = WAVE_TAIL_STEP_1,
    ) -> str:
        """Settle transform for the unit whose window just ended: starts
        at the held elevation and eases back over POP_OUT_MS. The target
        is tail_scale of the word's pitch-wave offset (the traveling
        ripple's first tail step by default, 0 at the end of speech,
        where the whole line relaxes onto the baseline)."""
        if duration_ms <= 0 or pop_scale <= 1.0:
            return ""
        t2 = int(min(POP_OUT_MS, duration_ms / 2))
        if t2 <= 0:
            return ""
        wave_px = (
            _pitch_offset_px(pitch_hz, span["size_px"]) if pitch_hz else 0.0
        )
        elevation_px = (pop_scale - 1.0) * span["size_px"] + wave_px
        theta_start = math.degrees(elevation_px / org_distance)
        # Traveling wave (his rule 2026-11-22: words come up as spoken,
        # then come down and the next rises): the just-spoken word
        # settles onto the first tail step, not its full offset.
        theta_end = math.degrees(wave_px * tail_scale / org_distance)
        return (
            f"\\org(-100000,{org_y})"
            f"\\frz{theta_start:.5f}"
            + _glide_frz(0, t2, theta_start, theta_end)
        )

    def _pitch_hold_tags(
        self,
        span: dict,
        pitch_hz: float,
        org_y: int,
        org_distance: float,
        scale: float = 1.0,
        from_scale: Optional[float] = None,
        glide_ms: float = 0,
    ) -> str:
        """Pitch-contour offset for a spoken unit (launch film: the
        ripple trail). scale < 1 renders the decaying tail of the
        traveling wave. When from_scale is given and differs, the unit
        GLIDES from that level to scale over glide_ms with an S-curve,
        so the tail decays as continuous motion instead of stepping
        down at each word onset. Empty when both ends sit on the
        baseline."""
        offset_px = _pitch_offset_px(pitch_hz, span["size_px"]) * scale
        from_px = (
            _pitch_offset_px(pitch_hz, span["size_px"]) * from_scale
            if from_scale is not None
            else offset_px
        )
        if abs(offset_px) < 0.5 and abs(from_px) < 0.5:
            return ""
        theta_deg = math.degrees(offset_px / org_distance)
        tags = f"\\org(-100000,{org_y})"
        if abs(from_px - offset_px) < 0.5 or glide_ms <= 0:
            return tags + f"\\frz{theta_deg:.5f}"
        theta_from = math.degrees(from_px / org_distance)
        return (
            tags
            + f"\\frz{theta_from:.5f}"
            + _glide_frz(0, glide_ms, theta_from, theta_deg)
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

    def _advance_map(self) -> Optional[dict[str, float]]:
        """Per-character advance widths (em units) from the real font.

        Loaded once from self.font_path via fontTools; None when the
        font or fontTools is unavailable (callers fall back to a rough
        0.5em/char estimate).
        """
        if self._advances is not None:
            return self._advances or None
        self._advances = {}
        try:
            from fontTools.ttLib import TTFont

            if self.font_path and self.font_path.exists():
                font = TTFont(str(self.font_path))
                upem = font["head"].unitsPerEm
                cmap = font.getBestCmap()
                hmtx = font["hmtx"]
                self._advances = {
                    chr(cp): hmtx[name][0] / upem for cp, name in cmap.items()
                }
        except Exception:  # noqa: BLE001 - metrics are best-effort
            logger.debug("Font advance metrics unavailable, using estimate")
        return self._advances or None

    def _estimate_span_width(
        self, span_text: str, size_px: int, width_pct: int
    ) -> float:
        """Estimated rendered width of a span in pixels.

        Uses real font advances when available (exact for the default
        variable-font instance; \\fscx scales advances linearly), else a
        rough 0.5em/char average. The box companion's letter-spacing
        and the two-line split both depend on this matching libass's
        real layout closely.
        """
        advances = self._advance_map()
        if advances:
            ems = sum(advances.get(c, 0.5) for c in span_text)
        else:
            ems = len(span_text) * 0.5
        return ems * size_px * (width_pct / 100.0)

    def _split_event_lines(
        self, event: CaptionEvent, screen_width: int, screen_height: int
    ) -> list[tuple[CaptionEvent, int]]:
        """Split an event into (child event, margin_v_extra) caption lines.

        Returns [(event, 0)] when the caption fits the work area on one
        line. Otherwise splits the words into two groups (spec 2.4.2: no
        more than two lines on a frame); the first group stacks above the
        second by line height plus spacing.
        """
        work_area = compute_work_area_position(
            screen_height=screen_height, screen_width=screen_width
        )
        available = screen_width - work_area["margin_left"] - work_area["margin_right"]
        words = list(event.words)
        if len(words) < 2 or not event.text:
            return [(event, 0)]

        def span_size_px(word) -> int:
            return max(1, round(screen_height * word.size_pct / 100.0))

        widths = [
            self._estimate_span_width(
                word.text + " ", span_size_px(word), int(word.width)
            )
            for word in words
        ]
        if sum(widths) <= available:
            return [(event, 0)]

        # Greedy fill: first line takes as many words as fit.
        used = 0.0
        split = 1
        for i, w in enumerate(widths):
            if used + w > available and i > 0:
                split = i
                break
            used += w
        else:
            split = len(words) - 1
        first, second = words[:split], words[split:]
        if not second:
            return [(event, 0)]

        text1 = " ".join(w.text for w in first)
        text2 = " ".join(w.text for w in second)
        child1 = event.model_copy(update={"words": first, "text": text1})
        child2 = event.model_copy(update={"words": second, "text": text2})
        # Stacking distance must clear the FULL rendered box height
        # (glyph ascent+descent ~1.5x type size, plus box padding on both
        # sides) or libass collision handling shifts a box upward.
        max2 = max(span_size_px(w) for w in second)
        base_fs = max(1, round(screen_height * DEFAULT_BASELINE_SIZE_PCT / 100.0))
        box_padding = max(6, round(base_fs * 0.3))
        # 2.4.2: "adequate spacing between each line" - a slim gap; the
        # lines read as one stacked caption block (their Green Book
        # example has the boxes nearly touching).
        gap = max(2, round(base_fs * 0.12))
        line2_full = round(max2 * 1.5) + 2 * box_padding
        return [(child1, line2_full + gap), (child2, 0)]

    def _build_timed_lines(
        self,
        event: CaptionEvent,
        speaker_color: str,
        screen_height: int,
        italic_tag: str,
        sync_enabled: bool = True,
        screen_width: int = 1920,
        margin_v_extra: int = 0,
        breakout_pct: float = BREAKOUT_SIZE_PCT,
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
        # Spec section 2.4.1 breakout exception: very loud bursts break
        # out of the captions box - render the text with no box at all.
        breakout = any(
            span["size_px"] >= round(screen_height * breakout_pct / 100.0)
            for span in spans
        )
        # Rise origin: far left of the caption baseline (see _pop_tags).
        margin_v = (
            screen_height
            - compute_work_area_position(
                screen_height=screen_height, screen_width=screen_width
            )["box_y"]
            + margin_v_extra
        )
        org_y = screen_height - margin_v
        org_distance = 100000.0 + screen_width / 2.0

        # Letter units per word for the dock wave: whitespace folds into
        # the following letter so elevations index visible glyphs only.
        letter_units: list[list[str]] = []
        letter_base: list[int] = []
        _pos = 0
        for _span in spans:
            _units: list[str] = []
            _pending = ""
            for _ch in _span["text"]:
                if _ch.isspace():
                    _pending += _ch
                    continue
                _units.append(_pending + _ch)
                _pending = ""
            if _pending and _units:
                _units[-1] += _pending
            elif _pending:
                _units.append(_pending)
            letter_units.append(_units)
            letter_base.append(_pos)
            _pos += len(_units)
        letter_count = [len(_u) for _u in letter_units]

        # Per-letter pitch for the wave crest: explicit letter_pitches
        # first, else the letter's syllable pitch, else the word pitch.
        letter_pitch: list[list[Optional[float]]] = []
        for _i, _span in enumerate(spans):
            _w = _span["word"]
            _n = letter_count[_i]
            _lp = _w.letter_pitches or []
            if _lp:
                letter_pitch.append(
                    [_lp[j] if j < len(_lp) else _w.pitch_hz for j in range(_n)]
                )
                continue
            _syls = _w.syllables or []
            if _syls and any(s.get("pitch_hz") for s in _syls):
                _per: list[Optional[float]] = []
                for _s in _syls:
                    _k = sum(1 for c in _s.get("text", "") if not c.isspace())
                    _per.extend([_s.get("pitch_hz")] * _k)
                while len(_per) < _n:
                    _per.append(_per[-1] if _per else _w.pitch_hz)
                letter_pitch.append(_per[:_n])
            else:
                letter_pitch.append([_w.pitch_hz] * _n)
        white = f"\\c&HFFFFFF&\\alpha&H{alpha:02X}&"

        if not spans:
            tags: dict[str, str] = {"color": white}
            if italic_tag:
                tags["italic"] = italic_tag
            return [
                self._build_box_line(
                    event.start, event.end, sentence, [], event.id, margin_v
                ),
                {
                    "start": event.start,
                    "end": event.end,
                    "text": sentence,
                    "type": "dialogue",
                    "parent_event_id": event.id,
                    "tags": tags,
                    "layer": 1,
                    "style": "Default",
                    "margin_v": margin_v,
                },
            ]

        # The box keeps constant baseline height and only grows
        # horizontally around loud words (user rule 2026-11-22).
        box_base_fs = max(
            1, round(screen_height * DEFAULT_BASELINE_SIZE_PCT / 100.0)
        )

        def _baseline_geometry() -> str:
            return f"\\fs{box_base_fs}\\b0\\frz0"

        # Sustained-loud escalation (launch film WHOOOOOA: a loud word
        # keeps growing while it is held). _esc gives a span's type
        # size at absolute time t; words under the loudness gate never
        # grow. The spec 2.3.6 maximum caps the growth.
        esc_rate = event.style.escalation_rate
        esc_max = event.style.escalation_max
        esc_gate_px = round(box_base_fs * event.style.escalation_gate)
        esc_cap_px = max(1, round(screen_height * event.style.maximum_pct / 100.0))

        def _esc(span: dict, t_abs: float) -> int:
            if span["size_px"] < esc_gate_px:
                return span["size_px"]
            offset = t_abs - span["word"].start
            if offset <= 0:
                return span["size_px"]
            mult = min(1.0 + esc_rate * offset, esc_max)
            return min(esc_cap_px, round(span["size_px"] * mult))

        points = self._sync_points(event) if sync_enabled else []
        if points and event.words:
            # Terminal settle point: once the final word's spoken window
            # ends, the caption returns to settled state (user rule: a
            # word comes back to its original position after it is
            # spoken). Without this the final word holds its pop until
            # event end — and for a split caption's FIRST line (whose
            # words end mid-event) that left the line's last word
            # floating above the box for the rest of the event.
            last_spoken_end = max(float(w.end) for w in event.words)
            if points[-1][0] < last_spoken_end < event.end:
                points.append((last_spoken_end, len(event.words), None))
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
        pulsing = bool(points)
        # Off-camera italic appears when each word is SPOKEN, not during
        # read-ahead (user rule 2026-11-22: "the italic bold will appear
        # when it's spoken, not from earlier"). Bold already follows the
        # same rule via the read-ahead baseline geometry.
        ital = "\\i1" if italic_tag else ""
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

            # Box companion is built per interval: the loud word's box
            # section widens only while the word is actually big
            # (spoken-window pulse), then narrows back.
            box_span_tags: list[str] = []
            box_parts: list[str] = []
            for i, span in enumerate(spans):
                if not pulsing or i == cur_word:
                    if pulsing and i == cur_word:
                        # Escalation: the box keeps widening while the
                        # word grows (launch film WHOOOOOA).
                        word_end_t = min(end, span["word"].end)
                        box_from = _esc(span, start)
                        box_to = _esc(span, word_end_t)
                        box_tag = self._box_geometry_tags(
                            span, box_base_fs, size_px=box_from
                        )
                        grow_ms = round((word_end_t - start) * 1000.0)
                        if box_to > box_from and grow_ms > 0:
                            width = span["width"]
                            text_w = self._estimate_span_width(
                                span["text"], box_to, width
                            )
                            box_w = self._estimate_span_width(
                                span["text"], box_base_fs, width
                            )
                            fsp_to = max(0.0, (text_w - box_w) / max(1, len(span["text"])))
                            if width != 100:
                                fsp_to = fsp_to * 100.0 / width
                            t1 = int(
                                min(POP_IN_MS, max(1.0, duration_ms / 2))
                            ) if cur_syl in (None, 0) else 0
                            if fsp_to >= 0.5 and grow_ms > t1:
                                box_tag += f"\\t({t1},{grow_ms},\\fsp{fsp_to:.1f})"
                    else:
                        box_tag = self._box_geometry_tags(span, box_base_fs)
                elif cur_word is not None and i == cur_word - 1:
                    from_size = _esc(span, span["word"].end)
                    box_tag = self._box_geometry_tags(
                        span, box_base_fs, size_px=from_size
                    ) + self._pulse_down_box_tags(
                        span, box_base_fs, duration_ms, from_size=from_size
                    )
                else:
                    box_tag = _baseline_geometry()
                _emit_span(box_span_tags, box_parts, span["text"], box_tag)
            box_text = "".join(box_parts)

            # Dock-magnification wave layout for this interval (his rule
            # 2026-11-22: the ripple flows letter by letter like the
            # MacBook dock). The cursor sweeps the current word's
            # letters over its spoken window; the crest amplitude is the
            # pop elevation plus the word's pitch-wave offset; the lift
            # falls off smoothly with letter distance from the cursor
            # and bleeds a little into the previous word's tail.
            dock_split: dict[int, list[tuple[float, float]]] = {}
            glide_ms = duration_ms
            if pulsing and cur_word is not None and spans:
                pop_scale = event.style.pop_scale

                def _bump_amp(
                    i2: int,
                    j2: Optional[int] = None,
                    pop_scale: float = pop_scale,
                ) -> float:
                    sp2 = spans[i2]
                    amp = 0.0
                    if pop_scale > 1.0:
                        amp += (pop_scale - 1.0) * sp2["size_px"]
                    p2 = (
                        letter_pitch[i2][j2]
                        if j2 is not None and j2 < len(letter_pitch[i2])
                        else None
                    )
                    if p2:
                        amp += _pitch_offset_px(p2, sp2["size_px"])
                    elif sp2["word"].pitch_hz:
                        amp += _pitch_offset_px(
                            sp2["word"].pitch_hz, sp2["size_px"]
                        )
                    return amp

                def _wave_tail_px(i2: int, scale: float) -> float:
                    w2 = spans[i2]["word"]
                    if not w2.pitch_hz:
                        return 0.0
                    return (
                        _pitch_offset_px(w2.pitch_hz, spans[i2]["size_px"])
                        * scale
                    )

                if cur_word >= len(spans):
                    # Terminal: speech over - every letter glides from
                    # its bump/tail elevation back to the baseline.
                    last = len(spans) - 1
                    c_end = letter_base[last] + max(
                        0, letter_count[last] - 1
                    )
                    amp_last = _bump_amp(last)
                    for i2 in range(len(spans)):
                        age = cur_word - i2
                        from_tail = {
                            2: WAVE_TAIL_STEP_1,
                            3: WAVE_TAIL_STEP_2,
                        }.get(age, 0.0)
                        recs = []
                        for j2 in range(letter_count[i2]):
                            p2 = letter_base[i2] + j2
                            bump = _dock_falloff(abs(p2 - c_end)) * (
                                amp_last if age <= 2 else 0.0
                            )
                            recs.append(
                                (_wave_tail_px(i2, from_tail) + bump, 0.0)
                            )
                        if recs and max(
                            abs(a - b) for a, b in recs
                        ) >= 0.5:
                            dock_split[i2] = recs
                    glide_ms = min(TAIL_GLIDE_MS, duration_ms / 2)
                else:
                    _w = spans[cur_word]["word"]
                    _n = letter_count[cur_word]
                    _base = letter_base[cur_word]
                    _dur = max(1e-6, float(_w.end) - float(_w.start))
                    _f0 = min(max((start - float(_w.start)) / _dur, 0.0), 1.0)
                    _f1 = min(
                        max(
                            (min(end, float(_w.end)) - float(_w.start))
                            / _dur,
                            0.0,
                        ),
                        1.0,
                    )
                    c0 = _base + (_f0 * (_n - 1) if _n > 1 else 0.0)
                    c1 = _base + (_f1 * (_n - 1) if _n > 1 else 0.0)
                    fade1 = 1.0
                    if end > float(_w.end):
                        fade1 = max(
                            0.0,
                            1.0
                            - (end - float(_w.end)) * 1000.0 / POP_OUT_MS,
                        )
                    if end > float(_w.end):
                        glide_ms = min(
                            duration_ms,
                            max(
                                POP_OUT_MS,
                                (float(_w.end) - start) * 1000.0,
                            ),
                        )
                    amp_uniform = _bump_amp(cur_word)
                    for i2 in range(cur_word + 1):
                        recs = []
                        for j2 in range(letter_count[i2]):
                            p2 = letter_base[i2] + j2
                            if i2 == cur_word:
                                a0 = _bump_amp(cur_word, j2)
                                a1 = a0 * fade1
                                recs.append(
                                    (
                                        _dock_falloff(abs(p2 - c0)) * a0,
                                        _dock_falloff(abs(p2 - c1)) * a1,
                                    )
                                )
                            else:
                                bump0 = (
                                    _dock_falloff(abs(p2 - c0))
                                    * amp_uniform
                                )
                                bump1 = (
                                    _dock_falloff(abs(p2 - c1))
                                    * amp_uniform
                                    * fade1
                                )
                                age = cur_word - i2
                                first_after = (
                                    i2 == cur_word - 1
                                    and cur_syl in (None, 0)
                                )
                                tail = (
                                    WAVE_TAIL_STEP_1
                                    if age == 1
                                    else WAVE_TAIL_STEP_2
                                    if age == 2
                                    else 0.0
                                )
                                if age == 1:
                                    from_t = (
                                        0.0
                                        if first_after
                                        else WAVE_TAIL_STEP_1
                                    )
                                else:
                                    from_t = {
                                        2: WAVE_TAIL_STEP_1,
                                        3: WAVE_TAIL_STEP_2,
                                    }.get(age, 0.0)
                                recs.append(
                                    (
                                        _wave_tail_px(i2, from_t) + bump0,
                                        _wave_tail_px(i2, tail) + bump1,
                                    )
                                )
                        if i2 == cur_word or (
                            recs
                            and max(abs(a - b) for a, b in recs) >= 0.5
                        ):
                            dock_split[i2] = recs

            for i, span in enumerate(spans):
                if not pulsing:
                    # Sync disabled: static intonation geometry (fallback).
                    _emit(span["text"], white + self._geometry_tags(span))
                    continue
                if i in dock_split:
                    # Dock-magnification emission: per-letter elevation
                    # (his rule 2026-11-22: like the MacBook dock - each
                    # letter's lift falls off smoothly with its distance
                    # from the spoken position, so the ripple flows
                    # letter by letter, never in syllable chunks).
                    recs = dock_split[i]
                    units = letter_units[i]
                    if i == cur_word:
                        size_tags = self._pulse_up_tags(
                            span,
                            box_base_fs,
                            duration_ms,
                            first_of_word=cur_syl in (None, 0),
                            grow_from=_esc(span, start),
                            grow_to=_esc(span, min(end, span["word"].end)),
                            grow_ms=round(
                                (min(end, span["word"].end) - start) * 1000.0
                            ),
                        )
                    elif cur_word is not None and i == cur_word - 1:
                        size_tags = self._pulse_down_tags(
                            span,
                            box_base_fs,
                            duration_ms,
                            from_size=_esc(span, span["word"].end),
                        )
                    else:
                        size_tags = _baseline_geometry()
                    runs: list[list] = []
                    for j2, chunk in enumerate(units):
                        e0, e1 = recs[j2] if j2 < len(recs) else (0.0, 0.0)
                        if i == cur_word:
                            # Letter-granular sync (their film colors
                            # letter by letter): the letter joins the
                            # spoken color at the moment the cursor
                            # reaches it, with a short fade.
                            n_l = len(units)
                            w_dur = max(
                                1e-6,
                                float(span["word"].end)
                                - float(span["word"].start),
                            )
                            t_on = float(span["word"].start) + (
                                (j2 / n_l) * w_dur if n_l > 1 else 0.0
                            )
                            t_rel = (t_on - start) * 1000.0
                            if t_on < start - 1e-9:
                                tag = f"\\c{speaker_color}&{ital}" + size_tags
                            elif t_rel >= duration_ms:
                                tag = white + size_tags
                            else:
                                tag = white + size_tags + (
                                    f"\\t({int(t_rel)},"
                                    f"{int(t_rel + LETTER_SWEEP_FADE_MS)},"
                                    f"\\c{speaker_color}&\\alpha&H00&{ital})"
                                )
                        else:
                            tag = f"\\c{speaker_color}&{ital}" + size_tags
                        th0 = math.degrees(e0 / org_distance)
                        th1 = math.degrees(e1 / org_distance)
                        if abs(e0) >= 0.5 or abs(e1) >= 0.5:
                            tag += f"\\org(-100000,{org_y})\\frz{th0:.5f}"
                            if abs(th1 - th0) > 1e-6:
                                tag += _glide_frz(0, glide_ms, th0, th1)
                        if runs and runs[-1][1] == tag:
                            runs[-1][0] += chunk
                        else:
                            runs.append([chunk, tag])
                    for chunk, tag in runs:
                        _emit(chunk, tag)
                    continue
                # Unsplit words: word-level size geometry as before.
                if i == cur_word:
                    # The spoken moment: scale up from baseline to the
                    # word's intonation geometry right at its onset
                    # (user rules 2026-11-22: "pop/scale up when it's
                    # spoken, not from before").
                    word_end_t = min(end, span["word"].end)
                    geometry = self._pulse_up_tags(
                        span,
                        box_base_fs,
                        duration_ms,
                        first_of_word=cur_syl in (None, 0),
                        grow_from=_esc(span, start),
                        grow_to=_esc(span, word_end_t),
                        grow_ms=round((word_end_t - start) * 1000.0),
                    )
                elif cur_word is not None and i == cur_word - 1:
                    # Just finished: scale back down to its original
                    # size/weight/width and settle back to its spot on
                    # the pitch wave ("comes back to og position after
                    # it's spoken"; the wave trail persists).
                    geometry = self._pulse_down_tags(
                        span,
                        box_base_fs,
                        duration_ms,
                        from_size=_esc(span, span["word"].end),
                    ) + self._settle_tags(
                        span,
                        event.style.pop_scale,
                        duration_ms,
                        org_y,
                        org_distance,
                        pitch_hz=span["word"].pitch_hz,
                        tail_scale=(
                            0.0
                            if cur_word >= len(spans)
                            else WAVE_TAIL_STEP_1
                        ),
                    )
                else:
                    geometry = _baseline_geometry()
                if cur_word is None or i > cur_word:
                    # Unspoken (or pre-onset): read-ahead white, roman.
                    _emit(span["text"], white + geometry)
                elif i < cur_word:
                    word = span["word"]
                    if i == cur_word - 1 and cur_syl in (None, 0):
                        # Just finished: geometry carries the pulse-down
                        # + settle-to-wave transition for this interval.
                        _emit(
                            span["text"],
                            f"\\c{speaker_color}&{ital}{geometry}",
                        )
                    else:
                        # Already spoken: the traveling wave's tail.
                        # One word back holds 60% of its wave offset,
                        # two words back glides 60% -> 30%, three words
                        # back glides 30% -> flat; at the end of speech
                        # every word glides back to the baseline (his
                        # rule 2026-11-22: the ripple travels with the
                        # speech; his smoothness note: the tail decays
                        # as continuous motion, never stepped jumps).
                        terminal = cur_word >= len(spans)
                        age = cur_word - i
                        if terminal:
                            tail = 0.0
                        else:
                            tail = (
                                WAVE_TAIL_STEP_1
                                if age == 1
                                else WAVE_TAIL_STEP_2
                                if age == 2
                                else 0.0
                            )
                        from_tail = {
                            2: WAVE_TAIL_STEP_1,
                            3: WAVE_TAIL_STEP_2,
                        }.get(age)
                        tail_glide_ms = min(TAIL_GLIDE_MS, duration_ms / 2)
                        syl_mode = bool(
                            getattr(event.style, "syllable_mode", False)
                        )
                        syllables = (
                            word.syllables
                            if (syl_mode and word.syllables)
                            else None
                        )
                        if tail <= 0.0 and not from_tail:
                            _emit(
                                span["text"],
                                f"\\c{speaker_color}&{ital}{geometry}",
                            )
                        elif syllables:
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
                                p = syl.get("pitch_hz")
                                hold = (
                                    self._pitch_hold_tags(
                                        span,
                                        p,
                                        org_y,
                                        org_distance,
                                        scale=tail,
                                        from_scale=from_tail,
                                        glide_ms=tail_glide_ms,
                                    )
                                    if p
                                    else ""
                                )
                                _emit(
                                    syl_text,
                                    f"\\c{speaker_color}&{ital}{geometry}"
                                    + hold,
                                )
                        else:
                            p = word.pitch_hz
                            hold = (
                                self._pitch_hold_tags(
                                    span,
                                    p,
                                    org_y,
                                    org_distance,
                                    scale=tail,
                                    from_scale=from_tail,
                                    glide_ms=tail_glide_ms,
                                )
                                if p
                                else ""
                            )
                            _emit(
                                span["text"],
                                f"\\c{speaker_color}&{ital}{geometry}" + hold,
                            )
                else:
                    # Current word without letter data (no units): plain
                    # onset coloring (defensive; dock_split covers all
                    # real words).
                    _emit(
                        span["text"],
                        f"\\c{speaker_color}&{ital}{geometry}",
                    )

            tags = {"font": f"\\fn{CWI_FONT_FAMILY}"}

            if not breakout:
                lines.append(
                    self._build_box_line(
                        start, end, box_text, box_span_tags, event.id, margin_v
                    )
                )
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
                    "layer": 1,
                    "style": "Default",
                    "margin_v": margin_v,
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

    def _build_box_line(
        self,
        start: float,
        end: float,
        text: str,
        span_tags: list[str],
        parent_event_id: str,
        margin_v: int | None = None,
    ) -> dict:
        """Build the caption-box companion for a caption line.

        Same text and geometry as the caption it backs, rendered with the
        CwiBox style: near-invisible text over a continuous 90% black box
        (BorderStyle=3) that hugs the full line and stays constant while
        words pop (spec section 2.4.1).
        """
        line = {
            "start": start,
            "end": end,
            "text": text,
            "type": "box",
            "parent_event_id": parent_event_id,
            "tags": {"font": f"\\fn{CWI_FONT_FAMILY}"},
            "span_tags": list(span_tags),
            "layer": 0,
            "style": "CwiBox",
        }
        if margin_v is not None:
            line["margin_v"] = margin_v
        return line

    def _dialogue_stack_height(
        self, event: CaptionEvent, screen_width: int, screen_height: int
    ) -> int:
        """margin_v offset (px) lifting a non-dialogue event above dialogue.

        Launch film layout: with SFX and dialogue on screen together the
        SFX sits ABOVE the dialogue line ([Beep] above the spoken line).
        libass collision handling does not apply to lines with explicit
        MarginV, so the offset is computed directly: the full rendered
        height of every overlapping dialogue caption line (glyph box
        ~1.5x type size + box padding on both sides) plus the inter-line
        gap. 0 when no dialogue overlaps the event.
        """
        base_fs = max(1, round(screen_height * DEFAULT_BASELINE_SIZE_PCT / 100.0))
        box_padding = max(6, round(base_fs * 0.3))
        gap = max(2, round(base_fs * 0.12))
        top = 0
        for other in self.project.events:
            if other is event:
                continue
            other_type = (
                other.type.value
                if isinstance(other.type, EventType)
                else str(other.type)
            )
            if other_type in ("sound_effect", "music"):
                continue
            if not (other.start < event.end and other.end > event.start):
                continue
            # Simultaneous speakers already stack above each other; the
            # SFX/music line must clear the whole stack (user rule
            # 2026-11-22: SFX is always the top line).
            stack = self._simultaneous_dialogue_lift(
                other, screen_width, screen_height
            )
            for child, child_extra in self._split_event_lines(
                other, screen_width, screen_height
            ):
                if child.words:
                    max_sz = max(
                        round(screen_height * w.size_pct / 100.0)
                        for w in child.words
                    )
                else:
                    max_sz = base_fs
                top = max(
                    top,
                    stack + child_extra + round(max_sz * 1.5) + 2 * box_padding,
                )
        return top + gap if top else 0

    def _simultaneous_dialogue_lift(
        self, event: CaptionEvent, screen_width: int, screen_height: int
    ) -> int:
        """margin_v offset lifting a dialogue event above EARLIER-starting
        overlapping dialogue (user rule 2026-11-22: when several
        characters speak at once, each keeps their own color and the
        later speaker stacks above the earlier one; the very top line
        stays reserved for SFX). 0 when nothing overlaps."""
        base_fs = max(1, round(screen_height * DEFAULT_BASELINE_SIZE_PCT / 100.0))
        box_padding = max(6, round(base_fs * 0.3))
        gap = max(2, round(base_fs * 0.12))
        events_list = list(self.project.events)
        my_idx = next(
            (i for i, other in enumerate(events_list) if other is event), 0
        )
        lift = 0
        for idx, other in enumerate(events_list):
            if other is event:
                continue
            other_type = (
                other.type.value
                if isinstance(other.type, EventType)
                else str(other.type)
            )
            if other_type != "dialogue":
                continue
            if not (other.start < event.end and other.end > event.start):
                continue
            # Only speakers who started earlier (project order breaks
            # ties) push this line up.
            if other.start > event.start:
                continue
            if other.start == event.start and idx > my_idx:
                continue
            for child, child_extra in self._split_event_lines(
                other, screen_width, screen_height
            ):
                if child.words:
                    max_sz = max(
                        round(screen_height * w.size_pct / 100.0)
                        for w in child.words
                    )
                else:
                    max_sz = base_fs
                lift += (
                    child_extra + round(max_sz * 1.5) + 2 * box_padding + gap
                )
        return lift

    def _build_sfx_line(
        self,
        event: CaptionEvent,
        screen_width: int,
        screen_height: int,
        sfx_color: str = "&HFFFFFF",
        margin_v_extra: int = 0,
    ) -> list[dict]:
        """Build SFX dialogue lines (bracketed text).

        Spec section 2.4.4: sound effects appear in brackets and follow
        the CWI animation rules - loud sounds increase in type size and
        the words rise in sync with the sound. So when the event carries
        word timings, SFX goes through the same timed-lines path as
        dialogue, with the attribution color of the character who makes
        the sound (launch film: [GASP] in Slinky's pink), else white.

        Launch film layout: with SFX and dialogue on screen together the
        SFX sits ABOVE the dialogue line (margin_v_extra lifts it; SFX
        boxes draw at layer 2 and SFX text at layer 3 so the pair stays
        above the dialogue's layers 0/1).
        """
        text = event.text or ""
        if text and not text.lstrip().startswith("["):
            text = f"[{text.strip()}]"
            if event.text:
                event = event.model_copy(update={"text": text})
        if event.words:
            lines = self._build_timed_lines(
                event,
                sfx_color,
                screen_height,
                "",
                sync_enabled=True,
                screen_width=screen_width,
                margin_v_extra=margin_v_extra,
                breakout_pct=SFX_BREAKOUT_SIZE_PCT,
            )
            for line in lines:
                if line.get("style") == "CwiBox":
                    line["layer"] = 2
                else:
                    line["type"] = "sfx"
                    line["layer"] = 3
            return lines
        margin_v = (
            screen_height
            - compute_work_area_position(
                screen_height=screen_height, screen_width=screen_width
            )["box_y"]
            + margin_v_extra
        )
        box = self._build_box_line(
            event.start, event.end, text, [], event.id, margin_v
        )
        box["layer"] = 2
        return [
            box,
            {
                "start": event.start,
                "end": event.end,
                "text": text,
                "type": "sfx",
                "margin_v": margin_v,
                "tags": {
                    "color": f"\\c{sfx_color}&\\alpha&H1A&",
                    "font": f"\\fn{CWI_FONT_FAMILY}",
                },
                "layer": 3,
                "style": "Default",
            },
        ]

    def _build_music_line(
        self, event: CaptionEvent, margin_v: int
    ) -> list[dict]:
        """Build a music dialogue line (white text with music symbol, no word animation).

        Like SFX, music is non-dialogue and stacks above dialogue lines
        (margin_v lifts it; box layer 2, text layer 3).
        """
        # Spec section 2.4.5: the music symbol goes on either side of the
        # description (white, unanimated). Brackets are the SFX convention
        # (2.4.4), so strip them when wrapping with the symbol.
        text = (event.text or "").strip()
        if text and "\u266a" not in text:
            text = text.strip("[] ")
            text = f"\u266a {text} \u266a"
        box = self._build_box_line(
            event.start, event.end, text, [], event.id, margin_v
        )
        box["layer"] = 2
        return [
            box,
            {
                "start": event.start,
                "end": event.end,
                "text": text,
                "type": "music",
                "margin_v": margin_v,
                "tags": {
                    "color": "\\c&HFFFFFF&\\alpha&H1A&",
                    "font": f"\\fn{CWI_FONT_FAMILY}",
                },
                "layer": 3,
                "style": "Default",
            },
        ]

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
                    parts[0] = f"Dialogue: {evt.get('layer', 0)}"
                    parts[3] = evt.get("style", "Default")
                    if "margin_v" in evt:
                        parts[7] = str(evt["margin_v"])
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
        # Use the family name, not the file name: libass matches the
        # attachment against style/span font names (\fnRoboto Flex).
        return f"[Fonts]\nfontname: {CWI_FONT_FAMILY}\n{wrapped}\n"

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
        box_padding = max(6, round(base_fs * 0.3))

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
            f"{BLACK_90_PCT},"   # BackColour (unused at BorderStyle=1)
            "0,0,0,0,"           # Bold, Italic, Underline, StrikeOut
            "100,100,0,0,"       # ScaleX, ScaleY, Spacing, Angle
            "1,0,0,2,"           # BorderStyle=1 (no box on the text layer),
                                 # Outline=0, Shadow=0, Alignment=2 (bottom center)
            f"{work_area['margin_left']},{work_area['margin_right']},"
            f"{screen_height - work_area['box_y']},"  # MarginV (from bottom)
            "1"                  # Encoding
        )

        # Box layer style: near-invisible text (alpha FE) so libass still
        # draws the BorderStyle=3 box, as ONE continuous 90% black box
        # hugging the line (spec section 2.4.1).
        cwi_box_style = (
            f"Style: CwiBox,{font_name},"
            f"{base_fs},"
            "&HFEFFFFFF,"        # PrimaryColour (near-invisible text)
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
                result.append(cwi_box_style)
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

    @staticmethod
    def _ass_escape_filter_path(path: Path) -> str:
        """Escape a path for use inside an ffmpeg filtergraph option."""
        text = str(path)
        return (
            text.replace("\\", "\\\\")
            .replace(":", "\\:")
            .replace("'", "\\'")
        )

    def _stage_fontsdir(self, ass_path: Path) -> str | None:
        """Copy the CWI font next to the ASS file for libass fontsdir use.

        Returns the filter-escaped fontsdir path, or None when no font
        file is configured.
        """
        if not self.font_path or not self.font_path.exists():
            return None
        fonts_dir = ass_path.parent / ".cwi-fonts"
        fonts_dir.mkdir(parents=True, exist_ok=True)
        target = fonts_dir / self.font_path.name
        if not target.exists():
            shutil.copy2(self.font_path, target)
        return self._ass_escape_filter_path(fonts_dir)

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
        # Stage the CWI typeface into a fontsdir so libass picks up the
        # real Roboto Flex even when it ignores [Fonts] attachments
        # (this ffmpeg/libass build does).
        fontsdir = self._stage_fontsdir(ass_path)
        fontsdir_opt = f":fontsdir={fontsdir}" if fontsdir else ""
        if self.scale:
            vf_filter = (
                f"subtitles={ass_path}{fontsdir_opt},"
                f"scale={self.scale[0]}:{self.scale[1]}"
            )
        else:
            vf_filter = f"subtitles={ass_path}{fontsdir_opt}"
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
