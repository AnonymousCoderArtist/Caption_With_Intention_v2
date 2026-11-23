"""Audio classification: speech vs music vs sound effects.

Feeds the CWI element conventions (spec sections 2.4.4-2.4.5):
- speech regions -> dialogue events (from ASR, handled by M6)
- music regions  -> music events (white, in note symbols, no animation)
- sfx regions    -> sound_effect events (white, bracketed, animated)

Two classifiers, same interface:
- HeuristicClassifier: numpy-only, CPU-cheap, no model download.
  Music = sustained harmonic periodicity with low spectral flux;
  SFX = transient bursts with high spectral flux and low periodicity.
- YamnetClassifier: YAMNet ONNX (Apache-2.0, Google; ONNX export from
  huggingface.co/audiomagic/yamnet-onnx) for 521-class AudioSet labels.
  The top label becomes the bracket/descriptor text. Requires the
  `sound-classify` extra (onnxruntime) and the model files; use
  download_yamnet() or place yamnet.onnx + yamnet_class_map.csv under
  ~/.cache/cwi/.

The heuristic is the always-available baseline; YAMNet plugs in behind
the same classify() call once its model file is present.
"""

from __future__ import annotations

import csv
import math
import os
from dataclasses import dataclass
from typing import Literal, Optional

import numpy as np

from engine.audio_analysis.basic import positive_autocorrelation

SoundClass = Literal["speech", "music", "sfx", "silence"]


@dataclass
class SoundRegion:
    """A contiguous non-speech audio region with its classification."""

    start: float
    end: float
    label: SoundClass
    loudness: float  # normalized 0-1, for type sizing
    detail: Optional[str] = None  # e.g. "thunder" when a model provides it


def _frame_signal(samples: np.ndarray, frame: int, hop: int) -> list[np.ndarray]:
    if len(samples) < frame:
        return [samples] if len(samples) else []
    return [
        samples[i : i + frame]
        for i in range(0, len(samples) - frame + 1, hop)
    ]


def spectral_flux(samples: np.ndarray, sample_rate: int) -> float:
    """Mean spectral flux (frame-to-frame magnitude change).

    High for transients and noisy bursts (SFX), low for sustained
    tones (music) and steady speech.
    """
    frames = _frame_signal(samples, frame=1024, hop=512)
    if len(frames) < 2:
        return 0.0
    mags = [np.abs(np.fft.rfft(f * np.hanning(len(f)))) for f in frames]
    flux = [
        float(np.sum((mags[i + 1] - mags[i]) ** 2))
        for i in range(len(mags) - 1)
    ]
    norm = float(np.mean([np.sum(m**2) for m in mags])) + 1e-12
    return float(np.mean(flux) / norm)


def harmonicity(samples: np.ndarray, sample_rate: int) -> float:
    """Strength of periodic structure, 0-1 (normalized autocorrelation peak).

    High for music and voiced speech, low for noisy SFX.
    """
    if len(samples) < sample_rate // 10:
        return 0.0
    x = samples - np.mean(samples)
    denom = float(np.sum(x**2)) + 1e-12
    ac = positive_autocorrelation(x) / denom
    lo, hi = int(sample_rate / 500), int(sample_rate / 60)  # 60-500 Hz
    if hi >= len(ac):
        hi = len(ac) - 1
    if lo >= hi:
        return 0.0
    return float(np.max(ac[lo:hi]))


def zero_crossing_rate(samples: np.ndarray) -> float:
    """Fraction of adjacent samples with sign changes (noise indicator)."""
    if len(samples) < 2:
        return 0.0
    signs = np.signbit(samples)
    return float(np.mean(signs[1:] != signs[:-1]))


def estimate_region_loudness(samples: np.ndarray) -> float:
    """RMS loudness normalized to 0-1 (full-scale sine = 1.0)."""
    if len(samples) == 0:
        return 0.0
    rms = float(np.sqrt(np.mean(samples**2)))
    return min(1.0, rms * np.sqrt(2.0))


class HeuristicClassifier:
    """Rule-based speech/music/sfx classifier (no dependencies beyond numpy).

    Decision order:
    1. silence: very low energy.
    2. music: strong sustained periodicity (high harmonicity) with
       low spectral flux, OR very high harmonicity overall.
    3. sfx: high spectral flux (transients) or very low harmonicity.
    4. default: speech (mid periodicity, mid flux).
    """

    def __init__(
        self,
        silence_rms: float = 0.01,
        music_harmonicity: float = 0.45,
        music_flux_max: float = 0.020,
        sfx_flux: float = 0.045,
        sfx_harmonicity_max: float = 0.20,
    ) -> None:
        self.silence_rms = silence_rms
        self.music_harmonicity = music_harmonicity
        self.music_flux_max = music_flux_max
        self.sfx_flux = sfx_flux
        self.sfx_harmonicity_max = sfx_harmonicity_max

    def classify(self, samples: np.ndarray, sample_rate: int) -> SoundClass:
        if len(samples) == 0 or estimate_region_loudness(samples) < self.silence_rms:
            return "silence"
        harm = harmonicity(samples, sample_rate)
        flux = spectral_flux(samples, sample_rate)
        if harm >= 0.75 or (harm >= self.music_harmonicity and flux <= self.music_flux_max):
            return "music"
        if flux >= self.sfx_flux or harm <= self.sfx_harmonicity_max:
            return "sfx"
        return "speech"


YAMNET_URL = "https://huggingface.co/audiomagic/yamnet-onnx/resolve/main"
YAMNET_DIR = os.path.expanduser(os.path.join("~", ".cache", "cwi"))

# Overly generic AudioSet parents - demoted in favor of a specific
# sibling when one scores at least half as high ("[Thunder]" captions
# better than "[Water]").
_GENERIC_LABELS = {
    "water",
    "noise",
    "sound effect",
    "ambient noise",
    "sounds of things",
    "animal",
    "environment",
    "outside, urban or manmade",
    "outside, rural or natural",
    "audio",
}

# AudioSet display names that count as speech for our purposes.
_SPEECH_LABELS = {
    "speech",
    "child speech, kid speaking",
    "male speech, man speaking",
    "female speech, woman speaking",
    "conversation",
    "narration, monologue",
    "babbling",
    "speech synthesizer",
    "shout",
    "bellow",
    "whoop",
    "yell",
    "screaming",
    "whispering",
}


def download_yamnet(dest_dir: str = YAMNET_DIR) -> tuple[str, str]:
    """Download yamnet.onnx + class map (Apache-2.0) to dest_dir."""
    import urllib.request

    os.makedirs(dest_dir, exist_ok=True)
    paths = []
    for name in ("yamnet.onnx", "yamnet_class_map.csv"):
        path = os.path.join(dest_dir, name)
        if not os.path.exists(path):
            urllib.request.urlretrieve(f"{YAMNET_URL}/{name}", path)
        paths.append(path)
    return paths[0], paths[1]


class YamnetClassifier:
    """YAMNet (AudioSet, 521 classes) speech/music/sfx classifier.

    The top class display_name is kept as `detail` - it becomes the
    bracket text for SFX captions ("[Thunder]") or the descriptor for
    music ("jazz music playing").
    """

    def __init__(
        self,
        model_path: Optional[str] = None,
        class_map_path: Optional[str] = None,
        music_threshold: float = 0.25,
        auto_download: bool = True,
    ) -> None:
        try:
            import onnxruntime as ort
        except ImportError as exc:  # pragma: no cover - env dependent
            raise RuntimeError(
                "YamnetClassifier needs the 'sound-classify' extra "
                "(uv sync --extra sound-classify)"
            ) from exc
        if model_path is None or class_map_path is None:
            if not auto_download:
                raise RuntimeError("YAMNet model files not provided")
            model_path, class_map_path = download_yamnet()
        self.session = ort.InferenceSession(
            model_path, providers=["CPUExecutionProvider"]
        )
        with open(class_map_path, newline="", encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
        self.labels = [r["display_name"] for r in rows]
        self.music_idx = {
            i for i, name in enumerate(self.labels) if "music" in name.lower()
        }
        self.speech_idx = {
            i
            for i, name in enumerate(self.labels)
            if name.lower() in _SPEECH_LABELS
        }
        self.music_threshold = music_threshold

    def classify_detail(
        self, samples: np.ndarray, sample_rate: int
    ) -> tuple[SoundClass, Optional[str]]:
        if len(samples) == 0 or estimate_region_loudness(samples) < 0.005:
            return "silence", None
        if sample_rate != 16000:
            # naive resample (linear) to YAMNet's 16 kHz
            n = int(len(samples) * 16000 / sample_rate)
            samples = np.interp(
                np.linspace(0, len(samples) - 1, n), np.arange(len(samples)), samples
            ).astype(np.float32)
        scores = self.session.run(
            ["output_0"], {"waveform": samples.astype(np.float32)}
        )[0]
        mean_scores = scores.mean(axis=0)
        music_score = float(sum(mean_scores[i] for i in self.music_idx))
        speech_score = float(sum(mean_scores[i] for i in self.speech_idx))
        top = int(np.argmax(mean_scores))
        top_score = float(mean_scores[top])
        top_name = self.labels[top]
        if top_name.lower() in _GENERIC_LABELS:
            # prefer a specific sibling scoring >= half of the generic top
            order = np.argsort(mean_scores)[::-1]
            for idx in order[:8]:
                if self.labels[idx].lower() not in _GENERIC_LABELS and float(
                    mean_scores[idx]
                ) >= top_score * 0.5:
                    top, top_name = int(idx), self.labels[idx]
                    break
        if speech_score >= music_score and speech_score > top_score * 0.5:
            return "speech", "speech"
        if music_score >= self.music_threshold:
            best_music = max(self.music_idx, key=lambda i: mean_scores[i])
            name = self.labels[best_music]
            return "music", None if name.lower() == "music" else name
        return "sfx", top_name


    def classify(self, samples: np.ndarray, sample_rate: int) -> SoundClass:
        return self.classify_detail(samples, sample_rate)[0]


def merge_regions(
    regions: list[SoundRegion], max_gap_s: float = 0.6
) -> list[SoundRegion]:
    """Merge adjacent regions with the same label separated by tiny gaps."""
    merged: list[SoundRegion] = []
    for region in regions:
        if (
            merged
            and merged[-1].label == region.label
            and merged[-1].detail == region.detail
            and region.start - merged[-1].end <= max_gap_s
        ):
            prev = merged[-1]
            total = (prev.end - prev.start) + (region.end - region.start)
            prev.loudness = (
                prev.loudness * (prev.end - prev.start)
                + region.loudness * (region.end - region.start)
            ) / total
            prev.end = region.end
        else:
            merged.append(SoundRegion(**vars(region)))
    return merged


def detect_sound_regions(
    samples: np.ndarray,
    sample_rate: int,
    speech_spans: list[tuple[float, float]],
    classifier: Optional[HeuristicClassifier] = None,
    frame_s: float = 0.25,
    min_region_s: float = 0.3,
) -> list[SoundRegion]:
    """Find non-speech regions and classify each as music or sfx.

    Args:
        samples: Mono audio samples.
        sample_rate: Sample rate in Hz.
        speech_spans: (start, end) seconds covered by ASR speech.
        classifier: Classifier to use (defaults to HeuristicClassifier).
        frame_s: Analysis frame length in seconds.
        min_region_s: Regions shorter than this are dropped.

    Returns:
        Classified SoundRegion list, sorted by start time.
    """
    if not isinstance(sample_rate, (int, np.integer)) or sample_rate <= 0:
        raise ValueError("Sample rate must be a positive integer")
    if not math.isfinite(frame_s) or frame_s <= 0:
        raise ValueError("Frame duration must be finite and positive")
    if not math.isfinite(min_region_s) or min_region_s < 0:
        raise ValueError("Minimum region duration must be finite and non-negative")
    samples = np.asarray(samples)
    if samples.ndim != 1 or not np.isfinite(samples).all():
        raise ValueError("Sound detection requires finite mono samples")
    clf = classifier or HeuristicClassifier()
    frame = max(1, int(frame_s * sample_rate))
    speech_mask = np.zeros(len(samples), dtype=bool)
    for start, end in speech_spans:
        if not math.isfinite(start) or not math.isfinite(end) or end <= start:
            continue
        i0 = min(len(samples), max(0, int(start * sample_rate)))
        i1 = min(len(samples), max(0, int(end * sample_rate)))
        if i1 > i0:
            speech_mask[i0:i1] = True

    # Whole-region classifiers (YAMNet) segment by energy only and
    # classify each region once; per-frame classifiers vote per frame.
    whole_region = hasattr(clf, "classify_detail")
    energy_gate = HeuristicClassifier()

    labels: list[str] = []
    for i in range(0, len(samples), frame):
        chunk = samples[i : i + frame]
        if len(chunk) < frame // 2 or speech_mask[i : i + len(chunk)].any():
            labels.append("speech")
        elif whole_region:
            labels.append(
                "silence"
                if estimate_region_loudness(chunk) < energy_gate.silence_rms
                else "sound"
            )
        else:
            labels.append(clf.classify(chunk, sample_rate))

    regions: list[SoundRegion] = []
    current: Optional[str] = None
    region_start = 0
    for idx, label in enumerate(labels + ["speech"]):  # sentinel flushes
        if label != current:
            if current in ("music", "sfx", "sound"):
                t0 = region_start * frame / sample_rate
                t1 = min(idx * frame, len(samples)) / sample_rate
                if t1 - t0 >= min_region_s:
                    i0, i1 = int(t0 * sample_rate), int(t1 * sample_rate)
                    final_label = current
                    detail = None
                    if whole_region:
                        final_label, detail = clf.classify_detail(  # type: ignore[attr-defined]
                            samples[i0:i1], sample_rate
                        )
                        if final_label in ("speech", "silence"):
                            current = label
                            region_start = idx
                            continue
                    regions.append(
                        SoundRegion(
                            start=t0,
                            end=t1,
                            label=final_label,
                            loudness=estimate_region_loudness(samples[i0:i1]),
                            detail=detail,
                        )
                    )
            current = label
            region_start = idx
    # Never bridge a speech/silence gap when producing caption suggestions.
    return merge_regions(regions, max_gap_s=0.0)
