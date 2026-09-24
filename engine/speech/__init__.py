"""Speech pipeline — ASR + Diarization + Alignment in one pass.

Orchestrates the full speech-to-caption pipeline:

    1. ASR (faster-whisper)  →  word-level timestamps
    2. Diarization           →  speaker segments
    3. Alignment             →  refined boundaries
    4. Speaker matching      →  assign speaker_id to each word

Usage:
    from engine.speech.pipeline import SpeechPipeline

    pipeline = SpeechPipeline(
        asr_model="large-v3-turbo",
        diarize_backend="diarize",
    )
    result = pipeline.run("video.mp4")
    for word in result.words:
        print(f"{word.start:.2f}s {word.text} ({word.speaker_id})")
"""

from __future__ import annotations
