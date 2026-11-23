# Local editor review checklist

Review checklist, 2026-11-23. The user approved multiple logical commits and a push at 15:38 after reviewing the simplified editor.

## Open and edit

1. Run `uv sync --extra dev` at the repository root.
2. Use Node20.19+ or22.12+. In `frontend/editor`, run `npm ci`.
3. Run `uv run python engine/editor/start.py` from the root. If ports are occupied, choose `CWI_PORT` and `CWI_UI_PORT` explicitly.
4. Open the printed local URL. Open project JSON, then import its matching local source video.
5. Check the sequence dimensions/frame rate. Rotation-aware source dimensions are used for final rendering.
6. Select a caption. Edit text, timing, word typography, syllables, letter pitch, speaker and style in Properties.
7. Shift/Ctrl/Cmd-click or modifier+Space selects several cards/clips. Move, delete and ripple affect captions only, never source-video cuts.
8. Split between timed words. Merge compatible non-overlapping captions. Undo should restore the preceding structure and exact word timing.

## Review attribution

- Filter Speaker review. Listen to the turn, correct its label, mark checked, then advance to the next unchecked turn.
- Review candidates are heuristic warnings, not confirmed mistakes. Text confidence is not speaker-identity confidence.
- Missing identities, overlapping speech and brief replies still need human review. Existing colors/labels are not silently re-inferred by opening the editor.

## Save and render

- Save project downloads canonical JSON. Browser-local autosave is convenient, not a portable backup.
- A valid browser-local session restores before the API project on reload. Source video must be reselected.
- Render video snapshots current edits and transfers source bytes only to the local Python service. Check source-mismatch/truncation warnings.
- Inspect the actual final MP4 in the render panel, including fullscreen. Download it within the local one-hour retention window.
- Finish or cancel the active render before leaving the editor or opening another project.
- Source limit is2GB; one encoding worker at a time. A120second idle-read limit bounds abandoned transfers. There is a30minute encoding timeout.
- Lost create/source-response/status connections are reconciled or retried. Create uses a bounded idempotent retry; this is not page-reload resume. Cancelling frees a new slot after the current worker has stopped.

## Verification at this checkpoint

- Python:660passed,9skipped. Skips:3audio-classifier checks without onnxruntime,1Nemotron development-model/sample check,5missing Buzz video fixture checks. One pre-existing fixture deprecation warning.
- Frontend:78passed. Production build passes. Dependency audit:0findings at the latest check.
- `CWI_CHROME=/path/to/chrome npm run test:smoke` runs synthetic acceptance checks, retaining screenshots/video in its printed temporary directory.
- Acceptance covers keyboard selection/seek, split/merge, move/undo/redo, attribution review, JSON save/reopen, reload with API running, storage-failure rescue, stale save/reload/session and gesture guards, dropped create/status/source responses, transfer cancellation, real MP4 encode/play/download,390px layout, rotated portrait output, and a two-hour1000caption timeline.
- Real31-event/five-identity45-second project also imports, plays, restores, renders and downloads. This does not certify the five identities.

## Not signed off

- Browser/final pixel parity across fonts, synthetic bold, music-symbol fallback, complex shaping and overlap layout.
- Legacy duration/easing/syllable-mode/min-size/breakout flags are editable saved metadata but do not override the stable rendering path. Not every saved control changes output.
- Automatic speaker identity, overlapping ASR and automatic SFX/music recognition accuracy.
- A two-hour source-video processing/render benchmark. The long-timeline check is an editing test only.
- Native project-folder lifecycle, installer/distribution and internet deployment. The HTTP service remains local development software.

Design research and chronological evidence are in EDITOR_WORKING_NOTES.md. No remote changes were made.
