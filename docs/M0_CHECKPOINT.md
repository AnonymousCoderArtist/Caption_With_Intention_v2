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

## Branches
- main: d2bf8be (current, up to date with origin/main)
- master: d2bf8be (up to date with origin/master)

## ✅ M0 STATUS: DONE
## ✅ M1 STATUS: DONE

## Next: M2 — Scene/Chunk Engine (pending user go-ahead)
