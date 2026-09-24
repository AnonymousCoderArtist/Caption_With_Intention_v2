# Nemotron 3 Diarization — CPU benchmark

Date: 2026-09-24. Host: 4-core x86_64 (~3.5 GHz), 8 GB RAM, no GPU. This matches
our CPU-only target class.

Model: `nvidia/Nemotron-3-Diarization` (~100M-param transformer, released
2026-09-23), OpenMDW-1.1 open-weights, up to 8 speakers, overlap-aware.
Runtime: audio.cpp (0xShug0) `audiocpp_cli`, CPU backend, `--threads 4`.
Weights: community GGUF port `audio-cpp/Nemotron-3-Diarization-GGUF`.

## Setup

```
tools/nemotron-bench/
  audio.cpp/      # source + build (gitignored)
  models/         # GGUF weights (gitignored)
  bench/          # test audio + output JSON (gitignored)
  run_bench.sh    # benchmark script: ./run_bench.sh [bf16|q8] [threads]
```

## Results

Test audio: 149.7 s real multi-speaker clip (16 kHz mono) and a 598.9 s
looped variant (4x) to simulate a 10-minute chunk.

| Run | Wall time | RTF (audio-sec / wall-sec) |
|---|---:|---:|
| 150 s clip, BF16 (incl. model load) | 8.9 s | 16.8x |
| 150 s clip, Q8_0 (incl. model load) | 7.4 s | 20.3x |
| 10 min chunk, Q8_0 (sustained, 3 runs) | 59–64 s | 9.4–10.2x |

Sustained per-second cost is ~2.5–3x the short-clip rate; the offline profile
processes in 30.4 s chunks, so short files amortize per-chunk overhead better.
A feature-length (120 min) job is therefore roughly 12–15 min of wall time
for the diarization stage on this hardware — the whisper ASR stage remains
the dominant cost.

Memory: peak RSS ~460 MB for the 10-minute Q8_0 run (model load dominates).
Weights: BF16 189 MB, Q8_0 102 MB on disk.

Output quality spot-check (150 s clip): 40 turns, 6 speakers, per-turn
confidence 0.50–0.99 (mean 0.83), mean turn 2.6 s, median inter-turn gap
0.26 s. The first ~23 s (music title intro) correctly produced no turns.
Q8_0 turns matched BF16 within a few 10 ms frames on the 150 s clip.

## Output format (for the backend wrapper)

`--turns-out` writes JSON; each turn is

```json
{"start_sample": 369440, "end_sample": 407520, "speaker_id": "speaker_0", "confidence": 0.98694}
```

- `start_sample` / `end_sample` are audio samples at 16 kHz → divide by 16000
  for seconds.
- `speaker_id` is anonymous, ordered by first arrival (speaker_0 spoke first).
- `confidence` is a real per-turn value (0–1) — better than pyannote's
  hard-coded 1.0; feeds our review-queue confidence directly.
- Request options: `speaker_threshold` (default 0.5), `speaker_min_frames`,
  `speaker_pad_frames` (in 10 ms frames).

## Verdict

Fits our taste: open-weights, free, no API key, local after one-time download,
language-agnostic, chunk-friendly, and comfortably CPU-runnable (~1 min per
10-min chunk, ~0.5 GB RAM). Recommended default weights: Q8_0 (faster,
lighter, output-identical at this scale); keep BF16 for exact-parity work.
The current `diarize` fingerprint backend stays as the zero-dependency
fallback.

## Reproduce

```bash
cd tools/nemotron-bench
./run_bench.sh q8 4
```
