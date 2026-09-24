"""ASR (Automatic Speech Recognition) engine.

Uses faster-whisper (CTranslate2 backend) for fast, accurate,
low-resource transcription with word-level timestamps.

Architecture:
    Transcriber  →  high-level segments with speaker attribution
    Word         →  word-level timing and text
    Transcript   →  full document with metadata

Supported models (all via faster-whisper):
    tiny, base, small, medium, large-v3, large-v3-turbo, distil-large-v3

Usage:
    from engine.asr.transcriber import Transcriber

    transcriber = Transcriber(model="large-v3-turbo", device="cpu")
    result = transcriber.transcribe("audio.wav")
    print(result.text)
"""

from __future__ import annotations
