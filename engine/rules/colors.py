"""Color and palette validation per spec §4.1."""

from __future__ import annotations

import colorsys
from typing import Optional

from schemas.project import Speaker, SpeakerCategory


# V1.0 Design System Colors
MAIN_COLORS: dict[str, str] = {
    "yellow": "#E5E517",
    "blue_cyan": "#17E5E5",
    "red": "#E51717",
    "orange": "#E58017",
    "green": "#17E517",
    "pink": "#E517E5",
}

SUPPORTING_COLORS: list[str] = [
    "#E85C2E",
    "#47C2EB",
    "#EBC247",
    "#5E82ED",
    "#C2EB47",
    "#8C6BED",
    "#82ED5E",
    "#CC6BED",
    "#47EB70",
    "#EB47C2",
    "#5EEDC9",
    "#ED5E82",
]

# Spectrum ordering for distance calculations (approximate hue angles)
SPECTRUM_ORDER = [
    "red",      # 0
    "orange",   # 30
    "yellow",   # 60
    "green",    # 120
    "cyan",     # 180
    "blue",     # 240
    "purple",   # 280
    "pink",     # 330
]


def hex_to_hsv(hex_color: str) -> tuple[float, float, float]:
    """Convert hex color string to HSV tuple."""
    hex_color = hex_color.lstrip("#")
    r = int(hex_color[0:2], 16) / 255.0
    g = int(hex_color[2:4], 16) / 255.0
    b = int(hex_color[4:6], 16) / 255.0
    return colorsys.rgb_to_hsv(r, g, b)


def color_distance_hex(c1: str, c2: str) -> float:
    """Compute perceptual distance between two hex colors using HSV + RGB."""
    h1, s1, v1 = hex_to_hsv(c1)
    h2, s2, v2 = hex_to_hsv(c2)

    # Hue distance (circular)
    hue_dist = min(abs(h1 - h2), 1.0 - abs(h1 - h2))

    # Weighted combined distance
    return (
        100.0 * hue_dist  # hue is most important
        + 10.0 * abs(s1 - s2)
        + 5.0 * abs(v1 - v2)
        + 3.0 * sum((a - b) ** 2 for a, b in zip(hex_to_rgb(c1), hex_to_rgb(c2)))
    )


def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """Convert hex color to RGB tuple."""
    hex_color = hex_color.lstrip("#")
    return (
        int(hex_color[0:2], 16),
        int(hex_color[2:4], 16),
        int(hex_color[4:6], 16),
    )


def generate_minor_color(hue: float, saturation: float = 0.30, brightness: float = 0.90) -> str:
    """Generate a pastel/near-white color per V1.0 spec.

    Args:
        hue: Hue value 0.0-1.0.
        saturation: Fixed at 30% per V1.0.
        brightness: Fixed at 90% per V1.0.

    Returns:
        Hex color string.
    """
    r, g, b = colorsys.hsv_to_rgb(hue % 1.0, saturation, brightness)
    return "#{:02X}{:02X}{:02X}".format(int(r * 255), int(g * 255), int(b * 255))


def generate_minor_palette(count: int = 24) -> list[str]:
    """Generate 24 pastel colors spread evenly across hue spectrum."""
    return [generate_minor_color(i / count) for i in range(count)]


def validate_palette_collision(
    main_speaker_color: str,
    supporting_color: str,
    min_distance: float = 40.0,
) -> bool:
    """Check that a supporting color is sufficiently distant from a main color."""
    distance = color_distance_hex(main_speaker_color, supporting_color)
    return distance >= min_distance


def assign_speaker_color(
    speaker: Speaker,
    assigned: dict[str, str] | None = None,
) -> str:
    """Assign a color to a speaker based on category.

    Args:
        speaker: Speaker object with category and role.
        assigned: Dict of already-assigned speaker IDs to colors (to ensure uniqueness).

    Returns:
        Hex color string.
    """
    if assigned is None:
        assigned = {}

    # Check if already assigned
    for sid, color in assigned.items():
        if sid == speaker.id:
            return color

    if speaker.category == SpeakerCategory.main:
        # Map main speakers to main palette by index
        main_keys = list(MAIN_COLORS.keys())
        idx = hash(speaker.id) % len(main_keys)
        color = MAIN_COLORS[main_keys[idx]]
    elif speaker.category == SpeakerCategory.supporting:
        # Pick supporting color that doesn't conflict with main colors
        main_colors = list(MAIN_COLORS.values())
        for c in SUPPORTING_COLORS:
            if all(validate_palette_collision(c, mc, min_distance=30.0) for mc in main_colors):
                color = c
                break
        else:
            color = SUPPORTING_COLORS[hash(speaker.id) % len(SUPPORTING_COLORS)]
    else:
        # Minor: deterministic pastel based on speaker ID
        hue = (hash(speaker.id) % 1000) / 1000.0
        color = generate_minor_color(hue)

    assigned[speaker.id] = color
    return color


def get_hero_villain_colors() -> tuple[str, str]:
    """Return hero and villain colors (opposite positions in main palette).

    Hero: Yellow (#E5E517), Villain: Blue/Cyan (#17E5E5) — opposite on spectrum.
    """
    return MAIN_COLORS["yellow"], MAIN_COLORS["blue_cyan"]
