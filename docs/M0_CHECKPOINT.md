"""Caption With Intention — M0 checkpoint README.

This file documents the current build state for easy checkpoint recovery.
"""

# M0 Checkpoint — Project Foundation COMPLETE
# ==============================================

## ✅ Completed
- [x] Full directory structure created (matches spec §19)
- [x] pyproject.toml with all dependencies
- [x] Design system profiles (8 JSON files in design_systems/caption_with_intention/v1.0/)
- [x] Core data model (schemas/project.py, schemas/schema.py)
- [x] Project engine (engine/project/engine.py — create/open/save)
- [x] Project file format utilities (engine/project/format.py)
- [x] Structured JSON logging (engine/logging/logger.py)
- [x] Error classification (engine/errors/errors.py — 11 categories)
- [x] Color/palette engine (engine/rules/colors.py)
- [x] Profile loader (engine/rules/profile_loader.py)
- [x] Basic audio analysis (engine/audio_analysis/basic.py)
- [x] Media probing via FFmpeg (engine/media/probe.py)
- [x] Typography mapping (engine/typography/mapping.py)
- [x] Unit tests (31 tests, 29 passing)

## ✅ M1 — Media Ingest and Metadata COMPLETE
- [x] Video probing (duration/fps/resolution via ffprobe)
- [x] Audio stream probing (codec, sample rate, channels, language)
- [x] Duration/fps/resolution extraction
- [x] Embedded subtitle discovery
- [x] Source integrity hash (SHA-256)
- [x] Proxy generation (low-resolution FFmpeg proxy for fast analysis)
- [x] Ingest orchestrator (engine/ingest/ingest.py)
- [x] MediaIngestResult data model
- [x] Project VideoInfo integration (ingest_and_update_project)
- [x] Quick probe (lightweight metadata + hash, no proxy)
- [x] Proxy freshness tracking
- [x] M1 unit tests (24 tests)
- [x] M1 verification script (scripts/verify_m1.py)
- [x] All tests pass against real Buzz Lightyear trailer video

## Git Checkpoints
- `bff7bc6` — baseline project state with spec and font
- `a4394dd` — M0: Project foundation
- `d2bf8be` — Merge: master → main (M0 complete)
- `57c9394` — M1: Media ingest and metadata

## Branches
- main: 57c9394 (current)
- master: d2bf8be (up to date with origin/master)

## ✅ M2 — Scene/Chunk Engine COMPLETE
- [x] Shot detection (FFmpeg scene analysis)
- [x] Scene list (shots → scenes → chunks)
- [x] Adaptive chunking with overlap
- [x] Persistent checkpoint files
- [x] Resume/retry workflow
- [x] Modular architecture (engine/core/ registry, pipeline, ffmpeg, cache)
- [x] Memory optimization (slots on dataclasses + Pydantic models, ~80% reduction)
- [x] Caching layer (probe_video mtime-based cache, MemoryCache with TTL)
- [x] Parallel processing (ThreadPoolExecutor for probe+hash in ingest)
- [x] Lazy chunk generation (generate_chunks_lazy generator)
- [x] SceneListPipeline (pluggable stages: ShotDetection → Grouping → Chunking)
- [x] M2 unit tests (33 tests)
- [x] M2 verification script (scripts/verify_m2.py — 5/5 pass)
- [x] All 111 tests pass (M0+M1+M2)

## Git Checkpoints
- `bff7bc6` — baseline project state with spec and font
- `a4394dd` — M0: Project foundation
- `d2bf8be` — Merge: master → main (M0 complete)
- `57c9394` — M1: Media ingest and metadata
- `73200fe` — M2.1: Scene data models and shot detection
- `17b0087` — M2.2: Adaptive chunking engine
- `f44288f` — M2.3: Persistent checkpoint engine
- `4921b48` — M2.4: Scene list builder with shot-to-scene grouping
- `6d118e4` — M2.5: Unit tests and verification script
- `f74f188` — M2.6: Complete scene/chunk engine
- `23f94d2` — M2.7: Modular architecture, caching, memory optimization, parallelism
- `b4fd42d` — M2.8: Speaker design decision (diarization primary)

## Branches
- main: f74f188 (current, M2 complete)
- M2-scene-chunk-engine: same as main (current)
- master: d2bf8be (up to date with origin/master)

## ✅ M0 STATUS: DONE
## ✅ M1 STATUS: DONE
## ✅ M2 STATUS: DONE
## ✅ M3 STATUS: DONE — Caption import/export + speaker diarization

### M3 Completed
- [x] Caption exporters (SRT, VTT, TTML, ASS) — `engine/exporters/`
- [x] Caption exporter base (Plugin-registered) — `engine/exporters/base.py`
- [x] Speaker diarization (PRIMARY) — `engine/diarization/`
- [x] Active speaker tracker (diarization primary, face tracking fallback) — `engine/active_speaker/`
- [x] M3 unit tests (32 tests) — `tests/unit/test_diarization.py`
- [x] M3 verification script — `scripts/verify_m3.py` (7/7 pass)

## ✅ M4 — Deterministic CI renderer

### M4 Completed
- [x] CwiRenderer — deterministic ASS generation + FFmpeg burn-in
- [x] Read-ahead layer (white, configurable opacity via event.style)
- [x] Speaker-colored word overlays (word-onset sync)
- [x] Pop animation (15% default via event.style.pop_scale)
- [x] SFX rules (white, bracketed, no color animation)
- [x] Music rules (white, no word animation)
- [x] 90% black caption box (corrected to 8-digit ASS BGR format)
- [x] Lower 20% work area positioning
- [x] Max two lines enforcement
- [x] Dynamic box sizing
- [x] Type size range (3–12%, 5% baseline)
- [x] Pitch→weight mapping
- [x] Harmonics→width mapping
- [x] Off-camera italic attribution
- [x] Style-driven rendering (pop_scale, read_ahead_opacity from event.style)
- [x] Syllable mode support (per-syllable overlays with fallback)
- [x] Exception profile support (attribution/color layer toggles)
- [x] Speaker validation (warns on unknown speaker IDs)
- [x] ASS color format corrected to 8-digit BGR (&HE6E6E6E6)
- [x] M4 unit tests (95 tests: 76 base + 19 new)

### Polishing Improvements (Post-M4 completion)
- [x] Replaced hardcoded pop_scale (1.15) with event.style.pop_scale
- [x] Replaced hardcoded read_ahead_opacity (0.90) with event.style.read_ahead_opacity
- [x] Fixed WHITE_90_PCT from 6-digit to proper 8-digit ASS BGR format
- [x] Added syllable mode rendering with graceful fallback
- [x] Fixed syllable mode bug: word.syllables (Pydantic attr) not word.get()
- [x] Added exception profile rendering support
- [x] Added helper functions (_compute_opacity_color, _format_pop_scale, _build_syllable_overlays)
- [x] Added speaker validation and warning for unknown IDs
- [x] Added 19 new tests covering all polished features
- [x] Fixed existing test assertions for corrected ASS format
- [x] Committed and pushed (main up to date with origin/main)

## ✅ M4 STATUS: DONE (polished and committed)

## 🔨 M5 — Full manual editor (IN PROGRESS)

### M5 Completed So Far
- [x] Editor class with full CRUD (speakers, events, words, syllables)
- [x] Timing editor (event-level and word-level)
- [x] Typography inspector (size, weight, width, italic)
- [x] Animation inspector (pop_scale, syllable_mode, easing)
- [x] Box/work-area inspector (opacity, padding, breakout)
- [x] Speaker editor (color, category, off-camera)
- [x] Palette assignment
- [x] Scene overrides
- [x] Undo/redo history
- [x] Copy/paste style
- [x] Multi-select with apply-to-selection
- [x] Build from transcript
- [x] Style model expanded (size_pct, weight, width, italic, box_opacity, etc.)
- [x] 55 new tests (330 total, all passing)

### M5 Remaining
- [ ] Visual UI (frontend/editor/)
- [ ] Integration with renderer for real-time preview
- [ ] Full test coverage for edge cases

## Next: M5 — Full manual editor (UI integration)
