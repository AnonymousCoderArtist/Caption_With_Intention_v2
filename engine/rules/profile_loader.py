"""Design system profile loader.

Loads and caches JSON profile files from the design_systems directory.
All design constants are sourced from here — never scattered in code.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from engine.logging.logger import setup_logging

logger = setup_logging()

DESIGN_SYSTEMS_DIR = Path(__file__).resolve().parent.parent.parent / "design_systems" / "caption_with_intention" / "v1.0"

# Cache for loaded profiles
_profile_cache: dict[str, dict] = {}


def load_profile(profile_name: str) -> dict:
    """Load a design system profile by name.

    Args:
        profile_name: Name of the profile file (without .json extension).
                     E.g. "colors", "typography", "synchronization", etc.

    Returns:
        The profile data as a dictionary.

    Raises:
        FileNotFoundError: If the profile file does not exist.
    """
    if profile_name in _profile_cache:
        return _profile_cache[profile_name]

    profile_path = DESIGN_SYSTEMS_DIR / f"{profile_name}.json"
    if not profile_path.exists():
        raise FileNotFoundError(
            f"Design system profile not found: {profile_path}"
        )

    with open(profile_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    _profile_cache[profile_name] = data
    logger.info(
        "Loaded design system profile: %s", profile_name, extra={"stage": "profile_load"}
    )
    return data


def get_main_colors() -> dict:
    """Return the V1.0 main character colors."""
    profile = load_profile("colors")
    return profile.get("main", {})


def get_supporting_colors() -> list:
    """Return the V1.0 supporting colors."""
    profile = load_profile("colors")
    return profile.get("supporting", [])


def get_typography_profile() -> dict:
    """Return typography settings (size ranges, pitch/weight, harmonics/width)."""
    return load_profile("typography")


def get_sync_profile() -> dict:
    """Return synchronization settings (read-ahead, pop, syllable)."""
    return load_profile("synchronization")


def get_elements_profile() -> dict:
    """Return element rules (box, work area, SFX, music)."""
    return load_profile("elements")


def get_exceptions_profile() -> dict:
    """Return exception and override settings."""
    return load_profile("exceptions")


def get_exports_profile() -> dict:
    """Return export settings for sidecar formats."""
    return load_profile("exports")


def get_music_profile() -> dict:
    """Return music descriptor settings."""
    return load_profile("music")


def get_sound_effects_profile() -> dict:
    """Return SFX classification and rendering settings."""
    return load_profile("sound_effects")


def get_full_design_system() -> dict:
    """Load all design system profiles into a single dict."""
    return {
        "profile": load_profile("profile"),
        "colors": get_main_colors(),
        "supporting_colors": get_supporting_colors(),
        "typography": get_typography_profile(),
        "synchronization": get_sync_profile(),
        "elements": get_elements_profile(),
        "exceptions": get_exceptions_profile(),
        "exports": get_exports_profile(),
        "music": get_music_profile(),
        "sound_effects": get_sound_effects_profile(),
    }


def clear_profile_cache() -> None:
    """Clear the profile cache (useful for testing)."""
    _profile_cache.clear()
