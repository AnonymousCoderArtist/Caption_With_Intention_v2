# Long-video RAM/CPU round, 23 November 2026

Status: reviewed and approved for publication at17:41IST on23November2026. Builds on published `dd48bc9`. No new motion/style changes.

## Design

Use one source at a time, one analysis stage at a time, reused lazy model objects and short overlapping mono audio windows. Avoid a queue of decoded videos or multiple large model copies. Default window60seconds, overlap2seconds; maximum600seconds. For weak computers start with20-60seconds and a small model, then compare accuracy on representative dialogue before selecting a production model.

`LongVideoRunner` requires `SpeechPipeline(max_workers=1)`. `cpu_threads` reaches faster-whisper, Nemotron and the Parakeet ONNX session. ONNX operator concurrency is one, and thread-pool spinning is disabled when an explicit budget is supplied. The CLI sets common numerical-library thread limits before imports. FFmpeg extraction uses one codec thread. This is a compute-thread budget, not an OS CPU-percent cap: libraries can still own idle/helper threads and some filters/runtime work may exceed the requested count briefly.

Audio is decoded to one temporary16kHz mono WAV and removed after its chunk. Model objects survive across chunks/files, avoiding repeated loads. Checkpoint caption/turn metadata is written immediately. Final caption JSON is streamed from one chunk payload at a time. Speaker-turn metadata grows with source length and reconciliation can be expensive on dense scenes; this is not constant memory in transcript size. Recognition model memory is not capped. There is no automatic OOM retry or model downgrade.

## Safety

- Full streaming SHA256 of source and a pipeline/config fingerprint protect resume against stale source/settings. Full-file hashing adds startup I/O, not full-file RAM.
- Atomic checkpoint writes and per-chunk SHA256 detect truncated/corrupt output. A failed/corrupt chunk is retried; completed verified chunks are reused.
- Exclusive work-directory lock prevents two writers. A hard-killed run can leave `run.lock`; confirm the process is gone before manually removing it. Cancellation/ordinary exceptions release the lock.
- Disk-space check runs before each window. It is a conservative floor/estimate, not a guarantee against model downloads or all output growth.
- Progress/ETA is emitted per chunk. ETA is based on completed windows in the current process and is only an estimate. Cancellation is checked between chunks; a current native inference can finish first.
- Existing stream helpers now terminate after the final overlap, use `-t` duration instead of an incorrect end value, decode short videos to WAV, offset shared word objects only once, and raise on chunk failure instead of pretending a partial stream succeeded.
- Both backends now return source-time results. Compatibility stream APIs still return a list and retain overlap words. Use the resumable runner for long work; do not concatenate compatibility results blindly.

## Identity/seams

Adjacent windows use existing overlap-based speaker linking. No-overlap identities remain separate and flagged. VAD-only fallback labels are excluded from identity linking, not laundered into real people. Word midpoints choose which window owns the overlap, so duplicate windows do not both emit the same region. This is not text-based seam alignment: boundary errors or missing words can remain and need listening/review. Original word times are not quantized to chunk boundaries. Syllables/provenance are shifted to source time too.

## Run

```bash
uv sync --extra dev --extra asr
uv run python -m engine.speech video.mp4 --work-dir ./analysis-jobs --model base --cpu-threads 2 --chunk-seconds 60
```

Repeat the exact command to resume. Multiple positional source files are processed sequentially with the same model instance. Default CLI model is the small `base` diagnostic choice, not an accuracy recommendation or silent replacement of the existing SpeechPipeline default. For Parakeet, install its extra and pass `--backend parakeet --model nemo-parakeet-tdt-0.6b-v3`. Nemotron requires the local audio.cpp executable/model described elsewhere; if it falls back to VAD, output identity is unknown and flagged. Models can require one-time free downloads. No mandatory Google sign-in or paid API.

Outputs: `manifest.json`, per-chunk JSON, `speaker-review.json`, and `payload.json` for editor construction. The runner does not yet create a canonical project or submit directly into the editor UI. It does not render/encode the two-hour source.

## Measured evidence

| Check | Result | Boundary |
|---|---|---|
| Real2-hour synthetic tone source |125windows,60s maximum, cancel after4and resume reuses4;125total analysis calls | Actual FFmpeg extraction with diagnostic waveform analyzer, not ASR |
| Maximum decoded float32 waveform |960,000samples =3,840,000bytes | Does not include model tensors, NumPy temporaries or FFmpeg process |
| Diagnostic process peak RSS |41,936KiB, about41MiB | Main diagnostic process only, not its children |
| Real45s film, small.en+Nemotron,20s windows,2compute threads |14.03s elapsed; sampled process-tree RSS945,104KiB, about923MiB |100ms sampling, summed RSS can double-count shared pages; not a2h model benchmark |
| Same real run CPU sampling |20total runtime/helper threads at peak; summed ps average CPU up to208% | Not20active compute threads and not a hard2-core OS limit |
| Real output |23events,7model identities,21events flagged; zero invalid word windows; actual MP4 and editor view inspected | No WER/identity accuracy certification; short chunks fragment speakers |

The small model materially affects words on old film audio. Do not claim this round made transcription more accurate. The win is finite bounded windows, honest failure state, source-time consistency and reusable progress. A two-hour actual multi-model run, weak-PC profile and batch stress test are still open.

## Sources

- ONNX Runtime thread pools, spinning and intra/inter-op control: https://onnxruntime.ai/docs/performance/tune-performance/threading.html
- CTranslate2 parallelism and oversubscription guidance: https://opennmt.net/CTranslate2/parallel.html
- Python executor behavior, avoiding unbounded work queues: https://docs.python.org/3/library/concurrent.futures.html
- onnx-asr session/model usage and supported WAV formats: https://istupakov.github.io/onnx-asr/usage/

Implementation used the installed runtime API signature to verify `sess_options` support. No new production dependency was added. Sources are guidance, not proof of the measurements, which come from the local diagnostics above.

Publication checks:710Python passed/9skipped,82frontend passed,production build/full browser acceptance and focused lint passed again before commit.13source/doc files scanned for credentials and generated artifacts with no findings. New autosave changes are a separate review round.
