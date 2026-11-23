# Editor handoff, 23 November 2026

Status at the 13:30 handoff: local working changes only. The user later approved multiple logical commits and a push at 15:38.

## Delivered in the working tree

### Editing workspace

- Black, white and warm-gold editor with source-video composition, transport and timeline. After review, caption-card dots/type pills/side accents were removed and dialogue tracks were grouped into named, colored speaker lanes.
- Source-video clock drives playback. Timeline seeking, frame stepping, caption move/trim and overlapping lanes.
- Keyboard and pointer multiselect, group move/delete, caption-only ripple and single-step undo for batch changes. Source video is never cut or rippled.
- Split between timed words and merge compatible non-overlapping captions. Absolute word timing and review metadata survive structure edits.
- Caption text, word timing/typography, syllables, letter pitches, speakers, style, notes, review state and sequence settings can be edited.
- Buffered typing, numeric draft inputs, serialized edits and stale-response/session guards prevent common edit rollback and cross-project races.

### Local export

- Render video creates an actual FFmpeg MP4 from the current project snapshot and selected source.
- Preflight checks dimensions, duration and captions beyond the source; transfer/encoding progress, cancel, retry, final playback, seek, fullscreen and download are available.
- H264/yuv420p video, AAC audio and fast-start MP4. Rotation-aware display dimensions. Odd source dimensions receive at most one pixel of right/bottom padding rather than cropping/resizing.
- One active encoder, 2 GB source limit, 120-second idle transfer bound, 30-minute encoder timeout and one-hour completed-output retention.
- Lost create/source/status response recovery is covered. Create has one idempotent retry. This is not durable page-reload job resume.
- Active render must finish/cancel before project replacement or leaving the editor. CLI output replacement is staged so an encode failure does not destroy an existing output.

### Saving and review

- Canonical JSON open/save, empty New and browser-local autosave. Valid browser edits restore before the API project on reload. Video must be reselected.
- Storage failure is visible and JSON rescue remains available.
- Attribution-review filter, listen-to-turn, next unchecked turn, speaker assignment and explicit checked state.
- Review warnings use timing coverage, competing overlap and short/missing identities. They are not identity-confidence scores.
- Deleting a speaker reopens affected review. Undo restores identity and checked state.

## Verified

- Python: 660 passed, 9 skipped. Skips are 3 optional onnxruntime audio-classifier checks, 1 Nemotron development-model/sample check and 5 absent Buzz video fixture checks. One pre-existing fixture warning.
- Frontend: 78 tests passed. Production build passed. Dependency audit: zero findings at the latest check.
- Focused lint passed for new local service, launcher, batch, structure and render work plus their regression tests. Unrelated legacy lint was not swept into this work.
- Repeatable browser acceptance covers edit/undo, save/reopen, API/local restoration, storage rescue, stale reads/saves/sessions/gestures, render response failures, cancellation, actual MP4 encode/play/download, 390 px layout, rotated portrait output and a two-hour, 1,000-caption editing project.
- The last caption in that two-hour editing fixture can be edited and its saved JSON preserves the new end. This is not a two-hour source encode benchmark.
- Existing real 31-caption, five-model-identity, 45-second project was reopened, played, restored and rendered through the UI. Download verified as H264/yuv420p 640×480, AAC, 45.038 seconds, 4,780,515 bytes. UI and an output frame were visually inspected. The five identities are not certified correct.

## Not signed off

- Exact preview/final parity across fonts, synthetic bold, complex shaping, music-symbol fallback and overlap layout. Final MP4 remains the visual source of truth.
- Automatic speaker identity, overlapping ASR and automatic SFX/music recognition accuracy.
- Legacy duration/easing/syllable-mode/min-size/breakout fields remain editable saved metadata but do not override the stable rendering path. Not every saved control changes final output.
- Full long-video analysis/orchestration, native project-folder lifecycle, installer/distribution and internet deployment. The local HTTP service is development software.
- No claim that this reproduces every official Caption With Intention reference frame exactly.

## Run locally

1. Repository root: `uv sync --extra dev`.
2. Node 20.19+ or 22.12+. In `frontend/editor`, run `npm ci`.
3. Root: `uv run python engine/editor/start.py`.
4. Open the printed URL, open project JSON, then select the matching local video.
5. Save JSON for a portable backup. Render video for final MP4.

Set `CWI_PORT` and `CWI_UI_PORT` if default ports are occupied. Browser acceptance runs from `frontend/editor` using `CWI_CHROME=/path/to/chrome npm run test:smoke`. CLI fallback: `uv run python -m engine.renderer project.cwi.json source.mp4 output.mp4`.

Design research and chronological checks are in `EDITOR_WORKING_NOTES.md`; the short review path is in `EDITOR_REVIEW_CHECKLIST.md`. Caption With Intention is the original creators' design system. This work is Lokesh's independent automation/editor implementation.
