"""ASR (Automatic Speech Recognition) engine.

Uses faster-whisper (CTranslate2 backend) for fast, accurate,
low-resource transcription with word-level timestamps.

Architecture:
    Transcriber  →  high-level segments with speaker attribution
    Word         →  word-level timing and text
    Transcript   →  full document with metadata

Supported models:
    faster-whisper backend: tiny, base, small, medium, large-v3,
        large-v3-turbo, distil-large-v3
    parakeet backend (CPU-first, via onnx-asr):
        nemo-parakeet-tdt-0.6b-v3 (default), nemo-parakeet-tdt-0.6b-v2,
        nemo-parakeet-rnnt-0.6b, nemo-canary-1b-v2
    See docs/ASR_BACKENDS.md for the comparison and recommendation.

Usage:
    from engine.asr.transcriber import Transcriber

    transcriber = Transcriber(model="large-v3-turbo", device="cpu")
    result = transcriber.transcribe("audio.wav")
    print(result.text)

    # Or pick a backend explicitly:
    from engine.asr.backends import create_asr_engine

    engine = create_asr_engine(backend="parakeet")
    result = engine.transcribe("audio.wav")
"""

from __future__ import annotations
