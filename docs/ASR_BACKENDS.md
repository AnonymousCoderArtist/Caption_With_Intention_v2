# ASR backend comparison (Nov 2026)

How the CWI automation engine picks a speech-to-text model. Requirements
specific to this project: **word-level timestamps** (color sync happens
at word onset), **runs on low hardware / CPU** (local-first, offline),
and good English accuracy for film/TV dialogue.

## The short version

| Model | English WER | Speed on CPU | Word timestamps | Verdict |
|---|---|---|---|---|
| **Parakeet TDT 0.6B v3 (ONNX)** | 6.75% (VoxPopuli) | **~41x realtime** (Ryzen 9800X3D) | yes (token-level) | **default low-hardware pick** |
| Parakeet TDT 0.6B v2 (ONNX) | 6.51% (VoxPopuli) | ~40x realtime | yes | English-only alternative |
| faster-whisper large-v3-turbo | ~11.5% (VoxPopuli, Whisper decode) | not CPU-viable (large class) | yes | keep for GPU / max-accuracy runs |
| Canary 1B v2 (ONNX) | 7.42% (VoxPopuli) | ~10x realtime | yes | multilingual, slow on CPU |
| Nemotron 3.5 Transcribe | **5.33%** (HF Open ASR avg, best open-weight) | **needs a real GPU** (~4B active / 30B total params) | yes | future "gpu" tier; also does diarization + translation in one checkpoint |
| parakeet-unified-en-0.6b | 5.91% (HF leaderboard avg) | NeMo/GPU-oriented; streaming 160ms–2s | yes | watch: offline+streaming in one model; no CPU-friendly runtime packaged yet |

CPU numbers: onnx-asr's own comparison (AMD Ryzen 7 9800X3D, VoxPopuli
English subset) — Parakeet TDT 0.6B v3 runs at 41.2x realtime vs
9.8x for Canary 1B v2; large-v3-turbo has no viable CPU row there.

## The "new NVIDIA model" (what was in the news)

**Nemotron 3.5 Transcribe** (released 2026-10-28): open-weight,
promptable speech model — one checkpoint does transcription (40
languages), speaker attribution (up to 8 speakers), translation, and
audio Q&A. #1 among open-weight models on the Hugging Face Open ASR
English leaderboard (5.33% avg WER) and top of two diarization
benchmarks. It is **not** low-hardware: a hybrid Mamba-Transformer MoE
with ~4B active parameters per token (30B total), served with vLLM or
NeMo-Speech.cpp on RTX/DGX Spark-class GPUs, and built for recorded
audio rather than streaming. Great future fit for machines with a GPU —
it could fuse ASR + diarization (our M6+M7) into one pass — but it is
not the answer for a CPU laptop.

Also recent: **parakeet-unified-en-0.6b** (2026) — one 600M model doing
both offline and streaming inference down to 160 ms latency, offline WER
5.91% avg (better than TDT v2's 6.04% on the same leaderboard table).
Interesting for a future live-preview mode; today it ships only through
NeMo, so it is not practical for our CPU-first path.

## What we run

- **Default for low hardware: Parakeet TDT 0.6B v3 via
  [onnx-asr](https://github.com/istupakov/onnx-asr)** — pure ONNX
  runtime (no PyTorch/NeMo), int8 quantization available, token
  timestamps we group into words (`engine/asr/parakeet.py`).
  `uv sync --extra parakeet`, then
  `SpeechPipeline(asr_backend="parakeet")`.
- **GPU / accuracy tier: faster-whisper large-v3-turbo** (existing
  default backend, unchanged).
- Diarization stays Nemotron 3 Diarization via audio.cpp (M7) — its
  ~100M-param Q8_0 GGUF runs fine on CPU (~1 min per 10-min chunk, 460 MB
  RSS, see tools/nemotron-bench/RESULTS.md).

## Sources

- onnx-asr comparison (CPU/GPU RTFx, VoxPopuli WER):
  https://istupakov.github.io/onnx-asr/comparison/
- onnx-asr usage (timestamps, quantization, model names):
  https://istupakov.github.io/onnx-asr/usage/
- Nemotron 3.5 Transcribe + Granary v2 release post (2026-10-28):
  https://huggingface.co/blog/nvidia/nemotron-transcribe-granary
- parakeet-unified-en-0.6b model card (offline/streaming WER table):
  https://huggingface.co/nvidia/parakeet-unified-en-0.6b
- Nemotron 3.5 Transcribe research page:
  https://research.nvidia.com/labs/nemotron/NVIDIA-Nemotron-3.5-Transcribe/
