"""Audio signal analysis utilities for CWI.

Provides functions for loudness estimation, pitch analysis, and harmonic
analysis used by the intonation engine.
"""

from __future__ import annotations

import numpy as np
from typing import Optional


def estimate_loudness(
    audio_chunk: np.ndarray,
    sample_rate: int,
    mode: str = "rms",
) -> float:
    """Estimate loudness of an audio chunk.

    Args:
        audio_chunk: 1D numpy array of audio samples.
        sample_rate: Audio sample rate in Hz.
        mode: 'rms', 'peak', or 'short_term'.

    Returns:
        Loudness value in arbitrary units (normalized 0-1).
    """
    if len(audio_chunk) == 0:
        return 0.0

    if mode == "rms":
        rms = np.sqrt(np.mean(audio_chunk**2))
        # Normalize to typical speech range (-60dB to 0dB)
        return float(min(1.0, max(0.0, (20 * np.log10(rms + 1e-10) + 60) / 60)))
    elif mode == "peak":
        peak = np.max(np.abs(audio_chunk))
        return float(min(1.0, max(0.0, (20 * np.log10(peak + 1e-10) + 60) / 60)))
    elif mode == "short_term":
        # Short-term RMS over 20ms windows
        window_size = int(sample_rate * 0.02)
        if len(audio_chunk) < window_size:
            return estimate_loudness(audio_chunk, sample_rate, "rms")
        rms_values = [
            np.sqrt(np.mean(audio_chunk[i : i + window_size] ** 2))
            for i in range(0, len(audio_chunk) - window_size, window_size)
        ]
        avg_rms = np.mean(rms_values)
        return float(min(1.0, max(0.0, (20 * np.log10(avg_rms + 1e-10) + 60) / 60)))
    else:
        raise ValueError(f"Unknown loudness mode: {mode}")


def estimate_pitch(
    audio_chunk: np.ndarray,
    sample_rate: int,
) -> Optional[float]:
    """Estimate fundamental frequency (F0) using autocorrelation.

    Args:
        audio_chunk: 1D numpy array of audio samples.
        sample_rate: Audio sample rate in Hz.

    Returns:
        Estimated pitch in Hz, or None if no pitch detected.
    """
    if len(audio_chunk) < sample_rate * 0.02:  # Need at least 20ms
        return None

    # Autocorrelation method
    corr = np.correlate(audio_chunk, audio_chunk, mode="full")
    corr = corr[len(corr) // 2 :]  # Keep positive lags

    # Find first zero crossing
    zero_crossings = np.where(np.diff(np.sign(corr)))[0]
    if len(zero_crossings) == 0:
        return None

    first_zero = zero_crossings[0]
    if first_zero < 2:
        return None

    # Find peak in autocorrelation before first zero crossing
    search_range = corr[:first_zero]
    if len(search_range) == 0:
        return None

    peak_lag = np.argmax(search_range)
    if peak_lag < 1:
        return None

    pitch_hz = sample_rate / peak_lag

    # Sanity check: human voice range 80-500 Hz
    if 80 <= pitch_hz <= 500:
        return float(pitch_hz)
    return None


def smooth_signal(
    values: list[float],
    window_size: int = 5,
    method: str = "moving_average",
) -> list[float]:
    """Smooth a signal to prevent visible jitter.

    Args:
        values: Input signal values.
        window_size: Smoothing window size.
        method: 'moving_average' or 'exponential'.

    Returns:
        Smoothed signal values.
    """
    if not values:
        return []

    if method == "moving_average":
        result = []
        for i in range(len(values)):
            start = max(0, i - window_size // 2)
            end = min(len(values), i + window_size // 2 + 1)
            result.append(float(np.mean(values[start:end])))
        return result
    elif method == "exponential":
        alpha = 2.0 / (window_size + 1)
        result = [values[0]]
        for i in range(1, len(values)):
            result.append(alpha * values[i] + (1 - alpha) * result[-1])
        return result
    else:
        raise ValueError(f"Unknown smoothing method: {method}")


def analyze_audio_chunk(
    audio_chunk: np.ndarray,
    sample_rate: int,
) -> dict:
    """Run full audio analysis on a chunk.

    Returns loudness, pitch, and basic harmonic info.
    """
    loudness = estimate_loudness(audio_chunk, sample_rate, "rms")
    pitch = estimate_pitch(audio_chunk, sample_rate)
    peak = float(np.max(np.abs(audio_chunk))) if len(audio_chunk) > 0 else 0.0

    return {
        "loudness": loudness,
        "pitch_hz": pitch,
        "peak_amplitude": peak,
    }
