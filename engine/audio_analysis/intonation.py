"""Word-level intonation analysis (M9).

Aggregates per-word acoustic features from audio + word timings and
maps them into CI typography values per the design system:

    Volume    -> type size   (3% whisper .. 12% yell of screen height)
    Pitch     -> font weight (low pitch heavy, high pitch light)
    Harmonics -> font width  (low harmonics wide, high harmonics narrow)

Word timings come from ASR + alignment (M6). Acoustic features are
smoothed across neighboring words so typography doesn't visibly jitter.

Usage:
    from engine.audio_analysis.intonation import IntonationAnalyzer

    analyzer = IntonationAnalyzer()
    result = analyzer.analyze("scene.wav", words)
    for wi in result.words:
        print(wi.text, wi.typography)
"""

from __future__ import annotations

import logging
import statistics
import subprocess
import tempfile
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import numpy as np

from engine.asr.models import Word
from engine.audio_analysis.basic import (
    estimate_loudness,
    estimate_pitch,
    smooth_signal,
)
from engine.typography.mapping import (
    compute_word_typography,
    pitch_to_weight,
)

# Normal-speech anchor: loudness 0.5 maps to the 5% baseline type
# size (see typography.mapping.volume_to_size).
NORMAL_SPEECH_LOUDNESS = 0.5

# Voice-register stabilization (spec 2.3.8-2.3.9): weight and width
# encode the voice's overall character, not per-word fluctuations.
# Width deviation from the scene's median harmonic balance is scaled
# by this factor (speech measures ~0.88 low-dominant with the 1 kHz
# split and must render at neutral width 100).
WIDTH_DEVIATION_SCALE = 150.0

logger = logging.getLogger("caption_with_intention")

DEFAULT_SAMPLE_RATE = 16000
# Frequency split between "low" and "high" harmonic energy (Hz).
DEFAULT_HARMONIC_CUTOFF_HZ = 1000.0
# Smoothing window across consecutive words (odd numbers work best).
DEFAULT_SMOOTH_WINDOW = 5
# Words shorter than this (s) borrow their neighbor's features: pitch
# estimation needs ~20 ms minimum and gets unreliable below ~40 ms.
MIN_RELIABLE_WORD_DURATION = 0.04


def estimate_harmonic_energies(
    audio_chunk: np.ndarray,
    sample_rate: int,
    cutoff_hz: float = DEFAULT_HARMONIC_CUTOFF_HZ,
) -> tuple[float, float]:
    """Split spectral energy into low/high bands (0-1 normalized).

    Low-harmonic-dominant speech (deep, resonant) maps to WIDE type;
    high-harmonic-dominant speech (bright, breathy) maps to NARROW type.

    Returns:
        (low_energy, high_energy), each normalized 0-1 against the
        chunk's total spectral energy; (0.0, 0.0) for silence.
    """
    if len(audio_chunk) < 2:
        return 0.0, 0.0

    windowed = audio_chunk * np.hanning(len(audio_chunk))
    spectrum = np.abs(np.fft.rfft(windowed))
    freqs = np.fft.rfftfreq(len(audio_chunk), d=1.0 / sample_rate)
    energy = spectrum**2

    total = float(energy.sum())
    if total <= 0:
        return 0.0, 0.0

    low = float(energy[freqs < cutoff_hz].sum()) / total
    high = float(energy[freqs >= cutoff_hz].sum()) / total
    return low, high


@dataclass(slots=True)
class WordIntonation:
    """Acoustic features + CI typography for one word."""

    text: str
    start: float
    end: float
    loudness: float = 0.0
    pitch_hz: Optional[float] = None
    low_harmonic: float = 0.0
    high_harmonic: float = 0.0
    typography: dict = field(default_factory=dict)
    reliable: bool = True  # False for very short / silent words

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "start": self.start,
            "end": self.end,
            "loudness": round(self.loudness, 4),
            "pitch_hz": (
                round(self.pitch_hz, 1) if self.pitch_hz is not None else None
            ),
            "low_harmonic": round(self.low_harmonic, 4),
            "high_harmonic": round(self.high_harmonic, 4),
            "typography": dict(self.typography),
            "reliable": self.reliable,
        }


@dataclass(slots=True)
class IntonationResult:
    """Intonation analysis for a sequence of words."""

    words: list[WordIntonation] = field(default_factory=list)
    sample_rate: int = DEFAULT_SAMPLE_RATE
    duration: float = 0.0

    @property
    def word_count(self) -> int:
        return len(self.words)

    @property
    def unreliable_count(self) -> int:
        return sum(1 for w in self.words if not w.reliable)

    def to_dict(self) -> dict:
        return {
            "word_count": self.word_count,
            "unreliable_count": self.unreliable_count,
            "sample_rate": self.sample_rate,
            "duration": self.duration,
            "words": [w.to_dict() for w in self.words],
        }


class IntonationAnalyzer:
    """Per-word intonation analysis with cross-word smoothing.

    Args:
        harmonic_cutoff_hz: Low/high spectral split frequency.
        smooth_window: Cross-word smoothing window (1 = no smoothing).
        smooth_method: 'moving_average' or 'exponential'.
    """

    def __init__(
        self,
        harmonic_cutoff_hz: float = DEFAULT_HARMONIC_CUTOFF_HZ,
        smooth_window: int = DEFAULT_SMOOTH_WINDOW,
        smooth_method: str = "moving_average",
    ) -> None:
        self.harmonic_cutoff_hz = harmonic_cutoff_hz
        self.smooth_window = max(1, smooth_window)
        self.smooth_method = smooth_method

    def analyze(
        self,
        audio: np.ndarray,
        sample_rate: int,
        words: Sequence[Word],
    ) -> IntonationResult:
        """Analyze word-level intonation from an in-memory waveform.

        Args:
            audio: 1-D float waveform.
            sample_rate: Audio sample rate in Hz.
            words: Word timings (ASR + alignment output).

        Returns:
            IntonationResult with per-word features + CI typography.
        """
        audio = np.asarray(audio, dtype=np.float32)
        duration = len(audio) / sample_rate if sample_rate else 0.0
        if not words:
            return IntonationResult(
                words=[], sample_rate=sample_rate, duration=duration
            )

        raw: list[dict] = []
        for word in words:
            raw.append(self._analyze_word(audio, sample_rate, word))

        # Cross-word smoothing so typography doesn't jitter frame to
        # frame. Pitch keeps None for unvoiced words: smooth only the
        # voiced runs, then re-attach.
        loudness_s = smooth_signal(
            [r["loudness"] for r in raw],
            window_size=self.smooth_window,
            method=self.smooth_method,
        )
        low_s = smooth_signal(
            [r["low"] for r in raw],
            window_size=self.smooth_window,
            method=self.smooth_method,
        )
        high_s = smooth_signal(
            [r["high"] for r in raw],
            window_size=self.smooth_window,
            method=self.smooth_method,
        )
        pitch_s = self._smooth_pitch([r["pitch"] for r in raw])

        # Scene-relative calibration. Absolute dB levels conflate hot
        # mastering with loud delivery: an evenly loud narration
        # otherwise renders every word big. When the scene's typical
        # word runs hotter than the normal-speech anchor, scale all
        # words down so the typical word lands on the anchor (baseline
        # size) and only genuine emphasis grows. Quiet scenes keep
        # their absolute levels, so whispers stay small. The recorded
        # loudness field stays the raw smoothed measurement; the
        # calibrated value drives typography only.
        refs = [
            loudness_s[i] for i, r in enumerate(raw) if r["reliable"]
        ]
        ref = statistics.median(refs) if refs else 0.0
        cal = (
            NORMAL_SPEECH_LOUDNESS / ref
            if ref > NORMAL_SPEECH_LOUDNESS
            else 1.0
        )

        out: list[WordIntonation] = []
        for i, (word, r) in enumerate(zip(words, raw)):
            reliable = r["reliable"]
            loud_raw = loudness_s[i] if reliable else 0.0
            loud = loud_raw * cal
            pitch = pitch_s[i] if reliable else None
            low = low_s[i] if reliable else 0.0
            high = high_s[i] if reliable else 0.0
            out.append(
                WordIntonation(
                    text=word.text,
                    start=word.start,
                    end=word.end,
                    loudness=loud_raw,
                    pitch_hz=pitch,
                    low_harmonic=low,
                    high_harmonic=high,
                    typography=compute_word_typography(loud, pitch, low, high),
                    reliable=reliable,
                )
            )

        # Voice-register stabilization (spec 2.3.8-2.3.9). Per-word
        # pitch estimates on short words are octave-noisy (one narrator
        # measured 95-331 Hz across a single sentence) and speech
        # harmonics are near-constant, so raw per-word weight/width
        # flicker word to word. Weight instead uses the scene's median
        # pitch for every word; width is relative to the scene's median
        # harmonic balance, so typical speech renders at neutral width
        # 100 and only genuinely unusual textures deviate.
        voiced = [w.pitch_hz for w in out if w.pitch_hz is not None]
        med_pitch = statistics.median(voiced) if voiced else None
        balances = [
            w.low_harmonic / (w.low_harmonic + w.high_harmonic)
            for w in out
            if w.reliable and (w.low_harmonic + w.high_harmonic) > 0
        ]
        med_bal = statistics.median(balances) if balances else None
        for w in out:
            typo = dict(w.typography)
            typo["weight"] = pitch_to_weight(med_pitch)
            width = 100
            if med_bal is not None and w.reliable:
                tot = w.low_harmonic + w.high_harmonic
                if tot > 0:
                    dev = (w.low_harmonic / tot) - med_bal
                    width = round(
                        min(150.0, max(25.0, 100 + dev * WIDTH_DEVIATION_SCALE))
                    )
            typo["width"] = width
            w.typography = typo

        logger.info(
            "Intonation analysis: %d words (%d unreliable) over %.2fs",
            len(out),
            sum(1 for w in out if not w.reliable),
            duration,
        )
        return IntonationResult(
            words=out, sample_rate=sample_rate, duration=duration
        )

    def analyze_file(
        self,
        source_path: str | Path,
        words: Sequence[Word],
    ) -> IntonationResult:
        """Analyze word-level intonation from an audio/video file.

        WAV files are read directly; other containers (mp4, mp3, ...)
        are extracted to a temporary 16 kHz mono WAV via ffmpeg first.
        """
        source = Path(source_path)
        tmp_path: Optional[str] = None
        try:
            audio_path = source
            if source.suffix.lower() != ".wav":
                fd, tmp_path = tempfile.mkstemp(suffix=".wav")
                import os

                os.close(fd)
                cmd = [
                    "ffmpeg",
                    "-y",
                    "-i",
                    str(source),
                    "-ac",
                    "1",
                    "-ar",
                    str(DEFAULT_SAMPLE_RATE),
                    tmp_path,
                ]
                proc = subprocess.run(
                    cmd, capture_output=True, timeout=120, check=False
                )
                if proc.returncode != 0:
                    raise RuntimeError(
                        f"ffmpeg audio extraction failed for {source}"
                    )
                audio_path = Path(tmp_path)

            import soundfile as sf

            audio, sample_rate = sf.read(str(audio_path), dtype="float32")
            if audio.ndim > 1:
                audio = audio.mean(axis=1)
            return self.analyze(audio, sample_rate, words)
        finally:
            if tmp_path:
                try:
                    Path(tmp_path).unlink()
                except OSError:
                    pass

    def _analyze_word(
        self,
        audio: np.ndarray,
        sample_rate: int,
        word: Word,
    ) -> dict:
        """Extract raw acoustic features for one word's audio slice."""
        start_i = max(0, int(word.start * sample_rate))
        end_i = min(len(audio), int(word.end * sample_rate))
        chunk = audio[start_i:end_i]

        min_samples = int(MIN_RELIABLE_WORD_DURATION * sample_rate)
        if len(chunk) < min_samples:
            return {
                "loudness": 0.0,
                "pitch": None,
                "low": 0.0,
                "high": 0.0,
                "reliable": False,
            }

        loudness = estimate_loudness(chunk, sample_rate, "rms")
        if loudness <= 0.0:
            # Silent span: no intonation to show
            return {
                "loudness": 0.0,
                "pitch": None,
                "low": 0.0,
                "high": 0.0,
                "reliable": False,
            }

        pitch = estimate_pitch(chunk, sample_rate)
        low, high = estimate_harmonic_energies(
            chunk, sample_rate, self.harmonic_cutoff_hz
        )
        return {
            "loudness": loudness,
            "pitch": pitch,
            "low": low,
            "high": high,
            "reliable": True,
        }

    def _smooth_pitch(
        self, pitches: list[Optional[float]]
    ) -> list[Optional[float]]:
        """Smooth pitch over voiced runs; unvoiced words stay None."""
        result: list[Optional[float]] = list(pitches)
        run: list[int] = []

        def flush() -> None:
            if len(run) >= 2:
                smoothed = smooth_signal(
                    [pitches[i] for i in run],  # type: ignore[misc]
                    window_size=min(self.smooth_window, len(run)),
                    method=self.smooth_method,
                )
                for idx, value in zip(run, smoothed):
                    result[idx] = value
            run.clear()

        for i, p in enumerate(pitches):
            if p is None:
                flush()
            else:
                run.append(i)
        flush()
        return result
