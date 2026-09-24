# Caption With Intention v2 — Project Context

## Overview
CWI transforms closed captions into an expressive, accessible experience (color attribution, word-onset sync, intonation mapping). Python engine + React/TS frontend.

## Branch Status
- **Branch**: `master`
- **Milestones**: M0 ✅, M1 ✅, M2 ✅, M3 ✅, M4 ✅ (polished), M5 ✅ (editor engine + visual UI), M6 ✅ (ASR + word alignment)
- **Tests**: 388 Python + 19 frontend (all green via `uv run pytest`)
- **Tooling**: uv manages the venv, lockfile (`uv.lock`), and all Python commands (`uv sync`, `uv run`)
- **Next**: M7 — Speaker diarization (spec §M7; default backend is now Nemotron 3 Diarization via audio.cpp — 2026-09-24; cross-chunk identity reconciliation + spec exit criteria still to close)

## Directory Tree
```
engine/
  core/              ← M2: registry, pipeline, ffmpeg, cache
  editor/            ← M5 ✅: manual caption editor engine
    __init__.py      ← Editor package marker
    editor.py        ← Editor class (M5 core) — CRUD, undo/redo, copy/paste, multi-select
    api.py           ← EditorAPI — transport-agnostic JSON API service layer
    test_api.py      ← Placeholder for API tests (moved to tests/unit/test_editor_api.py)
  renderer/          ← M4 ✅: deterministic CWI renderer
    renderer.py      ← CwiRenderer class (deterministic ASS + FFmpeg burn-in)
    styles.py        ← ASS color constants (8-digit BGR), style computation
  rules/             ← colors.py (palette), profile_loader.py (design system JSON)
  typography/        ← mapping.py: volume_to_size, pitch_to_weight, harmonics_to_width, compute_word_typography
  audio_analysis/    ← basic.py: estimate_loudness, estimate_pitch, smooth_signal, analyze_audio_chunk
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
  scenes/            ← shot detection, scenes, chunking, checkpoints
  alignment/         ← M6 ✅: aligner.py (VAD refinement: vectorized RMS, adaptive threshold, short-silence merging, ffmpeg video extraction; forced: wav2vec2 CTC span via `gpu` extra), models.py
  asr/               ← M6 ✅: transcriber.py (faster-whisper, lazy-loaded), corrector.py (rule-based transcript correction, gap-aware), models.py
  speech/            ← M6 ✅: pipeline.py (concurrent ASR + diarization + correction; O(n+m) speaker matching; build_editor_payload → editor)
frontend/            ← React/TS (editor, timeline, preview, inspector, speaker-panel, export-panel)
  editor/            ← M5 ✅: React/TypeScript editor UI
    index.html
    package.json
    tsconfig.json
    tsconfig.node.json
    vite.config.ts
    vitest.config.ts
    fonts/
      RobotoFlex.ttf  ← Custom font (from project font asset)
    src/
      main.tsx
      App.tsx          ← Main layout (3-panel)
      styles/global.css ← Global styles
      test-setup.ts
      api/
        client.ts      ← EditorApiClient (transport-agnostic)
        client.test.ts ← API client tests (8 tests)
      components/
        ProjectSummary.tsx
        SpeakerPanel.tsx   ← Speaker CRUD + palette
        EventList.tsx      ← Event listing
        EventEditor.tsx    ← Event/word/syllable editor (primary panel)
        InspectorPanel.tsx ← Typography, animation, box inspectors
        Timeline.tsx       ← Visual timeline tracks
        Toolbar.tsx        ← Undo/redo, copy/paste, selection
      types/
        project.ts       ← TypeScript types mirroring Python schemas
        editor.ts        ← EditorAPI TypeScript stub
        project.test.ts  ← Type validation tests (6 tests)
  timeline/          ← (pending)
  preview/           ← (pending)
  inspector/         ← (pending — see EventEditor + InspectorPanel)
  speaker-panel/     ← (pending — see SpeakerPanel)
  export-panel/      ← (pending)
apps/cli/            ← empty
apps/desktop/        ← empty
tests/
  unit/              ← 385 Python tests, + TypeScript tests in frontend/editor
    test_editor.py (58 tests): undo/redo, speaker/event/word/syllable CRUD, timing, typography, animation, box, palette, scene overrides, multi-select, copy/paste, build_from_transcript (incl. M6 precise-word-timing + provenance)
    test_editor_api.py (26 tests): EditorAPI all methods — project, undo/redo, speakers, events, words, syllables, timing, typography, animation, box, speaker editor, palette, scene overrides, selection, copy/paste, style, build_from_transcript, error handling
    test_renderer.py (40 tests): style computation, ASS color conversion, CwiRenderer generation, speaker attribution, FFmpeg commands
    test_renderer_m4.py (55 tests): read-ahead, word-onset sync, pop animation, SFX/music rules, syllable mode, exception profiles, work area, typography mapping, validation, style-driven rendering, helper functions
    test_foundation.py: colors, typography, project format, schema
    test_ingest.py: proxy, ingest, quick probe, real video
    test_probe.py: ffprobe, hash, captions
    test_proxy.py: proxy creation, dimensions, freshness
    test_scenes.py: shots, scenes, chunking, checkpoint, pipeline
    test_diarization.py: SRT/VTT/TTML/ASS exporters, SpeakerSegment, SpeakerLabel, Diarizer, ActiveSpeakerTracker
    test_alignment.py (16 tests): M6 ✅ Aligner config + VAD refinement on real (ffmpeg-generated) audio
    test_asr.py (12 tests): M6 ✅ ASR models + Transcriber config/lazy-load
    test_corrector.py (13 tests): M6 ✅ transcript correction rules + audit log
    test_speech_pipeline.py (15 tests): M6 ✅ speaker matching, correction in run(), build_editor_payload
  frontend/editor/src/api/client.test.ts (8 tests): API client transport, type validation
  frontend/editor/src/types/project.test.ts (6 tests): TypeScript type validation
  integration/       ← M6: test_m6_pipeline_to_renderer.py (3 tests: ASR→correction→editor→renderer end-to-end, stubbed ASR/diarization)
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

### engine/editor/editor.py
- `Editor`: Undo/redo history, CRUD (speakers, events, words, syllables), property inspectors (typography, animation, box/work-area), timing adjustments, copy/paste style, multi-select with apply_to_selection, build_from_transcript()
- `EditAction`: Undo/redo action record (type, before, after, target)
- Undo/redo properly handles add/remove operations for events, speakers, and words

### engine/editor/api.py
- `EditorAPI`: Transport-agnostic JSON API wrapping Editor. All methods return `{"success": True, "data": ...}` or `{"error": "..."}`. Covers every Editor method: project, undo/redo, speakers, events, words, syllables, timing, typography, animation, box, speaker editor, palette, scene overrides, selection, copy/paste style, build_from_transcript.

### engine/asr/transcriber.py + models.py
- `Transcriber(model="large-v3-turbo", device, compute_type, ...)`: faster-whisper loaded lazily in `_load()` (import-safe); `transcribe()` → `TranscriptionResult` (segments + word-level timestamps/confidence); `transcribe_stream()` chunks long video via ffmpeg (spec §9: 30s chunks, 2s overlap)
- `Word` / `Segment` / `TranscriptionResult`: dataclasses with `to_dict()`

### engine/asr/corrector.py (M6 — transcript correction)
- `TranscriptCorrector(min_confidence=0.5, remove_repeats=True, remove_empty=True, max_repeat_gap=0.25)`: rule-based, no ML; `correct(words) → CorrectionReport` (cleaned words + audit log with original/proposed/reason/rule_id per spec §2.2)
- Rules: `repeat-collapse` (ASR stutter — only when the duplicate is within `max_repeat_gap` seconds; "no ... no" with a long gap is kept as intentional), `empty-drop`, `low-confidence` (flag only, never rewords; confidence=0 = "no data", not flagged)

### engine/alignment/aligner.py + models.py (M6 — word alignment)
- `Aligner(audio_path, mode="vad_refinement"|"forced", min_silence_duration=0.15, hop_length=10ms, sample_rate=16000)`
- Audio handling: WAV read via soundfile; mp4/mp3/... extracted to a temp 16 kHz mono WAV via ffmpeg (`cleanup()` removes it); non-16 kHz resampled with linear interpolation
- VAD refinement (default, always available): vectorized per-frame RMS (reshape, ~17x faster than the old Python loop on 10-min audio), adaptive threshold (`0.1 x p95(energies)` — works on quiet and loud recordings alike), silences shorter than `min_silence_duration` merged (a 50ms dip is not a word boundary), start snaps forward to the next onset / end snaps back to the silence-run onset
- Forced mode: wav2vec2 CTC posterior span — first/last non-blank feature frames after duplicate collapse give the word's true acoustic extent (`ctc_word_boundaries()`, pure numpy, unit-tested without torch); requires `uv sync --extra gpu`; falls back to VAD refinement if unavailable
- `AlignedWord` (Word + phonemes, alignment_confidence, boundary_type), `AlignmentResult` (confidence stats, boundary_counts)

### engine/diarization/diarizer.py + nemotron.py (M7 — default backend: Nemotron 3 Diarization)
- `Diarizer(backend="nemotron")` — DEFAULT. NVIDIA Nemotron 3 Diarization (~100M-param open-weights transformer, OpenMDW-1.1, released 2026-09-23) run through the audio.cpp CLI (`audiocpp_cli --task diar --family nemotron_3_diar`, CPU backend). Up to 8 speakers, overlap-aware, real per-turn confidence (0–1)
- `engine.diarization.nemotron` — resolution + IO: `resolve_cli()` (kwarg → `CWI_AUDIOCPP_CLI` env → PATH → dev build under `tools/nemotron-bench`), `ensure_model()` (one-time ~102 MB Q8_0 GGUF download from Hugging Face into `~/.cache/caption_with_intention/models/`, then offline), `parse_turns_file()` (audio.cpp `--turns-out` JSON → `SpeakerSegment`; start_sample/end_sample ÷ 16000 → seconds), `run_diarization()` (subprocess + timeout `max(180, 120 + 0.75×duration)`)
- Graceful degradation: missing CLI / model / download failure / CLI error → falls back to `ffmpeg_vad` (never crashes)
- `_prepare_16k_wav()` shared by nemotron + diarize backends (existing 16 kHz WAV used in place; else ffmpeg extraction; non-16 kHz WAVs re-extracted)
- `backend="diarize"` — old default (Silero VAD + 5-dim audio fingerprint, zero-dependency), now an opt-in fallback
- Measured on 4-core / 8 GB CPU: ~1 min per 10-min chunk, peak RSS ~460 MB (`tools/nemotron-bench/RESULTS.md`; repro via `tools/nemotron-bench/run_bench.sh`)
- Dev assets (gitignored): `tools/nemotron-bench/` — audio.cpp source+build, GGUF weights, bench WAVs, results

### engine/speech/pipeline.py (M6 — pipeline + editor handoff)
- `SpeechPipeline(asr_model, diarize_backend, align_mode, correct_transcript=True, min_confidence=0.5, ...)`: ASR + diarization run concurrently (ThreadPoolExecutor), O(n+m) two-pointer speaker matching (was O(n*m); ties keep earliest-listed segment — verified against a brute-force reference), then rule-based correction
- `run()` → `{transcription, diarization_segments, corrections, speaker_count, ...}`; `run_with_alignment()` adds the Aligner pass
- `build_editor_payload(result)` → `{"transcript", "speakers"}` for `EditorApi.build_from_transcript()` — segment→word grouping is O(log W) per segment via bisect; precise word timing + provenance survive into the editor project (M6 exit criteria, verified by tests/integration/test_m6_pipeline_to_renderer.py)

### engine/renderer/renderer.py
- `CwiRenderer`: Deterministic ASS generation + FFmpeg burn-in. All M4 visual rules: read-ahead, word-onset sync, pop animation, syllable mode, exception profiles, SFX/music rules, work area positioning, style-driven rendering
- `_compute_opacity_color(opacity, base_hex)` → ASS color string
- `_format_pop_scale(scale)` → ASS \fscx/\fscy tag string
- `_build_syllable_overlays(event, speaker, speaker_color_ass, pop_tag, font_tag)` → list[dict]
- `_get_exception_toggles(event)` → dict[str, bool]

### engine/renderer/styles.py
- `WHITE_90_PCT = "&HE6E6E6E6"`, `WHITE_SOLID = "&HFFFFFFFF"`, `BLACK_90_PCT = "&HDE000000"`, `BLACK_SOLID = "&H00000000"` — 8-digit ASS BGR format

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
engine.diarization.diarizer ← engine.core.ffmpeg, engine.diarization.models, engine.diarization.nemotron
engine.diarization.nemotron ← stdlib only (subprocess + urllib)
engine.diarization.models   ← dataclasses (slots)
engine.active_speaker.active_speaker ← engine.diarization.diarizer, engine.diarization.models
engine.editor.editor        ← schemas.project (Pydantic + stdlib)
engine.editor.api           ← engine.editor.editor (transport-agnostic wrapper)
engine.renderer.renderer    ← schemas.project, engine.renderer.styles, engine.core.ffmpeg (Pydantic + subprocess)
engine.renderer.styles      ← schemas.project (constants)
engine.asr.models           ← dataclasses (self-contained)
engine.asr.transcriber      ← stdlib; faster_whisper LAZY (asr extra)
engine.asr.corrector        ← engine.asr.models (stdlib only)
engine.alignment.models     ← engine.asr.models (dataclasses)
engine.alignment.aligner    ← numpy, soundfile; torch/transformers LAZY (forced mode only, gpu extra)
engine.speech.pipeline      ← engine.asr.*, engine.diarization.*, engine.alignment.*
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
- engine/alignment/ — **M6 DONE**: ASR word refinement (VAD refinement always available; forced wav2vec2 via `gpu` extra)
- engine/animation/ — Caption animation (M3+)
- engine/asr/ — **M6 DONE**: faster-whisper transcription (lazy) + rule-based transcript correction
- engine/caption_generation/ — Caption generation pipeline (M3+)
- engine/diarization/ — **M3 DONE / M7 DEFAULT BACKEND**: Speaker diarization (PRIMARY), default = Nemotron 3 Diarization (open-weight, via audio.cpp CPU), pluggable backends
- engine/editor/ — **M5 DONE**: Manual caption editor engine (Editor class, undo/redo, CRUD, copy/paste)
- engine/exporters/ — **M3 DONE**: SRT/VTT/TTML/ASS export
- engine/renderer/ — **M4 DONE**: Deterministic CWI renderer (ASS generation, FFmpeg burn-in)
- engine/validation/ — Validation rules (M3+)
- engine/face_tracking/ — Face tracking (M3+): FALLBACK when diarization confidence is low
- engine/music/ — Music analysis (M3+)
- engine/sound_events/ — Sound event detection (M3+)
- engine/speech/ — **M6 DONE**: concurrent ASR + diarization + correction pipeline; build_editor_payload() → editor handoff
- apps/cli/ — CLI application
- apps/desktop/ — Desktop application
- frontend/editor/ — React editor components (M5 UI integration — pending)
- frontend/timeline/, frontend/preview/, frontend/inspector/, frontend/speaker-panel/, frontend/export-panel/ — React components (pending)
- tests/integration/ — Integration tests
- tests/fixtures/ — Test fixtures
- scripts/.gitkeep, captions/.gitkeep, etc. — Placeholders

## Tooling — uv (authoritative)
All Python tooling goes through uv: venv (`.venv/`), lockfile (`uv.lock`), installs, test and script runs.
```bash
uv sync --extra dev                  # create .venv + install (creates uv.lock)
uv sync --extra dev --extra asr      # + faster-whisper
uv sync --extra dev --extra diarization
uv sync --extra dev --extra gpu      # + torch, torchaudio, transformers (forced alignment)
```

## Test Commands
```bash
uv run pytest tests/ -q              # full suite (388 tests)
uv run pytest tests/unit/ -v
uv run pytest tests/integration/ -v
uv run ruff check engine/            # lint (dev extra; [tool.ruff.lint] ignores UP045 to keep Optional[...] style)
uv run python scripts/verify_m0.py
```

## pyproject.toml Key Dependencies
Core: pydantic>=2.0, numpy>=1.24, soundfile>=0.12
Dev: pytest>=7.4, pytest-asyncio>=0.21, pytest-cov>=4.1, ruff>=0.1, mypy>=1.8
asr: faster-whisper>=1.0
diarization: pyannote.audio>=3.0, silero-vad>=0.3
gpu: torch>=2.0, torchaudio>=2.0, transformers>=4.40
(Past unused hard deps — whisper, scipy, librosa, ffmpeg-python, pyyaml, click, rich, httpx — were removed in the uv migration; the code never imported them. ffmpeg is a system binary, not a Python dep.)
