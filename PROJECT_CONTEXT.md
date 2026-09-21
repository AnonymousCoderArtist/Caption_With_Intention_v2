# Caption With Intention v2 — Project Context

## Overview
CWI transforms closed captions into an expressive, accessible experience (color attribution, word-onset sync, intonation mapping). Python engine + React/TS frontend.

## Branch Status
- **Branch**: `M2-scene-chunk-engine` (current), `master` (up to date)
- **Milestones**: M0 ✅, M1 ✅, M2 ✅, M3 ✅ (145 tests passing)
- **Next**: M4 — Deterministic CI renderer

## Directory Tree
```
engine/
  core/              ← M2: registry, pipeline, ffmpeg, cache
  active_speaker/    ← M3: diarization PRIMARY, face tracking fallback
    active_speaker.py ← ActiveSpeakerTracker class
  alignment/         ← M3+: caption-to-audio alignment
  animation/         ← M3+: caption animation
  asr/               ← M3+: speech recognition
  caption_generation/ ← M3+: caption generation
  diarization/       ← M3: speaker diarization (PRIMARY)
    diarizer.py      ← Diarizer class (pluggable backends: ffmpeg_vad, diarize, pyannote)
    models.py        ← SpeakerSegment, SpeakerLabel (slots dataclasses)
  errors/            ← CWIError, ErrorCategory (13 categories), ProjectCorruptionError
  exporters/         ← M3: SRT/VTT/TTML/ASS exporters
    base.py          ← CaptionExporter base (Plugin-registered)
    srt.py           ← SrtExporter
    vtt.py           ← VttExporter
    ass.py           ← AssExporter
    ttml.py          ← TtmlExporter
  ingest/            ← probe, hash, proxy, full ingest
    ingest.py        ← ingest_media(), ingest_and_update_project(), quick_probe(), MediaIngestResult
    proxy.py         ← generate_proxy(), get_proxy_info(), is_proxy_fresh()
  logging/           ← setup_logging(), JSONFormatter, StageAdapter
  media/             ← probe.py: probe_video(), compute_source_hash(), probe_embedded_captions()
  project/           ← ProjectEngine (create/open/save), format.py (dir structure)
  rules/             ← colors.py (palette), profile_loader.py (design system JSON)
  scenes/            ← shot detection, scenes, chunking, checkpoints
  sound_events/      ← empty (M3+)
  typography/        ← mapping.py: volume_to_size, pitch_to_weight, harmonics_to_width, compute_word_typography
  validation/        ← empty (M3+)
  face_tracking/     ← empty (M3+)
  music/             ← empty (M3+)
  audio_analysis/    ← basic.py: estimate_loudness, estimate_pitch, smooth_signal, analyze_audio_chunk
frontend/            ← React/TS (editor, timeline, preview, inspector, speaker-panel, export-panel) — empty
apps/cli/            ← empty
apps/desktop/        ← empty
tests/
  unit/              ← 145 tests total
    test_foundation.py (31 tests): colors, typography, project format, schema
    test_ingest.py (24 tests): proxy, ingest, quick probe, real video
    test_probe.py: ffprobe, hash, captions
    test_proxy.py: proxy creation, dimensions, freshness
    test_scenes.py (33 tests): shots, scenes, chunking, checkpoint, pipeline
    test_diarization.py (32+2 tests): SRT/VTT/TTML/ASS exporters, SpeakerSegment, SpeakerLabel, Diarizer (3 backends), ActiveSpeakerTracker
  integration/       ← empty
  fixtures/          ← empty
  audio/             ← empty
  timing/            ← empty
  visual_regression/ ← empty
design_systems/caption_with_intention/v1.0/  ← 9 JSON profile files
schemas/             ← schema.py (Pydantic models), project.py (version constants)
scripts/             ← verify_m0.py, verify_m1.py, verify_m2.py
docs/                ← M0_CHECKPOINT.md
config/              ← .gitkeep
captions/            ← .gitkeep
output/              ← .gitkeep
templates/           ← .gitkeep
```

## Key Classes & Functions (Import Paths That Must Stay Valid)

### engine/scenes/models.py
- `SceneType(str, Enum)`: dialogue, action, montage, title_card, transition, unknown
- `Shot(BaseModel)`: id, start, end, shot_type, is_reaction_shot, notes
- `Scene(BaseModel)`: id, start, end, scene_type, shots, dominant_speaker, is_off_camera, notes, override; properties: duration; methods: to_dict()
- `SceneList(BaseModel)`: scenes, total_duration; methods: add_scene(), get_scene_at_time(), to_dict()

### engine/scenes/shot_detection.py
- `ShotBoundary(@dataclass)`: time_sec, confidence; `__repr__`
- `detect_shots(source, threshold=0.3, min_shot_duration=0.5) → list[ShotBoundary]` — FFmpeg `select=gt(scene)` filter
- `detect_shots_via_keyframes(source) → list[ShotBoundary]` — ffprobe keyframe extraction
- `_filter_short_shots(boundaries, min_duration)`

### engine/scenes/chunking.py
- `Chunk(BaseModel)`: index, start, end, overlap_start, overlap_end, notes; properties: duration, overlap_duration
- `ChunkConfig(BaseModel)`: chunk_duration=600, overlap_duration=2, min_chunk_duration=30, max_chunk_duration=600
- `generate_chunks(total_duration, config=None) → list[Chunk]`
- `generate_chunks_lazy(total_duration, config=None)` — generator version (NEW)
- `get_chunk_overlap_regions(chunks) → list[tuple]`
- `split_chunks_for_resume(chunks, completed_indices) → list[Chunk]`
- Constants: DEFAULT_CHUNK_DURATION=600, DEFAULT_OVERLAP_DURATION=2, MIN_CHUNK_DURATION=30, MAX_CHUNK_DURATION=600

### engine/scenes/checkpoint.py
- `StageCheckpoint(@dataclass)`: stage_name, chunk_index, status, timestamps, error, output_path, metadata
- `ChunkCheckpoint(@dataclass)`: chunk_index, start, end, status, stages, output_files, notes; to_dict() uses `hasattr(self, "model_dump")` check
- `MasterCheckpoint(@dataclass)`: project_path, total_duration, total_chunks, completed_chunks, failed_chunks, chunks, pipeline_stages, current_stage_index; properties: is_complete, progress_pct
- `CheckpointEngine`: create_master(), load_master(), create_chunk_checkpoint(), load_chunk_checkpoint(), save_chunk_stage(), mark_chunk_completed(), mark_chunk_failed(), set_total_chunks(), get_pending_chunks(), get_failed_chunks()

### engine/scenes/scene_list.py
- `build_scene_list(source_path, shot_threshold=0.3, min_shot_duration=0.5, scene_gap=5.0, chunk_duration=600) → dict` — Full pipeline
- `shots_to_scenes(shot_boundaries, gap=5.0) → list[Scene]`
- `save_scene_list(scenes, output_path, total_duration)`
- `load_scene_list(path) → dict`
- Constants: DEFAULT_SCENE_GAP=5.0, MIN_SCENE_DURATION=3.0

### engine/media/probe.py
- `probe_video(path) → dict` — ffprobe with -show_format -show_streams
- `parse_probe_data(data) → dict`
- `compute_source_hash(path, chunk_size=65536) → str` — SHA-256
- `probe_embedded_captions(path) → list[dict]`

### engine/ingest/ingest.py
- `ingest_media(source_path, project_dir=None) → MediaIngestResult` — Full pipeline
- `ingest_and_update_project(source, project, project_dir=None) → MediaIngestResult`
- `quick_probe(source_path) → dict` — Lightweight probe + hash

### engine/ingest/proxy.py
- `generate_proxy(source, output_path=None, scale=0.25, preset="ultrafast") → dict`
- `get_proxy_info(proxy_path) → dict`
- `is_proxy_fresh(source_path, proxy_path) → bool`

### engine/project/engine.py
- `ProjectEngine`: create(), open(), save(), add_speaker(), add_event(); property: is_loaded

### engine/project/format.py
- `build_project_structure(base_dir) → Path`
- `save_project_metadata(project, base_dir)`
- `load_project_metadata(base_dir) → dict`
- `is_valid_project_dir(path) → bool`
- Constants: PROJECT_EXTENSION=".ci", METADATA_FILE="project.json", ANALYSIS_DIR, CAPTIONS_DIR, CACHE_DIR, RENDERS_DIR, EXPORTS_DIR, LOGS_DIR, etc.

### engine/errors/errors.py
- `ErrorCategory(str, Enum)`: 13 categories (fatal, recoverable, model_unavailable, insufficient_disk, unsupported_codec, gpu_memory_exhaustion, low_ai_confidence, conflicting_speaker_attribution, malformed_caption_source, output_encode_failure, validation_error, user_override)
- `CWIError`: category, recoverable, stage, details
- Subclasses: ProjectCorruptionError, ModelUnavailableError, LowConfidenceError, ValidationError, OutputEncodeError

### engine/logging/logger.py
- `JSONFormatter(logging.Formatter)`
- `StageAdapter(logging.LoggerAdapter)`
- `setup_logging(log_dir="logs", level=logging.INFO, json_format=True) → logging.Logger`

### engine/rules/colors.py
- MAIN_COLORS (6), SUPPORTING_COLORS (12), color_distance_hex(), generate_minor_palette(), generate_minor_color(), validate_palette_collision(), assign_speaker_color(), get_hero_villain_colors()

### engine/rules/profile_loader.py
- load_profile(), get_main_colors(), get_supporting_colors(), get_typography_profile(), get_sync_profile(), get_elements_profile(), get_exports_profile(), get_music_profile(), get_sound_effects_profile(), get_full_design_system()

### engine/typography/mapping.py
- volume_to_size(volume) → size_pct, pitch_to_weight(pitch) → weight, harmonics_to_width(harmonics) → width, compute_word_typography(...) → dict

### engine/audio_analysis/basic.py
- estimate_loudness(), estimate_pitch(), smooth_signal(), analyze_audio_chunk()

### schemas/schema.py
- Pydantic v2 models: SpeakerCategory(Enum), EventType(Enum), ReviewState(Enum), Word, Style, CaptionEvent, Speaker, VideoInfo, Project

### schemas/project.py
- SCHEMA_VERSION = "ci-project-1", DESIGN_SYSTEM = "caption-with-intention-v1.0"
- PROJECT_SCHEMA (JSON Schema draft-07)

## Dependency Graph
```
engine.scenes.chunking      ← pydantic only
engine.scenes.models        ← pydantic only
engine.scenes.shot_detection ← subprocess + stdlib (will use engine.core.ffmpeg)
engine.scenes.checkpoint    ← json + stdlib
engine.scenes.scene_list    ← chunking, models, shot_detection, engine.media.probe (will use engine.core.pipeline)
engine.media.probe          ← subprocess + stdlib (will add cache)
engine.ingest.proxy         ← engine.errors, engine.logging, engine.media.probe
engine.ingest.ingest        ← engine.errors, engine.logging, engine.media.probe, engine.ingest.proxy, schemas.project (will use ThreadPoolExecutor)
engine.project.engine       ← schemas.project, engine.logging, engine.errors (calls setup_logging at import!)
engine.project.format       ← schemas.project, json
engine.logging.logger       ← stdlib only (self-contained)
engine.errors.errors        ← stdlib only (self-contained)
engine.rules.colors         ← schemas.project, stdlib
engine.rules.profile_loader ← engine.logging, json
engine.typography.mapping   ← engine.rules.profile_loader
engine.audio_analysis.basic ← numpy only
engine.exporters.base       ← engine.core.registry (Plugin ABC)
engine.exporters.srt        ← engine.exporters.base
engine.exporters.vtt        ← engine.exporters.base
engine.exporters.ass        ← engine.exporters.base
engine.exporters.ttml       ← engine.exporters.base
engine.diarization.diarizer ← engine.core.ffmpeg, engine.diarization.models
engine.diarization.models   ← dataclasses (slots)
engine.active_speaker.active_speaker ← engine.diarization.diarizer, engine.diarization.models
```

## Speaker/Character Design Decision
Speaker diarization is PRIMARY — speech comes from humans, so diarization should drive speaker identification.
Face/video tracking is a FALLBACK only when diarization confidence is low.
Character avatars can be anything (cartoon faces, dinosaurs, custom avatars) — not limited to real human faces.
This means: diarization → confidence check → face tracking only as fallback.

## Design Decisions
1. Design constants in `design_systems/` JSON, loaded via profile_loader — never hard-coded
2. Checkpoints are JSON files (human-readable)
3. Source video never copied — referenced by path only
4. Proxy videos for fast analysis (25% scale)
5. Chunked processing with overlap (default 10-min chunks, 2s overlap)
6. Schema version `ci-project-1` enforced at project open
7. Error classification with 13 categories + recoverable/fatal
8. Structured JSON logging with stage context
9. Pydantic v2 for data models
10. `ProjectEngine.__init__` calls `setup_logging()` at import (side effect — note for refactoring)
11. Speaker diarization is PRIMARY (speech comes from humans); face/video tracking is FALLBACK only when confidence is low; character models can be any avatar

## Key Patterns for Optimization
- **Plugin/Registry**: `engine.core.registry` — `__init_subclass__` auto-registration
- **Pipeline**: `engine.core.pipeline` — `PipelineStage` ABC, `Pipeline` runner
- **FFmpeg utility**: `engine.core.ffmpeg` — centralized subprocess management
- **Caching**: `engine.core.cache` — MemoryCache with TTL, cached() decorator
- **Slots**: dataclasses use `@dataclass(slots=True)`, Pydantic models use `model_config["slots"] = True`
- **Parallelism**: ThreadPoolExecutor for I/O-bound ops, ProcessPoolExecutor for CPU-bound
- **Lazy loading**: generator versions of chunk generation

## Empty Directories (Intended Purpose)
- engine/active_speaker/ — **M3 DONE**: Active speaker tracking (diarization PRIMARY, face tracking FALLBACK)
- engine/alignment/ — Caption-to-audio alignment (M3+)
- engine/animation/ — Caption animation (M3+)
- engine/asr/ — Automatic speech recognition (M3+)
- engine/caption_generation/ — Caption generation pipeline (M3+)
- engine/diarization/ — **M3 DONE**: Speaker diarization (PRIMARY) with pluggable backends
- engine/exporters/ — **M3 DONE**: SRT/VTT/TTML/ASS export
- engine/validation/ — Validation rules (M3+)
- engine/face_tracking/ — Face tracking (M3+): FALLBACK when diarization confidence is low
- engine/music/ — Music analysis (M3+)
- engine/sound_events/ — Sound event detection (M3+)
- apps/cli/ — CLI application
- apps/desktop/ — Desktop application
- frontend/editor/, frontend/timeline/, etc. — React components
- tests/integration/ — Integration tests
- tests/fixtures/ — Test fixtures
- scripts/.gitkeep, captions/.gitkeep, etc. — Placeholders

## Test Commands
```bash
# Full test suite
python -m pytest tests/ -x -q

# Verification scripts
python scripts/verify_m0.py
python scripts/verify_m1.py
python scripts/verify_m2.py
python scripts/verify_m3.py
```

## pyproject.toml Key Dependencies
pydantic>=2.0, ffmpeg-python>=0.2, numpy>=1.24, scipy>=1.11, soundfile>=0.12, librosa>=0.10, whisper>=20231117, pyyaml>=6.0, click>=8.1, rich>=13.0, httpx>=0.25
Dev: pytest>=7.4, pytest-asyncio>=0.21, pytest-cov>=4.1, ruff>=0.1, mypy>=1.8
GPU: torch>=2.0, torchaudio>=2.0
