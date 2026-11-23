# Editor working notes, 2026-11-23

Chronological work log. The user approved multiple logical commits and a push at 15:38 after reviewing the simplified editor. Earlier checkpoints below retain their historical no-commit status.

## Current checkpoint

660 Python tests passed with9skipped at the last full run.78frontend tests, production build and repeatable acceptance smoke pass. Commit/push preparation approved after the latest UI review. Preview remains approximate; automatic speaker identity/overlapping ASR accuracy is not signed off. The chronological checkpoints below document progress and are not a second current feature list.

## Run and verify

- Python: `uv run python engine/editor/server.py`
- Frontend: Node 20.19+ or 22.12+, `cd frontend/editor && npm ci && npm run dev`
- Frontend tests: `npm test`; production build: `npm run build`.
- Python tests: `uv run pytest -q`.
- The development frontend proxies `/api` to localhost:8080.

## What works

- Black/white/warm-gold working UI, matching the source site's visual language without copying its licensed font.
- Local video import. The video's playback clock drives the caption monitor. It is not embedded in project JSON or sent to a cloud service. Render copies bytes to the local Python service.
- Caption monitor shows simultaneous active events, with later dialogue above earlier dialogue and non-dialogue above speech.
- Per-letter onset/settle motion uses the same bounded constants as the current renderer. Manual typography and per-word overrides are editable.
- Timeline ruler seeks; arrow keys step frames; caption bodies move, edges trim. Event-time edits proportionally retime words and syllables.
- Event-text edits preserve word timing when the word count is unchanged. When count changes, timing is evenly redistributed across the event. This is disclosed next to the text field and undoable. Re-run alignment for accurate new speech timings.
- Word, syllable, letter-pitch, speaker, style, review and sequence metadata edits.
- Local JSON open, local autosave with a visible storage-failure warning, JSON download, real empty New Project.
- API-backed edits have separate Chrome checks, not only in-memory demo tests.
- Undo restores nested Word/Style models, text edits, repeated-word removal, typography, animation, box edits and project metadata.
- Manual typography and custom box settings now reach final ASS rendering. Non-default-opacity boxes use one vector rectangle to avoid overlap seams between translucent per-letter box runs.

## Important limits

- Browser preview is an approximation. Final FFmpeg render remains the fidelity check. Browser font shaping, wrapping, SFX handling and stacking geometry are not pixel-identical to libass.
- Save Project downloads canonical JSON. The separate Render video action uses the local Python service for MP4 export and final playback.
- Local autosave stores the active project in this browser only. Download JSON for a durable portable copy. Video must be selected again after reload.
- Opening JSON starts a local editing session, not a server project replacement. New Project also starts locally so an existing backend project is not silently destroyed.
- Visual multiselect, group drag, batch move/delete and caption-only ripple are implemented. Source video editing is not included.
- Timeline move/trim uses proportional retiming, not speech re-alignment. Overlapping caption intervals are packed onto separate reachable lanes.
- Legacy animation duration/easing values remain saved, but the stable motion path uses fixed envelope constants. The UI says this.
- Broad file import checks are present, but this is not a complete hostile-file parser audit.
- Python lint has pre-existing issues in editor.py/api.py and other files; no whole-repo formatting sweep was made. Renderer and new regression test files pass ruff.

## Design research and rights

Read reference material only. No third-party installer, extension, binary launcher or font was copied into the project.

- Official source identity and warm gold: https://captionwithintention.org
- Caption design specification: https://download.captionwithintention.org/Caption-With-Intention_Design-System_V1.0.pdf
- Impeccable: https://github.com/pbakaus/impeccable?tab=readme-ov-file . Apache 2.0 license/NOTICE inspected; static guidance on tool UI density, stable typography, restrained accent, working states and responsive grouping used as reference. No code incorporated.
- Butter, ToyFight: https://www.awwwards.com/sites/butter . The listing identifies an awarded timeline editor and a black/white base palette. Its inspected hero also has colorful creative assets, so this is not a claim that the whole site is monochrome. No assets copied.
- Baillat, Locomotive: https://www.awwwards.com/case-study-baillat-studio-by-locomotive.html . Flexible editorial grid, simple navigation and black/white contrast. Its custom type is reference only.
- Premiere Properties: https://helpx.adobe.com/premiere/desktop/add-text-images/stylize-text/about-properties-panel.html
- Premiere captions: https://helpx.adobe.com/premiere/desktop/add-text-images/insert-captions/about-captions.html
- WAI slider: https://www.w3.org/WAI/ARIA/apg/patterns/slider/

## Dependency refresh

The existing dev dependencies had six audit findings, including critical findings in the old test tooling. Vite 7.3.8, Vitest 4.1.12 and React plugin 5.2.0 were selected after checking registry versions/engine requirements. A clean `npm ci`, build, tests and audit pass. Node minimum is explicit. The broken `vite --proxy-config` script was replaced by `vite`; proxy settings already live in vite.config.ts.

Latest checkpoint: 595 Python passed, 9 skipped; 36 frontend tests passed. Desktop (1440/1600px), 1100px, and 390px views inspected. Small screens use Events/Preview/Properties panel switches rather than a cut-off three-column desktop. Local New/edit/trim/manual-mode/sequence-settings workflow checked in Chrome.

Actual multi-speaker project import checked with the 31-event His Girl Friday payload and matching 45-second source video. Playback, local restore and properties views had no browser errors. Monitor sizing now preserves the sequence aspect ratio, so a 4:3 source is composed inside a 4:3 caption frame rather than a wide letterboxed overlay. Existing payload speaker-color choices/diarization uncertainty are preserved, not silently re-inferred.

Atomic style update endpoint now applies cross-panel style paste in one validated undo step. Legacy syllable add/update now use the validated word snapshot path, reject negative indices/malformed time windows and support exact undo. Live API Chrome style changes and undo rechecked; full suite 595 passed, 9 skipped.

### Preview/render comparison still open

A controlled 1280x720 gray-background comparison at 1.4s exposes a material difference: the browser's glyphs are larger and bolder than final libass output, and baseline placement differs. This is not fixed by sharing motion constants. Font inspection reports Roboto Flex UPEM 2048, hhea ascent/descent 1900/-500, Win ascent/descent 2461/600. ASS font-size normalization and browser CSS em sizing differ; optical sizing and binary ASS bold versus browser variable weight also need checking. Do not call the preview pixel-accurate. Evidence/scripts: `/tmp/cwi-ui-qa/parity.py`, `parity.mjs`, `parity.cwi.json`, `parity-comparison.png`, `parity-render.mp4`. Custom opacity box is uniform but its measured width still requires time-series comparison. No speculative font scaling correction applied at this checkpoint.

### Font-metric investigation, second checkpoint

Confirmed libass normalizes `FT_SIZE_REQUEST_TYPE_REAL_DIM` after adopting OS/2 Win ascent/descent, rather than CSS em. Source inspected: https://github.com/libass/libass/blob/master/libass/ass_font.c (set_font_metrics, ass_face_set_size). Browser glyph sizes now use the bundled font's exact 2048/3061 em ratio, with optical sizing disabled at the default 14. Motion distances are unchanged. Preview bottom margin now uses frame height, fixing percentage-padding's unexpected width basis. Custom-opacity vector boxes normalize advance widths using those same font metrics and use baseline size for fixed box height rather than an estimated 1.5 multiplier. Controlled before/after frames inspected. Font size is much closer, but variable weight, baseline and custom box geometry still differ; no pixel-parity claim. New targeted tests pass, 37 frontend tests and build pass. Default .9-opacity renderer box path is untouched.

### Editing reliability checkpoint

New Project now clears imported video, playback time, selection and clipboard instead of inheriting the previous media session. Add-event, add-speaker and add-word now run through the same serialized mutation queue as property edits. Reload discards stale session responses. Numeric inspector fields buffer typing, allow a temporarily empty field, validate on blur/Enter and make one undo step, instead of firing zero/invalid updates between keystrokes. Browser QA checks empty revert, 1.75s commit and single undo back to 1.5s. New-session QA confirms zero events, no video and 00:00:00:00. Startup launcher now tears down both servers when either exits, and handles API startup failure without referencing an uncreated frontend process.

### Saved-project video render

There is now a supported local command from the repo root:

```sh
uv run python -m engine.renderer saved-project.cwi.json matching-source.mp4 captioned.mp4
```

Uses the bundled Roboto Flex font. It refuses replacing an existing output unless `--overwrite` is supplied, and never allows the source/project path as output. No upload or hosted renderer. Verified on the same 4-second 1280x720 controlled source used for preview comparisons. Browser Save Project remains JSON only; this command consumes that JSON for final video. Three command tests pass.

Custom-opacity vector box time-series measurement after normalizing both glyph advances and companion spacing: text x517..762 at rest, x479..800 emphasized; box x505..774 at rest, x467..812 emphasized. Box y628..683 remains fixed throughout. This now verifies uniform horizontal-only growth around the controlled caption without the earlier oversized margin. Default-opacity path still unchanged. Browser weight/baseline still approximate.

### Render safety and validation checkpoint

Final video generation now stages ASS/fonts in a per-render temporary folder rather than touching `captions.cwi.ass` beside the source video. The CLI stages its video in the destination folder and replaces the requested output only after successful encoding, so failed overwrite renders preserve an existing video. Protected source/project/font paths include same-file checks. Failure and source-caption preservation regressions pass.

Local browser mutations now reject invalid opacity, pitch, word typography and style growth settings before adding undo history. Import uses the same validation helpers. Python word mutation validation matches supported ranges. Latest full suite: 602 passed, 9 skipped; frontend: 40 passed; build and changed-file ruff/diff checks pass. The only Python warning is the existing class-scoped-fixture deprecation.

End-to-end saved-file check: edited the controlled sentence in Chrome, clicked the actual Save Project button, captured its downloaded JSON, then rendered that exact file via the documented command. Final pixels show the revised text. Same-count edit preserved the three original word windows and emphasis. Evidence: `/tmp/cwi-ui-qa/browser-saved.cwi.json`, `browser-saved-render.mp4`, `browser-saved-render.png`. Sequence settings now also buffer numeric edits and send only the changed metadata key to avoid stale whole-video-field replacement.

Speaker updates now preserve stable IDs and validate candidate category/color before mutation, with no undo-history change on rejection. Latest verified totals:603 Python passed/9 skipped,41 frontend passed,build and diff clean.

Last small preview-data fix: syllable pitch now supplies per-letter modulation when explicit letter pitches are absent, matching the renderer's precedence. Explicit letter pitch still wins. Regression test covers both syllables and override. Preview screenshot rechecked after the change. Frontend42 tests pass/build clean. No further visual-parity claim.

### In-editor video export, newer checkpoint

Render video is now available in the toolbar. It sends a snapshot of current canonical edits plus the selected source file to the localhost Python service, shows transfer and FFmpeg encoding progress, supports cancellation, and downloads an MP4. It is not a hosted/cloud render. The backend accepts local Host/Origin only for render endpoints, limits source to2GB and one active job, stages source/ASS/fonts/output in an isolated directory, deletes source on completion/failure, and expires retained output after one hour. AAC audio encoding allows common non-MP4 source codecs. Render jobs have four unit tests; browser flow with actual local proxy and MP4 download passes. Prior notes saying there is no render UI are superseded. JSON Save Project remains separate.

### Preview typography/layout checkpoint

Dedicated caption-only static font face plus synthetic bold now follows libass more closely than variable-weight browser UI font. Caption glyph sizing, baseline line box, and padding geometry were compared on the same frame. At1.4s normalized1280x720 emphasized text bounds: final(479,637)-(800,679),browser(478,637)-(799,680). This is one controlled test, not a universal pixel-parity guarantee.

Browser dialogue wrapping now uses bundled font advance metrics and the renderer's nominal greedy two-line split and2.5% side margins, rather than letting CSS introduce a different wrap. A long-caption comparison confirms identical line-break words and visually matching vertical stack spacing. No renderer motion changed. Remaining differences include complex shaping/width overrides,SFX,default-opacity box sizing and edge cases requiring more footage checks. Frontend44 tests pass/build clean.

### Visual selection and caption ripple

Shift/Ctrl/Cmd-click selects multiple event cards or timeline clips, with visible outlines in both. Select-all, move-by-seconds and delete act on the selected set in one validated undo step. Ripple optionally moves captions starting at/after the selected boundary, or closes the union of deleted occupied intervals without removing intervening gaps. Word/syllable timing shifts together. Source video is never cut or shifted; the UI makes this explicit. Ripple delete asks before closing caption time. Batch API and local implementation have four tests each; browser selected two events, moved by1s and undid in one step. Full Python611 passed/9 skipped,frontend48 passed/build clean. Prior notes saying selection/ripple are absent are superseded. Dragging still moves the active clip only; batch movement uses the explicit move control.

### Speaker attribution review

Event list can filter to turns needing speaker review and displays a Check speaker badge. Missing/unknown labels and very short turns are review candidates. New pipeline output also stores limited word-level diarization coverage and competing-overlap reasons, kept separate from ASR confidence. The assigned identity is not silently changed by this diagnostic. The inspector can audition a short turn with context, correct the label, mark it checked and reopen review. Batch assign-and-check uses one undo step. Reviewed metadata survives project JSON. Existing31-event clip yields15 review candidates under these heuristics; this is a review queue, not15 confirmed mistakes. No claim of diarization accuracy improvement without ground-truth comparison.

Group drag follow-up: dragging a selected timeline clip now moves the whole selected set, with linked draft positions during drag; optional ripple moves later captions. Trim handles still affect only their active clip. Chrome verified2 selected clips move1s and single undo restores them, with/without ripple. This supersedes the earlier explicit-move-only note. Source video remains fixed. Render cancellation/failure was exercised against real45s source and invalid bytes; both delete staged source/partial output and allow a later job only after the old worker stops.

Current integrated checkpoint:616 Python passed/9 skipped,51 frontend passed,production build clean,audit0,diff clean. Next unchecked turn is available in the speaker-review inspector. Local API ordinary edits remain serialized while render status/upload/encoding use separate request threads. No commits or pushes in this daytime working tree.

Hardening: all local API actions now check Host/Origin, reject private/noncallable attributes, and restrict cross-origin response headers. HTTP regressions cover external-origin rejection and valid local reads. Normal editor operations are serialized. New batch controls collapse on mobile so they no longer consume the entire monitor area;390px screenshot inspected. Render panel is bounded to viewport height. Existing API remains a local development service, not an internet deployment server.

Width-parity check exposed a real renderer bug: box-companion spans discarded word horizontal scaling. They now preserve linear fscx, including custom-opacity vector rectangles and the native default box. Regression covers150%manual width. Browser width now uses linear horizontal scaling instead of the font's wdth axis, which is a different operation. Controlled135%comparison inspected: box width now follows widened text, but browser synthetic-bold advance/spacing still differs from final and is not signed off as exact parity. Mobile transport no longer wraps behind the timeline. Mocked status-network failure now recovers via Retry status; transfer cancellation cleans up even on interrupted reads.

Non-dialogue QA: internal spaces were disappearing in untimed/music captions because whitespace-only inline glyph spans collapsed. Preserved those spaces, fixed music white styling, and extracted tested punctuation formatting that does not duplicate existing music symbols. Timed width changes now return the box companion to baseline when speech ends, matching text. Added final-result video playback inside the render panel so users can inspect the actual MP4 instead of relying on approximate browser composition. This exposed missing HTTP byte-range support: added single-range206 responses and416 validation. Actual rendered MP4 now decodes and seeks to1.4s in Chromium (previously reset to0); download remains available. Music glyph fallback and some bold spacing remain approximate in browser preview.

Render preflight now checks source metadata against sequence dimensions and last-caption time. Mismatch and beyond-source captions require an explicit local confirmation, rather than quietly exporting a different wrap or truncating captions. An undecodable browser format remains usable after a warning, since FFmpeg may support it. Actual final-player full-screen inspection passed, with encoded captions visible at2.2s. Render snapshot retains its original source filename even if the editing session changes afterward.

Structure editing added: Split at playhead (between timed words, rejects cutting a spoken word) and Merge selected (same speaker/type/style/off-camera/exception settings, rejects overlap or untimed captions). Absolute word/syllable timing is preserved, and each operation is one undo. Merged notes and speaker-review flags are preserved instead of silently dropping review work. React local and Python API paths share equivalent constraints. Browser scenario:1caption→2split→1merged→2undo, screenshot inspected. Selection details now truly opens on desktop (not CSS-only hidden semantics) and collapses on mobile breakpoint changes, fixing keyboard/accessibility discoverability.

Nested timing follow-through: word start/end edits now retime their existing syllables proportionally, in both React-local and Python paths, instead of leaving pitch/syllable timing behind. Undo restores original nested data. Local adjust-word/event timing methods now go through validated mutation paths rather than mutating unchecked and recording history before failure. Added invalid-delta/no-history regression.

Export compatibility: canonical renderer now supports explicit AAC audio for MP4 CLI/UI exports, chooses H264/yuv420p/+faststart for MP4, and actually removes audio when preserve_audio=False. Previous CLI copied PCM audio into MP4 and could fail. A real PCM-MOV→captionedMP4 conversion passed, ffprobe confirms H264/yuv420p+AAC; real in-editor render/player still passes. Existing default renderer audio-copy behavior remains for callers that request preservation without specifying a codec. SIGTERM now follows normal server cleanup rather than abandoning local render temp files.

Repeatable acceptance check added at frontend/editor/scripts/smoke.mjs with a synthetic Python-generated project/video (no third-party media download). Run npm run test:smoke after uv sync --extra dev and npx playwright install chromium, or set CWI_CHROME to an installed Chromium/Chrome path. It uses dedicated strict ports15173/18180, validates split/merge/undo/redo, JSONdownload, actual localrender/MP4decode/play/download and390px overflow, retains evidence in a printed temp directory, and terminates both servers in finally. First successful full run screenshots inspected on desktop/mobile. Playwright added as a dev-only dependency; npm audit remains0.

Acceptance journey expanded and passed again: keyboard timeline seeking, bulk move+undo, mark speaker checked, save/reopen preserving review state, and a deliberately dropped render status followed by Retry status. Saved JSON retained exact word timing. Malformed review metadata imports now fail clearly before they can crash the review queue (new regression). README includes local setup/run instructions. Latest frontend65passed;Python629passed at prior checkpoint.

Attribution-review coverage correction: adjacent/overlapping segments from the same speaker now count their union, not only the single largest intersection. This avoids false low-coverage flags at segment joins without inflating duplicated overlaps; two regressions added. No speaker identities are changed. Consolidated the current PROJECT_CONTEXT section so old pending-export/multiselect notes and counts no longer contradict implemented local capabilities; retained explicit fidelity/recognition/long-video limitations.

Lifecycle QA: render output retention now starts at encode completion, not job creation, so a long encode still gets the promised full local download window. Shutdown cancels expiry timers and rejects new jobs.8render-job regressions pass. Keyboard Space in final-render controls no longer also starts the editor's source transport; native button keyboard behavior is preserved elsewhere. Acceptance journey now starts final playback with keyboard Space and passes.

Local API request boundaries: malformed/non-object JSON now returns400 instead of being treated as empty parameters, request JSON is limited to20MB, and GET requests cannot invoke editing methods. Read-only health/project calls remain available. Regression covers malformed bodies and GETundo rejection. Source transfer also installs a browser leave-page warning while upload/preflight is active; server-side encoding can continue once upload finishes.

Portrait metadata check caught a source-resolution mismatch: FFmpeg auto-rotates phone video before subtitles, while ASS had used coded landscape dimensions. Probe now exposes separate display dimensions/rotation without changing existing coded-width fields, and renderer uses display dimensions. Real90°metadata source rendered720×1280, portrait caption placement/wrapping inspected. Regressions cover display dimensions and renderer choice. Also fixed audio-only probe with absent duration. Controlled regular/bold preview matrix confirms synthetic bold still differs from libass; left explicit, not falsely marked exact.

Portrait acceptance now part of the repo smoke journey: generates a rotation-metadata source, imports matching portrait project, renders via UI and verifies decoded360×640output. Portrait screenshot inspected. Probe handles invalid/NaNrotation metadata gracefully. Latest full638Pythonpassed9skipped,frontend65passed. Existing legacy lint in media/probe.py left untouched.

Timeline accessibility/performance: caption cards and timeline clips support Space/Enter with pressed selection state and modifier multiselect. Word seek bars now have names. Ruler tick generation stays below501ticks even for a two-hour project, rather than creating one tick per second at normal zoom; tests retain short-project1second ticks. Frontend68passed/build and full smoke pass. This bounds ruler cost only, not a claim of full long-video performance certification.

Render cancellation race review: terminal encoding state now shares a lock with cancel, so a late completion cannot overwrite cancelled state. Source-transfer handoff uses the same guard. Cancel tolerates an encoder exiting between process poll and kill. Two regressions added; current full Python640passed/9skipped, frontend68passed, build clean. Portrait monitor overlay scales to narrow monitor width and was re-inspected after smoke.


Split review caught punctuation loss when punctuation existed only in event.text rather than word tokens. Both API and browser-local split now locate tokens in the original text and retain adjacent punctuation, while preserving word timing. Fallback joining remains for text/token mismatches. New tests cover a comma and terminal exclamation, including exact undo in Python. Full smoke passes after this change; frontend69passed.


JSON import review: reject object-valued project names/source labels/notes, unknown review states, malformed scene containers, invalid confidence and non-boolean speaker/word flags before controls render them. Older omitted fields still receive defaults. Added malformed-metadata cases, full smoke passes. This is input validation for common failures, not a full hostile-file audit.

Real footage recheck after import validation:31-event, five-speaker45-second project still imports, plays, edits project name and restores on reload without browser errors. The same project rendered through the actual in-editor local service and downloaded video/mp4 successfully. This checks the workflow, not the correctness of the five identity labels. The original colors and uncertain identities remain unchanged.

Punctuation follow-through: final renderer's automatic two-line split also rebuilt words and dropped event-level punctuation. It now uses composed source spans, keeping boundary separators with the first line. Regression covers all11commas and terminal punctuation; actual rendered720p frame inspected. Browser preview still does not fully preserve event-only punctuation, so this remains a preview caveat. Frontend validation now rejects malformed syllable pitches; final-player media errors explain expiry/decode failure rather than leaving a blank result.71frontend tests/build/fullsmoke pass.


Browser punctuation follow-through: display-only copies now retain punctuation in event text around located word tokens, leaving canonical word text/timing untouched. Line-break decisions still use raw word metrics like the renderer. A mismatched transcript/token list falls back to existing tokens. Regression and browser frame show comma and terminal exclamation. Does not change the remaining synthetic-bold, music-fallback or complex-shaping caveats.

Long-timeline browser check: a synthetic two-hour project with1000caption events imports and reaches the end via keyboard without browser errors, with361ruler ticks at tested zoom. This exposed the playhead moving offscreen while the timeline stayed at zero. Timeline now keeps the playhead visible on seek/play/zoom; updated end-of-project screenshot inspected. This is a browser editing check, not a two-hour video decode/render benchmark.73frontend tests/build/standard smoke remain green.

Repeatable smoke now includes the two-hour1000caption project and verifies bounded ruler plus scroll-follow. Launcher cleanup now handles SIGTERM, uses the installed local Vite directly rather than an npx wrapper, and refuses silently choosing another occupied frontend port. CWI_PORT/CWI_UI_PORT can choose isolated ports while keeping the proxy in sync. Real launcher termination check on18181/15174 confirms both listeners stop. Default8080 was already occupied during the check, so that existing listener was left untouched.


Launcher regression coverage now checks API startup failure, frontend early exit with matching custom ports, and SIGTERM during startup. Unexpected child exit is a nonzero launcher failure after cleanup, not a misleading successful command. Full Python645passed/9skipped; focused launcher lint clean. README documents combined launch and custom-port setup.

Reload/data-loss check caught a local session being ignored whenever the Python API was running: startup chose the backend before checking browser autosave. Open editor now restores a valid local project first, with fallback to API only when no valid local copy exists. Repeatable smoke explicitly reloads while the API is live and verifies the checked speaker state survives. A separate forced storage-quota failure check confirms the warning appears and Save project still downloads a usable rescue JSON; warning screenshot inspected. This does not make autosave a substitute for portable JSON backups.

npm start/dev:api now select the repository uv environment instead of whichever system Python happens to be on PATH. Actual npm-start API proxy check passed on isolated ports. Group SIGTERM exposed repeated signals interrupting cleanup; launcher/API now ignore further INT/TERM once shutdown starts. Rerun exited cleanly without traceback and both listeners closed. Seven targeted launcher/HTTP tests and focused lint pass; npm audit remains0.

Lost-transfer-response recovery: a dropped HTTP response after successful source transfer no longer marks the job failed locally or permits a conflicting new render. UI reconciles the existing job through status, including transferring/uploading states, and keeps cancellation available. Smoke forwards the actual portrait source to the server, drops only its response, and confirms the existing render completes. Initial test interception omitted binary body bytes and correctly triggered source-size validation; the corrected test explicitly sends the fixture bytes. Full expanded smoke passes after correction.

Transfer failure distinctions now exercised: a request dropped before source bytes reach the service remains cancellable as Waiting for source, while a response dropped after transfer recovers the existing encode. Smoke cancels the first and successfully renders the second. A404expired/missing status now releases the UI into failed/retryable state rather than permanently disabling close/new render. Preflight no longer shows a nonfunctional cancel button for an old completed job. Build and expanded smoke pass.

Abandoned transfer bound: local source-upload connection now has a120second idle-read timeout, preventing a half-open browser connection from holding the only render slot indefinitely. Manager regression simulates timeout, verifies partial source deletion and worker release, then starts another job.15targeted render/HTTP tests and focused lint pass. The timeout is inactivity per read, not a120second cap on a steadily transferring file.

Expired-status recovery now covered by acceptance: intercept a job status as404, verify close and Render again unlock, remove the simulated failure, clean up the test job and complete the next portrait render. This exercises the UI state transition rather than relying only on code review. Expanded smoke passes.

Review-filter finish state no longer falsely says there are no captions or invites creating a new event when all speaker candidates are checked. It explains the filter is complete and how to see all captions; smoke verifies this state and screenshot was inspected. Search now has an accessible name. Nested delete-button keyboard events no longer bubble into the card's selection handler.

Validation parity follow-through: Python editor now rejects invalid nested syllable pitch just like browser-local validation, before history mutation. Regression covers negative, string andNaN values with unchanged project/history. Event-list search/review filters reset on a genuinely new imported session, so old filters cannot make the next project look empty. Build/full smoke pass after the change.


Source identity preflight now also warns when duration materially differs from the sequence, even if dimensions match and captions end before the shorter file. It explains that export uses the entire selected source. Differences within the larger of half a second or1% are tolerated for frame/container rounding. New test covers45sversus60sand45.04srounding.73frontend tests/build/fullsmoke pass.

Odd-dimension source export: reproduced a real H264/yuv420p failure with641×359FFV1source. MP4 filter now pads only the right/bottom edge to the next even dimension after caption rendering, preserving source pixels and caption coordinates rather than resizing/cropping. Same source successfully exports642×360yuv420p; decoded frame inspected. Regression added. Full Python648passed/9skipped and expanded smoke pass.

Odd-dimension export now has a repeatable actual FFmpeg encode test, not only command inspection; nine CLI tests and full Python649passed/9skipped. Render panel discloses the at-most-one-pixel right/bottom MP4 padding. Control audit also found legacy minimum-size/breakout fields were saved but did not override the stable renderer. Relabeled them and added explicit scope notes instead of silently changing reviewed motion behavior. Maximum size is documented as the held-growth cap. Inspector layout rechecked after fixing a cramped two-column field row.

Failure diagnostics: CLI previously kept only the first500characters of FFmpeg stderr, usually the build banner rather than the error. It now retains the bounded final1500characters, so encoder/file failures are visible. Regression confirms a trailing encoder diagnostic survives. Full Python650passed/9skipped. Existing core/ffmpeg.py unused-import and explicit-check lint warnings were left unchanged; the new regression file is clean.

Clock regression added to smoke: actual source video advances under Play, pauses, and its currentTime agrees with the editor timeline within0.1s. Transport scrub now cleans up pointer listeners on pointercancel as well as pointerup.73frontend tests/build/fullsmoke pass. All newly added Python modules/tests pass the grouped focused lint check after sorting one test import; legacy-file warnings remain separately noted.


Undecodable source check: importing invalid video bytes displays the decode error, and a failed Play attempt returns the transport to Play instead of leaving it falsely in Pause/playing state. Stale play-promise failures are ignored after source/play-state changes. Acceptance exercises the invalid source and transport state; build/fullsmoke pass. FFmpeg fallback export remains available for valid formats a browser cannot decode.

Opening-session race: a delayed initial API project response can no longer replace a New/imported local session selected while Open editor is waiting. Startup now guards client choice and project reads with the session generation. Acceptance holds the API response, creates an empty New project, releases the old response and verifies the new project stays empty. Build/fullsmoke pass.

Save/render snapshot safety: shared snapshot reader now checks project generation before and after the async project read. A save or render waiting on an old session cannot silently snapshot a replacement project. JSON save catches read/network errors instead of creating an unhandled rejection; failed saves show an error and can be retried. Acceptance aborts a live API read, then delays another save while switching to New and verifies no stale JSON download occurs. Production build/full smoke pass. Save-success text now points to the available Render video button.

Speaker-name editing now uses buffered text input rather than one transport mutation per keystroke. Blur flushes before Save; acceptance renames a speaker and immediately saves JSON, then verifies the full name survives. Also clears a previous source-video decode error when the source is replaced/removed, rather than retaining it over the caption-only monitor. Build, 73 frontend tests and full smoke pass (one acceptance-selector typo corrected before the passing run).

Nested timing consistency: import and direct word edits now reject syllables before/after their parent word in both local and Python engines, before creating undo history. Previously only the inspector enforced this boundary, so imported data could drive animation outside the word window. Existing word/event retiming tests still pass. Full Python 651passed/9skipped, frontend74passed, production build/fullsmoke pass.

Project-session cleanup: importing a project now clears the style clipboard, audition stop point and settings panel just like New. Speaker-panel draft/add state resets per session, so a partly entered speaker from another project is not carried into the next. Acceptance copies style, opens/edits the add-speaker form, imports again, and verifies the draft/form and style clipboard are cleared. Build/full smoke pass.

11:52 real-footage rerun after reliability changes: reopened the existing 31-caption/five-model-speaker project with its matching 45-second source, played/paused on the media clock, renamed and restored from browser storage, inspected word/speaker panels, and completed another actual UI MP4 render/download. Browser errors: none. UI screenshots visually inspected. Existing source project has no out-of-word syllables under the new boundary validation.

Active-render ownership: Back to start and project replacement are now blocked while preflight/transfer/encoding is active, with an explicit finish/cancel message. Before-unload warning covers encoding as well as transfer, preventing an easy path to abandoning the only active local worker without its cancel/status UI. Completed render UI resets on New/import so an old output cannot look like the new project's result. Acceptance attempts Back/import during a stalled transfer, verifies both are blocked, then cancels normally. Build/full smoke pass.

Word-property edits now retain event-only punctuation. Changing a weight/pitch/timing previously rebuilt the entire caption from raw word tokens and silently dropped quotes/punctuation stored only in event.text. Both engines now rebuild text only when the word text itself changes. Python/local regressions cover typography and timing; full Python652passed/9skipped, frontend75passed, build/fullsmoke pass.

Out-of-order API reads: reload requests now carry their own increasing generation as well as session identity. An earlier edit's delayed project response cannot overwrite the newer view in the same project. Acceptance captures the first rename's old response, completes a second rename/reload, then releases the old response and verifies the second name stays visible. Build/full smoke pass.

Word-text replacement now keeps mapped caption punctuation/spacing, including repeated words. Sequential matching identifies the selected occurrence, replaces only its token span and leaves the rest of event.text intact; unmatchable legacy text still falls back to rebuilt words. Both engines tested with quoted repeated words and undo. Full Python653passed/9skipped, frontend76passed, build/fullsmoke pass.

Caption notes now use the same buffered input as text/speaker names, with immediate blur flush. Acceptance types notes, changes panel, saves JSON and verifies the complete note survives. Legacy duration/easing labels now explicitly state that neither stable preview nor stable final output uses them as overrides, rather than implying an unspecified compatible mode exists. Production build/full smoke pass.

Legacy animation controls inspected visually after wording changes. Stable rendering resamples a continuous per-letter path after collecting onset points, so syllable_mode is also labeled legacy rather than implying a chunked-wave switch. Syllable pitch data still feeds the continuous wave. Notes/duration/easing panel layout is readable at desktop width. Build/full smoke pass.

Local render creation now validates finite/positive sequence metadata and editor timing/word/syllable constraints before allocating a folder or reserving the worker. Malformed direct API payloads fail early instead of copying a full video before a renderer failure. Four regressions verify invalid sequence/event/word/syllable payloads leave no job and do not block a valid render. Focused lint/full Python657passed/9skipped/fullsmoke pass.

Lost render-create response recovery: requests carry a random idempotency key. One retry after a transport/parse failure recovers the existing job and original project snapshot instead of failing against an invisible active worker. Acceptance lets create finish server-side, drops its response and verifies the retry proceeds through real MP4 completion. Distinct keys still respect the one-worker bound; malformed keys are rejected. Full Python659passed/9skipped, production build/fullsmoke pass. This is bounded one-retry recovery, not durable browser-reload resume.

Timeline gesture ownership: New/import remounts the timeline, whose active drag/ruler listeners now clean up on unmount and before a second gesture. Transport scrub also cleans up on unmount. This prevents a pointerup from an old session moving a matching caption ID in the replacement project. Acceptance starts a real caption drag, imports another session before pointerup, releases and saves, then verifies the imported start time stayed unchanged. Build/full smoke pass.

Deleting a speaker now reopens attribution review for captions that referenced that identity. Previously a checked event could become unassigned while remaining hidden from the review queue. Both engines have delete/undo regressions: queue reopens, undo restores identity and checked status. Full Python660passed/9skipped, frontend77passed, build/fullsmoke pass.

13:00 review checkpoint: focused lint passes across new service/start/batch/structure/render code and new HTTP/launcher/batch/structure/render/CLI/review regressions. Fresh dependency audit reports zero findings. Working HEAD remains unchanged; no commit/push performed. Review checklist now includes active-render ownership, bounded create retry, stale-session/gesture acceptance coverage and inactive legacy-control caveats.

13:05 recorded acceptance rerun: standard synthetic journey passes with current fixes. Recorded15.84s browser video and sampled contact sheet inspected; it deliberately exercises dropped responses, cancellation and expired-status recovery, so it is verification evidence rather than a polished product tour. CLI help/setup entry also checked again.

Long-project editing fix: the caption End inspector still had a legacy ten-minute maximum even though the timeline accepted two-hour projects. Removed that fixed ceiling; positive timing validation remains. Acceptance selects caption1000 at around1h58m, changes its end and verifies the saved JSON contains the edit. Build/full smoke pass.

13:18 multiselect/ripple pointer rerun after gesture cleanup: two captions remain selected in cards/timeline, a60px group drag shifts the second caption from3.64s to4.64s, and one undo restores3.64s. Ripple toggle is on; resulting group-selection/timeline screenshot inspected. This fixture deliberately uses neutral short video behind a longer sequence for gesture-only QA, not source synchronization certification.

13:24 integrated verification repeated: Python660passed/9skipped, frontend77passed, production build/full browser acceptance pass. Skip reasons recorded in review checklist:3optional onnxruntime classifier checks,1Nemotron development-model/sample check,5missing Buzz video fixture checks. These are not counted as passed model-accuracy validation. HEAD unchanged and diff check clean.

15:36 user-directed simplification: removed colored type pill and speaker dot from caption cards, plus the card's colored left accent. Type/caption/name text remains; inspector type pill also becomes plain text. Sidebar is retained, interpreting the ambiguous side remark as its card-side accent. Theme remains black/white/gold. Timeline now groups speech by speaker identity/name/color, with extra same-speaker overlap sublanes and a separate Unassigned lane. Existing move/trim/select paths apply to each lane. Three-speaker colored screenshot fixture is an illustration, not corrected diarization ground truth. Actual pointer edit and screenshots inspected. Frontend78passed, build/full acceptance pass. No commits.

15:38 publication preparation: recovered the user approval from the authenticated conversation, checked origin/main matches the local starting HEAD, scanned all74 changed/new source files for credential patterns and large artifacts, and reviewed the candidate list. No recordings, local projects, node_modules, virtual environments, test outputs or credentials are selected. Planned logical commits: renderer/export correctness; editor backend/review; reactive frontend/speaker lanes; documentation.

15:52 uncommitted polish follow-up: added same-project Edit/Text/Color/Speakers/Export workspaces. Text reduces timeline height; Color focuses the monitor and source-video brightness/contrast/saturation. Grade is stored in sequence metadata and FFmpeg applies it before subtitle burn-in. Browser CSS grade is explicitly approximate, not a matching color-management pipeline. Added per-visible-character color arrays, validation, reset, JSON persistence and ASS spoken-letter overrides for dialogue/overlap/custom captions. Word-text replacement clears positional colors to avoid silently styling a different letter; undo restores them. Native color picker now buffers until blur so browser input/change event pairs cannot roll the choice back. SFX/music character styling and per-character fonts/sizes are not offered.

Low-end work:15fps lightweight caption preview option (normal30fps), memoized speaker lane packing/track tree, offscreen card rendering containment. A4xCPU-throttled Chrome smoke plays the45s source from~1s to3.3s in a2s test without page errors. This is not a real low-end phone or long-video performance certification; source video is not transcoded into a proxy yet. Full Python663passed/9skipped, frontend81passed, build and expanded browser acceptance pass. Actual45s graded MP4 rendered; inspected output crop shows only the selected i in Miss pink while neighboring letters retain speaker color. No new commits/pushes, pending review.

15:54 user approved the reviewed polish for separate feature commits and a push after each. Published workspace tabs, source-video grade, per-character spoken colors and lightweight preview/performance in that order. Final checks and remote-head verification recorded in handover. Earlier pending-review notes above describe the state before this approval.

Publication verification: Python663passed/9skipped; frontend81passed; production builds and full acceptance passed again during feature separation. All18 source/test files match the reviewed snapshot byte-for-byte. No generated outputs, recordings or credentials selected for commits.

16:10 desktop accuracy audit (uncommitted): rechecked official site/PDF/film contact sheet and all M0-M20 spec exit criteria. Added current milestone truth table instead of treating helper modules as finished products. FFT autocorrelation preserves linear reference with no new dependency;121-word real-fixture intonation measured4.18x faster with identical typography. Shared acoustic decode removes duplicate extraction. Fixed misplaced YAMNet classify method, timestamp overrun/drift, negative speech masking and merge-across-speech defects. Connected optional non-speech proposals, off by default, with unknown confidence and explicit Sound review UI. Controlled three-category MP4 and desktop screenshot inspected; actual film model suggestions remain unverified. No recognition accuracy claim. Publication still needs approval.

16:32 user approved this reviewed desktop audit round for multiple commits/pushes. Recovered original authenticated approval; reran684Python/9skip,82frontend,build and full browser acceptance before publication. Focused commits: CPU/classifier correctness; shared waveform/sound proposals; sound-review UI; documentation. No new long-video implementation had started and none was included.

16:45 long-video local round: shared finite stream windows fix final-overlap infinite loop, wrong extraction length, duplicate shared-word offsets, inconsistent Whisper source timestamps and silent partial failures. Sequential runner adds source/config matching, atomic checksummed chunks, one-writer lock, disk check, cancel/resume, metadata-only reconciliation and streamed final captions. VAD fallback never becomes global identity evidence. Explicit thread budget reaches Whisper/Nemotron/Parakeet; CLI sets BLAS/OpenMP limits before imports and processes sources one at a time. Real2h tone extraction/cancel/resume diagnostic and45s actual model run measured separately, detailed in LONG_VIDEO_RESOURCE_ROUND.md.710Python/9skip,82frontend,build/lint pass. Actual MP4/editor inspected. No commits/pushes.

17:41 user approved the reviewed long-video RAM/CPU round and requested an achievements summary. Recovered original approval;710Python/9skip,82frontend,build/full browser acceptance passed before publication. Stream safety and resumable runner published separately, followed by measured achievements/docs. Autosave request starts a separate local review round, not included in these commits.

17:49 autosave local review: existing local save preserved; added status/time, manual flush/lifecycle flush, best-effort previous valid snapshot, confirmation restore and corrupt-current fallback notice. Invalid/quota writes preserve stored current where setItem fails, JSON rescue tested.87frontend/build/full acceptance plus reload/restore/corruption/quota journey pass; screenshots inspected. Backend unchanged from710/9skip. Single current slot and simultaneous-tab limitations remain. No autosave commit/push.

18:11 user approved reviewed browser autosave and asked for a silent icon/no distracting popups plus optional local-disk autosave. Current reviewed state published as focused storage,UI and documentation commits.87frontend/build/full acceptance rechecked. Silent/disk changes remain separate and require review before publication.
