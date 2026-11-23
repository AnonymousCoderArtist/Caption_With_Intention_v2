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

Browser autosave now includes one previous valid recovery snapshot,a silent icon,and optional chosen-file disk saving in supported browsers. Browser storage is not a disk backup, and video files must be selected again after reload. Disk targets reconnect explicitly. See AUTOSAVE_RECOVERY.md for permission and close/crash limits.

## Verification trail

- [Current milestone truth table](ACCURACY_AUDIT_2026-11-23.md)
- [Long-video resource design, commands and caveats](LONG_VIDEO_RESOURCE_ROUND.md)
- [Editor run/handoff guide](EDITOR_HANDOFF_2026-11-23.md)
- [Chronological checks](EDITOR_WORKING_NOTES.md)

Design sources: https://captionwithintention.org and https://download.captionwithintention.org/Caption-With-Intention_Design-System_V1.0.pdf . This implementation does not establish caption-regulation compliance or official endorsement.


### Silent autosave and optional disk copy, local review

Replaced automatic save banners with a tiny topbar icon; settings/recovery only open on click. Optional user-chosen JSON file uses serialized writes after permission, alongside browser autosave. Disk errors pause until reconnect, project changes/reload detach the target. Browser support is feature-detected, not universal. No cloud/sign-in/cost added.92frontend tests,production build/full browser acceptance and focused writable-stream readback passed. Native OS picker/user-visible disk path remains manually unverified. See docs/AUTOSAVE_RECOVERY.md for permission and close/crash limits. User approved publication at18:19IST.


### Guide and portrait recheck, approved publication

Optional8-topic in-app guide added,never auto-opens. Extended9:16 testing found detached boxes/overwrapped long captions. Proposed portrait-only timed one-line pages fix that fixture while changing full-sentence read-ahead; landscape unchanged. Real18s portrait analysis/import/UI render/play/download and synthetic long/overlap frames inspected.711Python/9skip,94frontend,build/full acceptance,zero dependency-audit findings. Overlap blocks can still exceed the lower20% safe area,ASR/speaker errors remain. See docs/GUIDE_AND_PORTRAIT_RECHECK.md. Approved for publication at18:34IST; do not claim everything complete or fully optimized.
