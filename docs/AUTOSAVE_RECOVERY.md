# Local autosave and recovery

23November2026, reviewed round after `d321342`, approved at18:11IST. The existing editor already had a300ms browser-local autosave and reload path. This round makes it visible and adds one previous valid snapshot for recovery.

## Behavior

- Saving locally / Saved locally at [time] / Autosave failed status.
- Autosaves project JSON300ms after a state change, for local and API-backed projects. It never stores the source video. Existing API disk-save behavior is unchanged.
- Save locally now forces the current accepted project snapshot into browser storage.
- Page-hide/visibility/before-unload attempt a synchronous flush of the latest accepted snapshot. Storage failure during ordinary unload requests the browser's leave-page warning where supported.
- One previous valid snapshot is retained best-effort. Identical saves do not rotate it. Invalid current bytes never overwrite the valid previous snapshot.
- Recovery panel shows the previous project's name/caption count, provides current JSON download and offers explicit restore with confirmation. Restore resets selection/source-video session state; select the matching video again.
- Corrupt current JSON falls back to a valid previous snapshot on reopen, with a visible recovery notice.
- Quota/unavailable storage is visible and current JSON download remains available. Per-key atomic storage writes preserve the old current snapshot if the new write fails.

## Tests and inspection

87frontend tests passed (5new storage tests), production build and full existing browser acceptance passed. A focused browser journey verified changed notes survive reload, previous snapshot restore, corrupt-primary fallback, visible quota failure and downloadable JSON rescue. Desktop screenshots of saved/recovery, recovered notice and quota failure were inspected. Backend unchanged from710Python passed/9skipped publication checkpoint.

## Limits

Browser-local data belongs to this browser profile/origin, not a portable file or disk backup. Clearing site data/private browsing/browser failure can remove it. The previous copy is best-effort under quota, not a version history. There is still one current session slot, not a multi-project library. Simultaneous tabs can overwrite each other's local copy; use one editing tab. A crash before the debounce/flush, or before an edit is accepted into project state, can lose that newest change. Native input drafts still need commit/blur. Browser unload events are best-effort, not a durability guarantee. Video must be selected again; undo history is not recovered. Download JSON for a durable user-controlled copy.

No cloud services, account sign-in or paid resource added. Approved for publication. The requested silent-icon redesign and optional disk autosave are a separate next round.


## Silent icon and optional disk copy, local review round

This supersedes the visible-strip behavior above, approved for publication at18:19IST.

- A tiny topbar check/spinner is the default. Browser/disk errors change it to a subtle exclamation mark. Autosave never opens a banner, panel, toast or leave-page confirmation. Click the icon to inspect status and recovery controls. Project import/edit feedback unrelated to autosave is unchanged.
- Optional disk save uses the browser's native Save File picker, only on an explicit click. Choose a new JSON file or an existing file you intend to replace. This supplements browser recovery, it does not move it.
- Available only when secure-context `showSaveFilePicker` is supported. This API has limited browser availability; the button detects support and otherwise offers JSON download. No paid service or sign-in is used.
- The initial file selection/access dialog is required. No permission requests are made during editing. Browsers may request access again on a later reconnect, so this is not a promise of permission once forever.
- Connection lasts only for this page session and project. Reload, new/open project and restoring a prior snapshot detach the disk target. Choose the intended file again. Cancelling a replacement picker leaves an existing connection unchanged.
- One write at a time; pending edits coalesce to the newest accepted snapshot. Unchanged settled snapshots are skipped. Saved is reported only after the writable stream closes. Project changes abort writes that have not yet started closing; a close already submitted to the browser may finish with the old snapshot, never the new project's data.
- A disk permission/write/close failure pauses disk writes until explicit reconnect. The icon reports the failure, browser autosave continues independently. This does not detect edits made to the same disk file by other software. Use one editor tab and do not share that target between active editors.
- Browser-local synchronous unload flush remains best-effort. Async disk writes cannot be guaranteed on close/crash. Wait for the saved icon before closing, and check its tooltip for both browser and disk status. Source video, undo history and unfinished input drafts remain outside both saved copies.

Validation: 92frontend tests, production build and full browser acceptance. Focused Chromium journey covered quiet UI, picker cancel, supported/unsupported controls, save/edit/readback through a real origin-private file writable stream with substituted picker/permission wrapper, permission denial without a new picker, independent browser recovery and disconnect on reload. Unit tests cover write serialization/coalescing, denied permission, abort before close on detach, and close failure. The native operating-system file picker and an actual user-visible disk file permission prompt were not exercised by automation. Manual desktop Chrome/Edge validation is still needed for that path. Three desktop states were visually inspected.

API sources: https://developer.mozilla.org/en-US/docs/Web/API/Window/showSaveFilePicker and https://developer.mozilla.org/en-US/docs/Web/API/FileSystemFileHandle/createWritable
