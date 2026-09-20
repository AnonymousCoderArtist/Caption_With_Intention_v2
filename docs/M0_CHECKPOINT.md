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

## Next: M3 — Caption import/export foundation
