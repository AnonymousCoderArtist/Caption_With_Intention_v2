"""Caption With Intention — M0 checkpoint README.

This file documents the current build state for easy checkpoint recovery.
"""

# M0 Checkpoint — Project Foundation
# ===================================

## Completed
- [x] Full directory structure created (matches spec §19)
- [x] pyproject.toml with all dependencies
- [x] Design system profiles (8 JSON files in design_systems/caption_with_intention/v1.0/)
- [x] Core data model (schemas/project.py, schemas/schema.py)
- [x] Project engine (engine/project/engine.py — create/open/save)
- [x] Project file format utilities (engine/project/format.py)
- [x] Structured logging (engine/logging/logger.py)
- [x] Error classification (engine/errors/errors.py)
- [x] Color/palette engine (engine/rules/colors.py)
- [x] Profile loader (engine/rules/profile_loader.py)
- [x] Basic audio analysis (engine/audio_analysis/basic.py)
- [x] Media probing via FFmpeg (engine/media/probe.py)
- [x] Typography mapping (engine/typography/mapping.py)
- [x] Unit tests (tests/unit/test_foundation.py)

## Next: M1 — Media Ingest and Metadata
# Need: FFmpeg integration tests, source hash verification, proxy generation

## Git Checkpoint
Commit bff7bc6 — baseline project state with spec and font
