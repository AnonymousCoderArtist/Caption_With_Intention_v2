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
