"""Pluggable ASR backend factory.

Two backends, selected by name:

- "faster_whisper" (default): Whisper via CTranslate2. Most accurate on
  GPU; heavy on CPU. Word timestamps built in.
- "parakeet": NVIDIA Parakeet TDT via onnx-asr. ~40x realtime on a
  desktop CPU with word-level timestamps — the low-hardware pick.
  See docs/ASR_BACKENDS.md for the benchmark comparison.

Both backends expose the same interface: transcribe(),
transcribe_stream() and get_model_info(), so callers (e.g.
engine.speech.pipeline.SpeechPipeline) can swap them freely.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:  # pragma: no cover - typing only
    from engine.asr.parakeet import ParakeetTranscriber
    from engine.asr.transcriber import Transcriber

BACKEND_FASTER_WHISPER = "faster_whisper"
BACKEND_PARAKEET = "parakeet"
SUPPORTED_BACKENDS = (BACKEND_FASTER_WHISPER, BACKEND_PARAKEET)

DEFAULT_MODELS = {
    BACKEND_FASTER_WHISPER: "large-v3-turbo",
    BACKEND_PARAKEET: "nemo-parakeet-tdt-0.6b-v3",
}


def create_asr_engine(
    backend: str = BACKEND_FASTER_WHISPER,
    model: Optional[str] = None,
    device: str = "cpu",
    **kwargs: object,
) -> Transcriber | ParakeetTranscriber:
    """Create an ASR engine for the given backend.

    Args:
        backend: One of SUPPORTED_BACKENDS.
        model: Backend-specific model name. None uses the backend
            default (see DEFAULT_MODELS).
        device: "cpu" or "cuda".
        **kwargs: Backend-specific options. For faster-whisper:
            compute_type, beam_size, vad_filter. For parakeet:
            quantization (compute_type="int8" maps to quantization
            "int8" automatically), providers.

    Raises:
        ValueError: Unknown backend name.
    """
    if backend == BACKEND_FASTER_WHISPER:
        from engine.asr.transcriber import Transcriber

        return Transcriber(
            model=model or DEFAULT_MODELS[backend],
            device=device,
            **kwargs,
        )

    if backend == BACKEND_PARAKEET:
        from engine.asr.parakeet import ParakeetTranscriber

        options = dict(kwargs)
        quantization = options.pop("quantization", None)
        compute_type = options.pop("compute_type", None)
        if quantization is None and compute_type == "int8":
            quantization = "int8"
        return ParakeetTranscriber(
            model=model or DEFAULT_MODELS[backend],
            quantization=quantization,
            device=device,
            **options,
        )

    raise ValueError(
        f"Unknown ASR backend: {backend!r}. "
        f"Supported: {', '.join(SUPPORTED_BACKENDS)}"
    )
