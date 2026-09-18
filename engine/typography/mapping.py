"""Typography mapping engine per spec §2.3 and §4.3.

Maps acoustic properties to typographic properties:
- Volume → type size (3%–12% of screen height, 5% baseline)
- Pitch → weight (80-160 Hz heavy, 160-200 Hz neutral, 200+ light)
- Harmonics → width (low freq dominant → wide, high freq → narrow)
"""

from __future__ import annotations

from typing import Optional

from engine.rules.profile_loader import get_typography_profile


def volume_to_size(
    loudness: float,
    minimum_pct: float = 3.0,
    baseline_pct: float = 5.0,
    maximum_pct: float = 12.0,
) -> float:
    """Map volume/loudness to type size percentage of screen height.

    Args:
        loudness: Normalized loudness value 0.0-1.0.
        minimum_pct: Minimum type size (% of screen height).
        baseline_pct: Baseline type size (normal speech).
        maximum_pct: Maximum type size.

    Returns:
        Type size as percentage of screen height.
    """
    # Linear mapping: louder → larger
    size = minimum_pct + loudness * (maximum_pct - minimum_pct)
    return max(minimum_pct, min(maximum_pct, size))


def pitch_to_weight(
    pitch_hz: Optional[float],
    baseline_weight: int = 400,
) -> int:
    """Map fundamental frequency to font weight.

    Args:
        pitch_hz: Estimated pitch in Hz, or None.
        baseline_weight: Font weight for baseline range (400).

    Returns:
        Font weight value (e.g., 100-900).
    """
    if pitch_hz is None:
        return baseline_weight

    if pitch_hz < 80:
        # Very low pitch — heavy/bold
        return 700
    elif pitch_hz < 160:
        # Low pitch — moderately heavy
        # Linear interpolation from 700 (at 80Hz) to 500 (at 160Hz)
        t = (pitch_hz - 80) / (160 - 80)
        return int(700 - t * 200)
    elif pitch_hz <= 200:
        # Baseline range — neutral Regular 400
        return baseline_weight
    elif pitch_hz <= 300:
        # High pitch — lighter
        t = (pitch_hz - 200) / (300 - 200)
        return int(baseline_weight - t * 200)
    else:
        # Very high pitch — lightest
        return max(100, baseline_weight - 300)


def harmonics_to_width(
    low_harmonic_energy: float,
    high_harmonic_energy: float,
    min_width: int = 50,
    max_width: int = 150,
) -> int:
    """Map harmonic content to font width axis.

    Args:
        low_harmonic_energy: Energy in low-frequency harmonics (0-1).
        high_harmonic_energy: Energy in high-frequency harmonics (0-1).
        min_width: Minimum width value.
        max_width: Maximum width value.

    Returns:
        Width value (50=condensed to 150=expanded).
    """
    # Low harmonics dominant → wider; High harmonics dominant → narrower
    ratio = low_harmonic_energy / (high_harmonic_energy + 0.001)
    normalized = ratio / (ratio + 1.0)  # 0-1 range
    width = min_width + normalized * (max_width - min_width)
    return int(round(width))


def compute_word_typography(
    loudness: float,
    pitch_hz: Optional[float],
    low_harmonic: float,
    high_harmonic: float,
    minimum_pct: float = 3.0,
    baseline_pct: float = 5.0,
    maximum_pct: float = 12.0,
) -> dict:
    """Compute full typography mapping for a word.

    Args:
        loudness: Normalized loudness 0-1.
        pitch_hz: Estimated pitch in Hz.
        low_harmonic: Low harmonic energy 0-1.
        high_harmonic: High harmonic energy 0-1.

    Returns:
        Dict with size_pct, weight, width values.
    """
    return {
        "size_pct": volume_to_size(loudness, minimum_pct, baseline_pct, maximum_pct),
        "weight": pitch_to_weight(pitch_hz),
        "width": harmonics_to_width(low_harmonic, high_harmonic),
    }
