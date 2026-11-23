# Accuracy and delivery audit, 23 November 2026

This bounded round after `8ee2a11` was reviewed and approved for focused commits and separate pushes at16:32IST on23November2026. Target is desktop computers, including weak computers. Phone layout is not a product requirement.

## This round

- Re-read the current official website and V1.0 PDF, including synchronization, intonation, sound/music and distribution sections. Reinspected the official Buzz sequence contact sheet. No motion constants were changed in this round. Earlier user-reviewed restrained motion remains the implementation target; it is not advertised as exact reference parity.
- Replaced full direct autocorrelation with zero-padded FFT autocorrelation for long spans. Short arrays retain the direct calculation. No new dependency. Tests compare against the linear reference, including non-power-of-two lengths and voice frequencies.
- A saved121-word/45-second film diagnostic measured intonation at0.0275s versus0.1148s with the direct reference, about4.18x for that analysis stage. Pitch/loudness and derived typography were unchanged on that fixture. Seven-run synthetic median kernel speedups were7.1x/42.2x/67.2x at4k/16k/32k samples. These are not whole-pipeline or weak-PC benchmarks.
- Full analysis shares one decoded waveform between intonation, pitch contours and optional sound detection. This removes duplicate decode, not the existing full-waveform memory limitation.
- Fixed YAMNet's misplaced `classify` method, which had been hidden by optional-model skips. Optional tests were run with the cached free model and CPU runtime:17passed.
- Sound-region timing uses actual sample boundaries and cannot run past the source. Invalid configuration/non-finite audio is rejected. Speech spans are clamped and no sound proposal bridges a detected speech gap.
- Connected opt-in sound proposals to `SpeechPipeline.run_full(..., detect_sounds=True)`. Default remains off. Without an explicitly supplied model classifier this uses cheap heuristics and generic labels. No model is implicitly downloaded by this path.
- Sound proposals have unknown confidence, model provenance, pending review and an explicit warning. A separate Sound review filter and Check sound labels make them visible. Accept/correct removes them from that filter; save/undo remain ordinary event edits.
- Project duration now uses maximum event end, not the end of the final start-sorted event. Long music beds must not shorten the sequence.

## Sound limitations

The controlled tone/noise fixture produced dialogue, music and SFX categories and an actual MP4 was inspected. Music is white/static with note symbols; SFX is white/bracketed. This proves plumbing and visual categories, not real-world label quality. Speech-covered frames are deliberately excluded, so underlying effects/music are missed. YAMNet proposed Door and Dog on gaps in the real film diagnostic; neither label is certified. Keep the feature opt-in and review every suggestion. No recognition, speaker-identity or WER improvement is claimed from these changes.

## Milestone truth against the repository specification

| Milestone | Current evidence | Still open |
|---|---|---|
| M0 foundation | Project schema, local editor/service, logs | Desktop packaging skeleton/product lifecycle incomplete |
| M1 ingest | Probe, integrity hash and proxy helpers | Proxy integration in editor, broad codec QA |
| M2 scenes/chunks | Chunk/scene/checkpoint modules and unit tests | Actual two-hour stop/reopen/resume exit test |
| M3 formats | SRT/VTT/TTML/ASS exporter modules | Full reader/import and embedded-caption extraction workflow |
| M4 renderer | Deterministic rules and actual MP4 fixtures | Exact official-film parity, shaping/overlap edge cases |
| M5 manual editor | Caption/word/syllable JSON/speaker/style edits, undo, tabs | Native scene overrides; legacy saved controls do not all affect stable rendering |
| M6 speech | Local ASR, alignment, editable provenance | Ground-truth WER/timing comparison and overlap transcription |
| M7 diarization | Nemotron backend, turn splitting, overlap reconciliation | Stable identity accuracy, no-overlap embeddings and global runner integration |
| M8 visual fallback | Confidence routing scaffold | Actual face/active-speaker inference; not complete |
| M9 intonation | Measured acoustic features, mappings, CPU refinement | Independent acoustic graphs and broader calibrated voice validation |
| M10 syllables | Heuristic/audio-refined syllables, editable JSON, contours | Phoneme alignment validation; friendly timing graph |
| M11 SFX/music | Classifiers plus new opt-in reviewable proposals | Mixed-under-dialogue detection and validated label confidence/accuracy |
| M12 review | Speaker and sound filters, editable status/notes | Unified issue queue, correction log and scene-jump workflow |
| M13 long production | Reusable chunk/checkpoint helpers | Bounded-memory full orchestrator, ETA/cache/model lifecycle and real crash-resume run |
| M14 timeline | Source clock, named speaker lanes, move/trim/zoom/scrub/frame-step | Waveform, loudness/pitch graphs, dedicated syllable/scene tracks |
| M15 export | Sidecar engine modules, local MP4 UI and CLI | Full sidecar UI, codec/quality/audio-copy controls and hardware detection |
| M16 regression | Numerical/timing tests, scripted browser acceptance and inspected renders | Automated approved golden-frame image diffs |
| M17 usability | Keyboard paths and named speaker indicators | Large-text/high-contrast options and community testing protocol/run |
| M18 distribution | Local launch instructions | Installers, model manager/checksums, third-party license inventory and explicit project license |
| M19 CLI/batch | Render CLI and diagnostic analysis scripts | Unified commands and persistent unattended job queue |
| M20 release | Useful local prototype | Not a completed MVP; above exit gates remain open |

Priority after this review: reproducible recognition/identity benchmark, bounded long-video orchestrator, audio graphs, then desktop packaging/offline models. Do not mark a milestone complete only because a helper module exists.

## Sources and precedence

- Official design site, current read: https://captionwithintention.org
- Official PDF: https://download.captionwithintention.org/Caption-With-Intention_Design-System_V1.0.pdf
- NumPy linear-correlation definition and direct-method performance warning: https://numpy.org/doc/stable/reference/generated/numpy.correlate.html
- SciPy direct/FFT correlation documentation, technical cross-check only; SciPy was not added: https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.correlate.html
- YAMNet model/task documentation: https://www.tensorflow.org/hub/tutorials/yamnet
- ONNX model distribution: https://huggingface.co/audiomagic/yamnet-onnx

Official film is the visual reference where the PDF and film differ. User-reviewed deviations and motion-stability choices are documented separately, not presented as official constants. The PDF says CWI augments conventional captions; burn-in output does not establish regulatory compliance. Caption With Intention is its creators' design. This repository is Lokesh's automation implementation.

## Publication checks

Full pre-push rerun:684Python passed/9skipped,82frontend passed,production build and full browser acceptance passed. Optional classifier suite separately passed17tests with cached model and CPU runtime.16changed/new source/doc files passed credential/large-artifact scan. No recordings, local media, generated outputs or credentials selected. Subsequent long-video work is not included in this approval.
