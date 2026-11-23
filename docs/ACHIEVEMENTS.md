# Achievements and current limits

Updated23November2026. Lokesh built the independent automation/editor implementation. Caption With Intention is the original creators' design system, not a design invented by this repository.

## Delivered and reviewed

- Local speech recognition, word timing/alignment, intonation and pitch-contour analysis feed an editable canonical project. Whisper and Parakeet backend adapters remain selectable. Nemotron diarization and conservative turn splitting expose uncertainty instead of majority-voting a whole sentence into one person's color.
- Deterministic ASS/FFmpeg caption output supports read-ahead, spoken color sync, restrained reviewed motion, speaker colors/italic, type-size/weight/width controls, overlap/SFX/music conventions and actual burned-in MP4. The final MP4 remains the fidelity check, not the browser preview.
- Desktop black/white/gold editor has Edit/Text/Color/Speakers/Export workspaces; caption/word/syllable metadata edits; named speaker lanes; source-clock preview; frame seek; move/trim/split/merge; multiselect and caption-only ripple; atomic undo/redo; JSON save/open; speaker and sound review.
- Per-character spoken color overrides persist to final output. Basic source-video grading is applied before subtitles. Browser grade is approximate.
- Local render service provides bounded one-job encoding, preflight, progress/cancel/retry, actual playback/download and protected output replacement. Canonical projects remain reusable without uploading source media.
- CPU acoustic refinement preserved the reference on the saved121-word film fixture while reducing that intonation stage from0.1148s to0.0275s, about4.18x. This is not a whole-app speedup or recognition-quality gain.
- Optional sound suggestions are off by default and explicitly unverified, with unknown confidence and pending review. Classifier boundary/interface defects have regression coverage.
- Long-video resource round: finite overlapping windows, source-time consistency, sequential stages/files, reused models, explicit thread budgets, atomic checksummed per-chunk checkpoints, source/config validation, writer lock, disk check, cancel/resume and streamed output assembly. No unbounded queue of decoded videos.

## Measured resource evidence

- Real2-hour synthetic audio source:125windows; cancelled after4and resumed with those4reused. Maximum float32 decoded waveform3.84MB. Diagnostic main-process peak RSS41,936KiB, about41MiB. Diagnostic analyzer only, no speech-model memory included.
- Separate45-second real film, small.en+Nemotron,20-second windows and2compute threads:14.03seconds elapsed; sampled process-tree RSS945,104KiB, about923MiB. Sampling/summed-RSS limitations apply. This is not a two-hour actual-model benchmark or a hard RAM cap.
- That run produced23events and7model identities,21events flagged. Recognition errors remain. No certified WER/identity accuracy is claimed.
- Publication checks:710Python tests passed,9optional/fixture skips;82frontend tests passed; production build, full scripted browser acceptance and focused lint passed. Actual editor pixels and MP4 frames inspected. Green tests are not proof of reference-film parity.

## Not complete

Exact official-film visual parity, complex text shaping, overlapping ASR, validated speaker identity and no-overlap embedding links; full two-hour model inference on a weak computer; text-based chunk seam reconciliation; hard RAM/CPU caps and OOM recovery; editor-integrated analysis jobs; acoustic graphs; complete sidecar import/export UI; visual active-speaker fallback; offline installers/model manager/checksums/license inventory; community accessibility validation.

The editor already has basic browser-local autosave/reload recovery. A new requested autosave/recovery improvement is being developed separately and is not included in this publication. Browser storage is not a disk backup, and video files must be selected again after reload.

## Verification trail

- [Current milestone truth table](ACCURACY_AUDIT_2026-11-23.md)
- [Long-video resource design, commands and caveats](LONG_VIDEO_RESOURCE_ROUND.md)
- [Editor run/handoff guide](EDITOR_HANDOFF_2026-11-23.md)
- [Chronological checks](EDITOR_WORKING_NOTES.md)

Design sources: https://captionwithintention.org and https://download.captionwithintention.org/Caption-With-Intention_Design-System_V1.0.pdf . This implementation does not establish caption-regulation compliance or official endorsement.
