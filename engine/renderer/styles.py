"""CWI style computation for rendering engine.

Maps project data (speakers, events, typography settings) to renderable
styles: colors, sizes, positions, effects per caption event.
"""

from __future__ import annotations

from typing import Optional

from engine.rules.colors import (
    MAIN_COLORS,
    SUPPORTING_COLORS,
    assign_speaker_color,
)
from schemas.project import Speaker, SpeakerCategory


# ─── Render-time constants ─────────────────────────────────────────

DEFAULT_WORK_AREA_BOTTOM_PCT = 20.0   # lower 20% of frame
DEFAULT_CAPTION_BOX_OPACITY = 0.90    # 90% black
DEFAULT_READ_AHEAD_OPACITY = 0.90     # 90% white
DEFAULT_POP_SCALE = 1.15              # 15% increase
DEFAULT_BASELINE_SIZE_PCT = 5.0       # baseline type size
DEFAULT_MIN_SIZE_PCT = 3.0
DEFAULT_MAX_SIZE_PCT = 12.0

# ASS color format: &HAABBGGRR (A=alpha, B=blue, G=green, R=red)
# White at 90% opacity: alpha=0xE6 (90%), RGB=white
WHITE_90_PCT = "&HE6E6E6E6"  # 90% opaque white in ASS BGR format (8-digit)
WHITE_SOLID = "&HFFFFFFFF"  # Solid white (secondary colour, 8-digit)
BLACK_90_PCT = "&HDE000000"  # 90% opaque black in ASS BGR format (8-digit)
BLACK_SOLID = "&H00000000"  # Solid black (8-digit)


def hex_to_ass_color(hex_color: str) -> str:
    """Convert hex color (#RRGGBB) to ASS BGR color format (&HAABBGGRR).

    ASS uses BGR order (not RGB) and no alpha in the standard format.
    Alpha is controlled separately via the BackColour style property.
    """
    hex_color = hex_color.lstrip("#")
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    # ASS uses BGR order
    return f"&H{b:02X}{g:02X}{r:02X}"


def speaker_color_to_ass(speaker: Speaker) -> str:
    """Get the ASS color code for a speaker.

    Uses the speaker's already-assigned color (not re-assigning).
    """
    return hex_to_ass_color(speaker.color)


def compute_word_style(
    loudness: float = 0.5,
    pitch_hz: Optional[float] = None,
    low_harmonic: float = 0.5,
    high_harmonic: float = 0.5,
    minimum_pct: float = DEFAULT_MIN_SIZE_PCT,
    baseline_pct: float = DEFAULT_BASELINE_SIZE_PCT,
    maximum_pct: float = DEFAULT_MAX_SIZE_PCT,
    baseline_weight: int = 400,
    pop_scale: float = DEFAULT_POP_SCALE,
    italic: bool = False,
) -> dict:
    """Compute the full visual style for a single word.

    Args:
        loudness: Normalized loudness 0-1.
        pitch_hz: Estimated pitch in Hz.
        low_harmonic: Low harmonic energy 0-1.
        high_harmonic: High harmonic energy 0-1.
        minimum_pct: Minimum type size % of screen height.
        baseline_pct: Baseline type size % of screen height.
        maximum_pct: Maximum type size % of screen height.
        baseline_weight: Baseline font weight.
        pop_scale: Pop motion scale multiplier (e.g. 1.15 = 15% increase).
        italic: Whether the text should be italic.

    Returns:
        Dict with size_pct, weight, width, italic, pop_size_pct values.
    """
    from engine.typography.mapping import (
        volume_to_size,
        pitch_to_weight,
        harmonics_to_width,
    )

    size_pct = volume_to_size(
        loudness, minimum_pct, baseline_pct, maximum_pct,
    )
    weight = pitch_to_weight(pitch_hz, baseline_weight)
    width = harmonics_to_width(low_harmonic, high_harmonic)
    pop_size_pct = size_pct * pop_scale

    return {
        "size_pct": round(size_pct, 2),
        "weight": weight,
        "width": width,
        "italic": italic,
        "pop_size_pct": round(pop_size_pct, 2),
    }


def compute_work_area_position(
    screen_height: int = 1080,
    screen_width: int = 1920,
    bottom_margin_pct: float = 5.0,
    side_margin_pct: float = 2.5,
) -> dict:
    """Compute work area positioning for caption box.

    Returns pixel coordinates for the caption box and work area.

    Returns:
        Dict with work_area_top, work_area_bottom, box_y, margins.
    """
    work_area_top = screen_height * (1.0 - DEFAULT_WORK_AREA_BOTTOM_PCT / 100.0)
    work_area_bottom = screen_height
    box_y = work_area_bottom - (screen_height * bottom_margin_pct / 100.0)
    margin_left = screen_width * side_margin_pct / 100.0
    margin_right = screen_width * side_margin_pct / 100.0

    return {
        "work_area_top": int(work_area_top),
        "work_area_bottom": int(work_area_bottom),
        "box_y": int(box_y),
        "margin_left": int(margin_left),
        "margin_right": int(margin_right),
        "bottom_margin_pct": bottom_margin_pct,
        "side_margin_pct": side_margin_pct,
    }
