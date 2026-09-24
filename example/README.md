# Caption With Intention — Example Project

This folder contains a sample project demonstrating the Caption With Intention pipeline:

```
example/
├── captions/          — Output caption files (SRT, VTT, ASS)
├── design_systems/    — CI V1.0 design system profiles
├── fonts/             — Font resources (RobotoFlex)
├── project/           — Project metadata and analysis
├── rendered/          — Rendered frame samples
└── video/             — Source video samples
```

## Pipeline Output

The ASR engine (`engine/asr/`) produces structured transcription with:
- **Word-level timestamps** — every word has start/end time
- **Speaker attribution** — each word tagged with speaker ID (when diarization is active)
- **Confidence scores** — per-word and per-segment confidence
- **Segment grouping** — words grouped into sentence-like segments

### Example ASR Output Structure

```json
{
  "text": "Hello world this is a test",
  "language": "en",
  "model": "large-v3-turbo",
  "source_path": "audio.wav",
  "duration": 5.0,
  "word_count": 6,
  "segment_count": 2,
  "segments": [
    {
      "text": "Hello world",
      "start": 0.0,
      "end": 2.5,
      "confidence": 0.95,
      "words": [
        {"text": "Hello", "start": 0.0, "end": 0.8, "confidence": 0.97},
        {"text": "world", "start": 0.8, "end": 1.5, "confidence": 0.93}
      ]
    }
  ],
  "words": [
    {"text": "Hello", "start": 0.0, "end": 0.8, "confidence": 0.97, "speaker_id": "spk_1"},
    {"text": "world", "start": 0.8, "end": 1.5, "confidence": 0.93, "speaker_id": "spk_1"}
  ]
}
```

## Models Used

| Component | Model | Size | Accuracy |
|---|---|---|---|
| ASR | faster-whisper large-v3-turbo | 1.6 GB | ~7.7% WER |
| Diarization | diarize (CPU) | 0 | ~4.8% DER |
| Diarization (alt) | pyannote community-1 | 30 MB | ~12% DER |

## Running Transcription

```python
from engine.asr.transcriber import Transcriber

t = Transcriber(model="large-v3-turbo", device="cpu", compute_type="int8")
result = t.transcribe("path/to/audio.wav", word_timestamps=True)
print(result.text)
print(result.words)  # Word-level timing
```
