"""Audio signal analysis utilities for CWI.

Provides functions for loudness estimation, pitch analysis, and harmonic
analysis used by the intonation engine.
"""

from __future__ import annotations

from typing import Optional

import numpy as np


def positive_autocorrelation(samples: np.ndarray) -> np.ndarray:
    """Linear autocorrelation at non-negative lags, using FFT for long spans.

    Zero padding prevents circular wrap-around. Float64 keeps the same
    numerical precision as pitch analysis without a new dependency.
    """
    x = np.asarray(samples, dtype=np.float64)
    if not len(x):
        return np.empty(0, dtype=np.float64)
    if len(x) < 256:
        return np.correlate(x, x, mode="full")[len(x) - 1:]
    fft_size = 1 << (2 * len(x) - 1).bit_length()
    spectrum = np.fft.rfft(x, n=fft_size)
    return np.fft.irfft(spectrum * spectrum.conj(), n=fft_size)[:len(x)]


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
    min_hz: float = 80.0,
    max_hz: float = 500.0,
    clarity: float = 0.3,
) -> Optional[float]:
    """Estimate fundamental frequency (F0) using autocorrelation.

    Normalized autocorrelation, peak search bounded to the human voice
    range (80-500 Hz by default), with parabolic interpolation for
    sub-sample accuracy. Returns None for unvoiced/noisy spans whose
    best peak is weaker than `clarity` (fraction of the lag-0 peak).

    Args:
        audio_chunk: 1D numpy array of audio samples.
        sample_rate: Audio sample rate in Hz.
        min_hz: Lowest detectable F0 (longest lag).
        max_hz: Highest detectable F0 (shortest lag).
        clarity: Minimum normalized peak height to count as voiced.

    Returns:
        Estimated pitch in Hz, or None if no pitch detected.
    """
    if len(audio_chunk) < sample_rate * 0.02:  # Need at least 20ms
        return None

    x = np.asarray(audio_chunk, dtype=np.float64) - float(np.mean(audio_chunk))
    corr = positive_autocorrelation(x)

    if len(corr) == 0 or corr[0] <= 0:
        return None
    corr = corr / corr[0]  # normalize: lag-0 peak = 1.0

    lag_min = max(1, int(sample_rate / max_hz))
    lag_max = min(len(corr) - 1, int(sample_rate / min_hz))
    if lag_max <= lag_min:
        return None

    window = corr[lag_min : lag_max + 1]
    peak_lag = int(np.argmax(window)) + lag_min
    if corr[peak_lag] < clarity:
        # No strong periodicity -> unvoiced / noise
        return None

    # Parabolic interpolation around the peak for sub-sample lag
    peak = float(peak_lag)
    if 1 <= peak_lag < len(corr) - 1:
        a, b, c = corr[peak_lag - 1], corr[peak_lag], corr[peak_lag + 1]
        denom = a - 2 * b + c
        if abs(denom) > 1e-12:
            peak = peak_lag + 0.5 * (a - c) / denom

    if peak <= 0:
        return None
    pitch_hz = sample_rate / peak
    if min_hz <= pitch_hz <= max_hz:
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
