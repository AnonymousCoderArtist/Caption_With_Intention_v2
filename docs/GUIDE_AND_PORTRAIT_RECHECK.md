# Guide and portrait recheck, local review

23 November 2026. Approved at18:34IST;portrait paging reconfirmed18:36IST.

## In-app guide

Guide is available on the start screen and the editor topbar. It never opens by itself. Eight topics cover project/source import, the workspace, timing/text, speaker/sound review, appearance, autosave/recovery, rendering and troubleshooting. Close, Escape and Done dismiss it. Optional workspace buttons only change the visible workspace, not project data. Focus returns to the trigger. It is a non-modal reference panel, not an onboarding tour that blocks editing.

The guide states that video import does not run speech analysis, automatic analysis is currently command-line work, final rendering needs the local Python/FFmpeg service, JSON is not an MP4, browser storage is not a disk backup, and not every legacy control changes output. No account, paid resource or cloud service was added.

## Portrait defect found and proposed correction

Existing 9:16 export checks verified dimensions/rotation and playback, not robust narrow-frame caption layout. The extended test exposed a real defect: a long sentence split into two nominal lines, but the oversized second line wrapped again inside libass, causing detached black boxes and overlapping text. The two-line ordinary-film sample also exceeded the nominal lower20% area.

Proposed behavior for portrait only: page long dialogue in source time at word boundaries, retaining original word timings and stored project data. One line appears at a time for each dialogue event. Landscape keeps its existing two-line behavior. Preview and final renderer use the same page selection. Simultaneous-speaker lift counts the height of a portrait page, not the sum of all sequential pages. Export preflight explicitly warns about this paging and remaining safe-area limits.

This changes read-ahead: the entire original long sentence is no longer visible at once in portrait. It is a proposed adaptation for review, not a rule established by the official landscape reference film. Regular baseline size, black box, progressive spoken attribution color and lower placement remain. Exact official-film parity is not claimed. The user approved this behavior before publication.

## Evidence

- Fresh18-second540×960 real-film crop passed small.en+Nemotron analysis in3windows, canonical project import, source-clock preview, actual local UI render, playback and MP4 download. Output is H264540×960 with AAC,18.016seconds. Ten caption events and five model speaker identities were produced; identity and ASR errors remain. The crop is a test source, not a native portrait reference film.
- Synthetic6-second540×960 long-caption stress render before/after inspected. After paging,60frames sampled at10fps had aggregate caption bounds x106..434,y850..926, inside the frame's lower20% and2.5% side margins. This is one ordinary-size fixture, not a universal safe-area guarantee.
- Synthetic portrait overlap render inspected: first speaker low, later speaker above, SFX top. The three-line block exceeds the lower20% work area. Long unbroken words, large manual type, high emphasis and multiple simultaneous items still need editorial review. Nothing silently scales manual type down or drops dialogue to force a fit.
- Existing rotated portrait acceptance still passes. Landscape full acceptance remains green.
-711Python tests passed,9skipped,one pre-existing fixture warning.94frontend tests passed. Production build and full browser acceptance passed. Dependency audit reported zero vulnerabilities. Added guide lifecycle checks to the repeatable browser script and portrait paging/source-time tests in both runtimes.

## Still open after recheck

This is a capable local editor and automation project, not everything complete or certified optimized. Remaining work includes exact reference-film parity, overlapping recognition/identity accuracy, multi-hour actual-model tests on weak hardware, hard resource caps/OOM recovery, editor-integrated analysis jobs, complex scripts/font fallback, complete sidecar UI, installer/model manager and a license inventory. Native OS disk-file chooser permission remains manually unverified. The guide and tests must not be used to imply those items are done.

Official design references: https://captionwithintention.org and https://download.captionwithintention.org/Caption-With-Intention_Design-System_V1.0.pdf . Work-area guidance is in section2.4.3; actual visual reference remains the official film. Caption With Intention is its original creators' design system. Lokesh built the automation.


### Portrait words-at-a-time setting, approved

Auto fit remains the default. Portrait-only selector offers a maximum1..50words per page,including3/5/10. Width can force fewer words,never more than the maximum. Page changes follow first-word onsets; final page ends at the caption end. Stored project includes the count; preview and final render use it. Landscape ignores it. Count validation rejects fractional/out-of-range values. A guide workspace-jump capitalization bug found in this round was also fixed.712Python/9skip,96frontend,build/full browser acceptance pass. Actual18s portrait UI render with3words selected inspected in preview and MP4. Approved18:43IST;long words/manual size/overlap safe-area limits remain.
