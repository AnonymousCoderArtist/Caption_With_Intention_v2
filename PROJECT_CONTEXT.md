# Caption With Intention v2 — Project Context

## Overview
CWI transforms closed captions into an expressive, accessible experience (color attribution, word-onset sync, intonation mapping). Python engine + React/TS frontend.

## Branch Status

### Approved stability revision (2026-11-22)

The user rejected the real-footage motion as unstable and distracting. This supersedes the older held pitch-tail and full-amplitude dock-wave notes below; those describe the previous iteration, not the new target.

- Normal automatically measured speech uses one stable baseline size. AUTO_EMPHASIS_SIZE_RATIO=1.55 suppresses small/noisy size excursions below 7.75% screen-height target; manual sizes, including whispers, remain editable. Automatic width deviations under 15 percentage points are neutralized. This is a conservative automatic inference rule, not a claim that semantic emphasis or whispers are perfectly detected.
- One absolute-time rise/return per letter, no syllable-triggered restart, no positive/negative pitch cancellation, and no held two-word pitch tail. MOTION_SAMPLE_HZ=30, MOTION_RISE_MS=60, MOTION_SETTLE_MS=140 minimum, MOTION_SETTLE_MAX_MS=320, MOTION_CADENCE_OVERLAP_MS=80. Slow words overlap neighboring letter envelopes without a stationary hold.
- MOTION_LIFT_RATIO=0.12 of baseline type height, with only MOTION_PITCH_MOD_RATIO=0.02 pitch modulation, so ordinary default motion stays between 10% and 14% of type height regardless of missing/extreme pitch. The pop_scale control remains a strength control. These are restrained implementation choices for the user's stability review, not exact timing constants published by CWI.
- Emphasis size envelopes use SIZE_RISE_MS=90, SIZE_SETTLE_MS=140. Sustained growth begins only after ESCALATION_HOLD_S=0.45 and stays capped by the existing maximum size. Box width follows the same absolute-time size envelope while its height stays fixed. Line fitting uses the effective rendered sizes, not stale pre-gate sizes.
- Evidence rechecked: official website synchronization/intonation sections, design PDF pages 28-29, and the official launch film's Buzz passage at 12 samples/sec. Videos remain the reference when PDF and footage differ. Re-rendered Duck and Cover (6s) and His Girl Friday (45s) from identical saved payloads; recognition/attribution limitations are unchanged.
- Pixel checks: 139 visible Duck gray-background frames had a single fixed outer box rectangle; a four-letter low-pitch fixture moved each glyph only 3px at 720p, returned flat, and kept glyph heights within a 1px rasterization range. Actual pixel strips inspected in addition to math/tests.
- 17 obsolete exact-tag/held-tail/pitch-cancellation assertions replaced by 28 numerical/time/color/layout checks in test_motion_stability.py. Full suite: 580 passed, 9 skipped. Renderer and new test lint clean. User approved this revision and the reviewed local fixes as several logical commits on 2026-11-22. Recognition limits remain explicit. Next work: speaker attribution/uncertainty review, then website-style UI restyle.

- **Branch**: `main`
- **Milestones**: M0 ✅, M1 ✅, M2 ✅, M3 ✅, M4 ✅ (polished), M5 ✅ (editor engine + visual UI), M6 ✅ (ASR + word alignment)
- **Tests**: 580 Python passed, 9 skipped (`uv run pytest`); frontend not rerun in this verification pass
- **Tooling**: uv manages the venv, lockfile (`uv.lock`), and all Python commands (`uv sync`, `uv run`)
- **M10 ✅ wired (2026-11-22)**: alignment/syllables.py — rule-based syllable splitting, per-word timing (proportional, snapped to acoustic energy dips when audio given), auto word-vs-syllable animation decision; output shape matches editor/renderer syllable dicts. Now wired into SpeechPipeline via attach_pitch_contours() (run_full). Remaining: phoneme-level alignment (needs gpu extra), manual syllable editor UI hookup
- **M9 ✅ wired (2026-11-22)**: intonation.py — per-word loudness/pitch/harmonics → CI typography with cross-word smoothing; estimate_pitch() rewritten (normalized autocorrelation, 80–500 Hz bounded lags, parabolic interpolation). Now wired into SpeechPipeline via attach_intonation() inside run_full(); sizes calibrated scene-relative (see below). Remaining: editor view surface
- **Traveling pitch wave (2026-11-22, his rule: "as the speaker is speaking the words should come up with synchronisation and then come down and next should be done like a wave as they speak")**: every voiced word carries a word-level pitch_hz (schema Word.pitch_hz, through editor _WORD_FIELDS and the payload); smooth_wave() in pitch_contour.py median-filters octave spikes out of the event's syllable+word pitch sequence (interior points only - edge glides stay raw) so offsets connect across word boundaries. Each word rises at its spoken moment, comes down right after, and the next rises in turn: a just-spoken word keeps 60% of its wave offset (WAVE_TAIL_STEP_1), one word later 30% (WAVE_TAIL_STEP_2), then baseline - a crest at the current word with a short falling slope behind it, matching the launch film's "Buzz Lightyear to the rescue!" (an earlier held-positions reading was WRONG; he rejected it as "words still in the air"). **Motion smoothness (his note: "smooth like the original video")**: every rise eases out (libass \t accel EASE_OUT=0.45), every settle/glide is an S-curve (chained ease-in EASE_IN=2.2 to the midpoint + ease-out, _glide_frz), the tail steps are eased glides (TAIL_GLIDE_MS=240) instead of jumps at word onsets, and when speech ends the whole line eases back to the baseline (terminal settle, tail target 0) instead of holding the last word's tail until the event cuts. **Dock-magnification wave (his rule 2026-11-22: "just like the MacBook dock... each one goes up and down with the relative next each right and left side")**: elevation is per LETTER, never per word/syllable chunk - a speech cursor sweeps the current word's letters over its window, the crest amplitude is the pop elevation plus the letter's pitch offset (letter_pitches > syllable pitch > word pitch), and the lift falls off cosine-squared over DOCK_SPREAD_LETTERS=3 letter positions, bleeding slightly into the previous word's tail; unspoken words stay clamped at the baseline ("pop when spoken"). Color sync is letter-granular for every word (the letter joins the speaker color when the cursor reaches it, 40ms fade - their film's sync is letter-granular). Verified frame-by-frame on the Duck and Cover e2e (gray-background render for pixel tracking): crests travel letter by letter with smooth falloff, tail decays continuously, line relaxes flat after the last word.
- **Feed fidelity fixes (2026-11-22, his review of the first e2e frames)**: (1) weight/width now encode the voice's REGISTER, not per-word wobble — per-word pitch estimates are octave-noisy (one narrator measured 95-331 Hz in one sentence) and speech harmonics are near-constant (~0.88 low-dominant), so raw values rendered every word wide with random bold; IntonationAnalyzer now gives every word the scene-median pitch's weight and renders width relative to the scene's median harmonic balance (typical speech = neutral 100). (2) Renderer terminal settle: a split caption's first line used to hold its last word's pop/rise until event end (the next sync point lived on line 2) — a settle interval now starts at the final word's spoken end. (3) Off-camera italic now appears when each word is SPOKEN, not during read-ahead (his rule: "the italic bold will appear when it's spoken, not from earlier"); read-ahead stays plain roman, bold was already onset-gated.
- **Automated data feed ✅ (2026-11-22)**: SpeechPipeline.run_full() = run_with_alignment + attach_intonation + attach_pitch_contours — one call turns any video into an editor payload where sizes, syllable pitch contours and letter sweep data all come from the real audio (no manual annotation). Verified end-to-end on 1951 Duck and Cover narration: uniform narration renders at the 5% baseline, multi-syllable words ride the narrator's measured pitch. Two calibration fixes this required: (1) volume_to_size is now piecewise anchored so loudness 0.5 (normal speech) lands exactly on the 5% baseline (was a linear 3-12% map that put normal speech at 7.5%); (2) IntonationAnalyzer normalizes hot-mastered scenes down so the scene's median word sits at the normal-speech anchor — otherwise evenly loud broadcast audio made EVERY word ~9% and falsely triggered the loud-word sweep/escalation gates. Renderer letter sweep now skips whitespace (ASR word texts carry leading spaces) so per-letter pitch data aligns to the word's letters.

- **Fidelity audit (2026-11-22)**: SFX animate per spec 2.4.4 (white + bracketed, loudness sizing, onset rise); loud bursts (>=10% screen height) break out of the box per spec 2.4.1 (BREAKOUT_SIZE_PCT); sound effects break out at a lower threshold (>=6%, SFX_BREAKOUT_SIZE_PCT) - launch film: big [GASP] has no box, small [Beep] keeps its box; music gets the note symbol on both sides of the description (spec 2.4.5, brackets stripped); sustained loud words escalate in size while held (launch film WHOOOOOA, Style.escalation_rate/max/gate, capped at the 12% spec max); simultaneous speakers stack in start order each in their own color with SFX always the top line (user rule 2026-11-22); syllables carrying pitch_hz ride the voice pitch mid-word (verified on real footage: 1951 Duck and Cover narration tracked with pYIN, syllables visibly rise/dip with the measured pitch; lights up once the analysis pipeline emits per-syllable pitch); a sustained loud word's sync keeps sweeping letter by letter across the scaled-up hold (user rule 2026-11-22), and with Word.letter_pitches the scaled-up letters also ride the pitch wave (same 160-200Hz/25% mapping as the syllable contour); pitch-to-weight and harmonics-to-width ranges matched to the 2.3.9 charts (weight 100-1000, width 25-150)
- **Video-verified fidelity pass (2026-11-22)**: loud words are a spoken-window PULSE (normal before, pop big+bold+raised at onset, hold while spoken, return to original size/position after - verified frame-by-frame against the official CWI videos, which are the source of truth over the PDF); box stays constant height and widens horizontally only during a pulse (letter-spacing on the box spans); captions split to max two lines with a slim gap (2.4.2); box/line-split widths use real Roboto Flex glyph advances (fontTools), not estimates; SFX sits ABOVE overlapping dialogue (explicit margin_v offset - libass collision handling ignores explicit MarginV) and takes the color of the character who makes the sound ([GASP] in the launch film); syllable_mode now defaults ON
- **M8 partial ✅ (2026-11-22)**: audio_analysis/classify.py — YAMNet sound classification (optional `sound-classify` extra, onnxruntime, model auto-downloads from huggingface.co/audiomagic/yamnet-onnx to ~/.cache/cwi; generic-label demotion recovers specific classes like Thunderstorm) + heuristic fallback + energy-segmented region detection. Remaining: wire detected regions into SpeechPipeline as SFX/music events
- **Next**: M7 — Speaker diarization (spec §M7; default backend is now Nemotron 3 Diarization via audio.cpp — 2026-09-24; cross-chunk identity reconciliation ✅ in reconcile.py — remaining: embedding-based matching for chunks without usable overlap, and wiring reconciliation into the M13 long-video runner)

## Multi-speaker verification (2026-11-22)

- Real test: 45-second His Girl Friday scene, multiple people in a jail/press-room conversation; full speech pipeline, Nemotron diarization, faster-whisper small.en, alignment, intonation, pitch contours, editor handoff and FFmpeg render. Selected reproducible-script run: five model speaker identities, 20 caption events, zero inverted/zero-duration word windows. Three events had no matched speaker. Another small.en run produced 27 events, seven unassigned, so run-to-run ASR variation also needs attention. Recognition and attribution are NOT fully verified: transcript errors remain and a model identity count is not ground-truth speaker accuracy.
- Controlled renderer test: three overlapping dialogue speakers in distinct colors, later speakers above earlier ones, attributed SFX on top. Frames and six-second video inspected. This uses scripted captions and does not verify automatic SFX detection or overlapping ASR.
- Speaker turn handoff: payloads now split ASR sentences at changes in word speaker attribution, including unassigned words. This avoids letting majority vote color another person's brief reply. Latest rerun after this fix: 31 events, 12 explicitly unassigned, five identities and zero invalid windows. More unknown events are surfaced rather than hidden by a sentence majority; identity accuracy is still not established.
- Concrete fixes: missing numpy scope in fingerprint diarization; Silero timestamps interpreted as samples rather than milliseconds; alignment snapping cannot invert a word window (40ms minimum fallback for zero-length ASR words); auto speaker colors avoid occupied main palette entries and renderer shares one assignment map; editor honors event types when adding/importing events.
- Fallback fingerprint diarization still failed to separate this film's voices. No speculative tuning retained. Nemotron requires the audio.cpp CLI and a model download; it ran locally without account access or a paid service.
- Reproduce: `CWI_AUDIOCPP_CLI=/path/to/audiocpp_cli uv run python scripts/verify_multispeaker.py clip.mp4 --output /tmp/cwi-review`. The script defaults to small.en for an affordable CPU diagnostic run, not the production ASR default. For audio.cpp, configure `-DAUDIOCPP_MODEL_SET=custom -DAUDIOCPP_MODELS=nemotron_3_diar` to avoid building unrelated models.
- Eight regression tests added across test_multispeaker_regressions.py and test_speaker_turn_payload.py. At that stage: 569 passed, 9 skipped; after the stability revision: 580 passed, 9 skipped. No new ruff diagnostics against HEAD in touched engine files; existing warnings remain. No claim that everything is verified. UI website restyle remains queued.

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
  audio_analysis/    ← basic.py: estimate_loudness, estimate_pitch, smooth_signal, analyze_audio_chunk; intonation.py (M9); pitch_contour.py (M10 feed)
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
  asr/               ← M6 ✅: transcriber.py (faster-whisper, lazy-loaded), corrector.py (rule-based transcript correction, gap-aware), models.py; backends.py (pluggable factory), parakeet.py (Parakeet TDT via onnx-asr, CPU-first), longform.py (shared chunk extraction)
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
    test_renderer_m4.py (65 tests): read-ahead, word-onset sync, pop animation, SFX/music rules, syllable mode, exception profiles, work area, typography mapping, validation, style-driven rendering, helper functions
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
- volume_to_size(volume) → size_pct — piecewise anchored: loudness 0.5 (normal speech) → 5% baseline, [0,0.5] → 3-5%, [0.5,1] → 5-12%
- pitch_to_weight(pitch) → weight, harmonics_to_width(harmonics) → width, compute_word_typography(...) → dict

### engine/audio_analysis/basic.py + intonation.py (M9)
- estimate_loudness(), estimate_pitch() (rewritten 2026-11-22: normalized autocorrelation, bounded lags, parabolic interpolation, clarity gate), smooth_signal(), analyze_audio_chunk()
- `estimate_harmonic_energies(chunk, sr, cutoff_hz=1000)` — FFT low/high spectral split (0-1)
- `IntonationAnalyzer(harmonic_cutoff_hz, smooth_window, smooth_method)`: analyze(audio, sr, words) / analyze_file(path, words) → IntonationResult; per-word loudness/pitch/harmonics smoothed across words → compute_word_typography; words <40ms or silent marked reliable=False (excluded from smoothing); scene-relative calibration scales hot scenes down so the median word lands at the normal-speech anchor (loudness 0.5 → 5% baseline) while quiet scenes keep absolute levels — the WordIntonation.loudness field keeps the raw measurement, typography uses the calibrated value; weight/width are voice-register stabilized (scene-median pitch → weight for all words; width relative to scene-median harmonic balance, neutral 100 for typical speech)
- `WordIntonation` / `IntonationResult` dataclasses with to_dict()

### engine/audio_analysis/pitch_contour.py (M10 — automated pitch feed)
- `span_pitch(audio, sr, start, end)` — median autocorrelation pitch over a span
- `attach_syllable_pitch(words, audio, sr)` — per-syllable pitch_hz for syllable-animated words
- `letter_pitches_for_word(audio, sr, start, end, text, size_pct, syllable_count)` — per-letter Hz for single-syllable held loud words (same gate/hold rules as the renderer sweep); aligns to the word's non-space letters
- Wired by `SpeechPipeline.attach_pitch_contours()`; respects the M10 use_syllable_animation decision

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

### engine/asr/backends.py + parakeet.py + longform.py
- `create_asr_engine(backend, model=None, device, **kwargs)` — factory; backends: `faster_whisper` (default) and `parakeet`; `compute_type="int8"` maps to ONNX `quantization="int8"` on the parakeet backend
- `ParakeetTranscriber(model="nemo-parakeet-tdt-0.6b-v3", quantization, device, language)` — onnx-asr lazy-loaded (parakeet extra); interface-compatible with Transcriber; token→word grouping with word-level timestamps + geometric-mean confidence; English-only models (v2, rnnt) reject other languages; transcribe_stream() offsets times onto the source timeline (unlike the whisper backend's chunk-relative times)
- `tokens_to_words()`, `words_to_segments()` — pure helpers (pause >1.5s or sentence punctuation splits segments)
- Model comparison + sources: docs/ASR_BACKENDS.md (Parakeet TDT v3 ≈41x realtime CPU, 6.75% VoxPopuli WER; Nemotron 3.5 Transcribe is the most accurate open-weight but GPU-only — future tier)
- pyproject extra: `parakeet` (onnx-asr>=0.7); SpeechPipeline takes `asr_backend="parakeet"`

### engine/asr/transcriber.py + models.py
- `Transcriber(model="large-v3-turbo", device, compute_type, ...)`: faster-whisper loaded lazily in `_load()` (import-safe); `transcribe()` → `TranscriptionResult` (segments + word-level timestamps/confidence); `transcribe_stream()` chunks long video via ffmpeg (spec §9: 30s chunks, 2s overlap)
- `Word` / `Segment` / `TranscriptionResult`: dataclasses with `to_dict()`

### engine/asr/corrector.py (M6 — transcript correction)
- `TranscriptCorrector(min_confidence=0.5, remove_repeats=True, remove_empty=True, max_repeat_gap=0.25)`: rule-based, no ML; `correct(words) → CorrectionReport` (cleaned words + audit log with original/proposed/reason/rule_id per spec §2.2)
- Rules: `repeat-collapse` (ASR stutter — only when the duplicate is within `max_repeat_gap` seconds; "no ... no" with a long gap is kept as intentional), `empty-drop`, `low-confidence` (flag only, never rewords; confidence=0 = "no data", not flagged)

### engine/alignment/syllables.py (M10 — syllable splitting + timing)
- `split_syllables(text)` — rule-based English syllabification (V-CV/VC-CV splits, digraphs kept, silent-e, "-le", "-tion" glide merges; documented limits: some vowel-hiatus words like "video" merge)
- `assign_syllable_timings(word, syllables, audio=None, sr=None)` — proportional split; with audio, boundaries snap to RMS energy dips (±30% window) and confidence rises (0.5 + dip-depth/2); text-only confidence 0.4
- `should_use_syllable_animation()` — spec's automatic decision: ≥2 syllables + word ≥0.2s + confidence ≥0.6 (in practice: audio-refined only)
- `syllabify_words(words, audio, sr)` — batch; `WordSyllables` dataclass, syllables as {"text","start","end"} dicts matching editor/renderer shape

### engine/alignment/aligner.py + models.py (M6 — word alignment)
- `Aligner(audio_path, mode="vad_refinement"|"forced", min_silence_duration=0.15, hop_length=10ms, sample_rate=16000)`
- Audio handling: WAV read via soundfile; mp4/mp3/... extracted to a temp 16 kHz mono WAV via ffmpeg (`cleanup()` removes it); non-16 kHz resampled with linear interpolation
- VAD refinement (default, always available): vectorized per-frame RMS (reshape, ~17x faster than the old Python loop on 10-min audio), adaptive threshold (`0.1 x p95(energies)` — works on quiet and loud recordings alike), silences shorter than `min_silence_duration` merged (a 50ms dip is not a word boundary), start snaps forward to the next onset / end snaps back to the silence-run onset
- Forced mode: wav2vec2 CTC posterior span — first/last non-blank feature frames after duplicate collapse give the word's true acoustic extent (`ctc_word_boundaries()`, pure numpy, unit-tested without torch); requires `uv sync --extra gpu`; falls back to VAD refinement if unavailable
- `AlignedWord` (Word + phonemes, alignment_confidence, boundary_type), `AlignmentResult` (confidence stats, boundary_counts)

### engine/diarization/reconcile.py (M7 — cross-chunk identity reconciliation)
- `reconcile_speakers(chunk_segments, min_match_overlap=0.15, merge_gap=0.05)` — per-chunk local labels (source-timeline times) → stable global `spk_N` ids; adjacent chunks linked by mutual speech overlap in the shared region (greedy one-to-one, union-find for transitivity); unmatched locals become NEW global speakers (conservative — never wrongly merges)
- `ReconciliationResult`: segments (relabeled, deduped, sorted), speaker_map {(chunk, local)->global}, global_speakers, matches log, unmatched list
- `merge_duplicate_turns()` — collapses the same speech diarized twice in the chunk overlap (same-speaker only; real simultaneous speech preserved)
- `merge_speakers()` / `split_speaker()` — editor override path (spec M7 exit criteria)
- Embedding-based matching for chunks without usable overlap: TODO

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
- `run()` → `{transcription, diarization_segments, corrections, speaker_count, ...}`; `run_with_alignment()` adds the Aligner pass; `run_full()` = run_with_alignment + attach_intonation (M9 typography) + attach_pitch_contours (M10 syllable/letter pitch) — the fully automated video→CWI path
- `build_editor_payload(result)` → `{"transcript", "speakers"}` for `EditorApi.build_from_transcript()` — segment→word grouping is O(log W) per segment via bisect; precise word timing + provenance survive into the editor project (M6 exit criteria, verified by tests/integration/test_m6_pipeline_to_renderer.py); run_full results also merge typography (size_pct/weight/width), syllables and letter_pitches into payload words, and Editor._WORD_FIELDS carries them into the project

### engine/renderer/renderer.py
- `CwiRenderer`: Deterministic ASS generation + FFmpeg burn-in implementing the CWI Design System V1.0 visually as ONE dialogue line per word/syllable onset interval (single-layer model, no base+overlay doubling): each line carries the full sentence — spoken words in the speaker attribution color (stay colored), unspoken words in white 90% read-ahead, current word RISES 25% of its type height at onset (spec 2.2.3 elevation, not scale - libass has no per-span translate, so the rise is a tiny \frz rotation around an origin 100000px left of the baseline; the rest of the line never moves) and returns over ~300ms; before the first onset the whole line is white 90%; syllable mode colors in syllable by syllable; the 90% black caption box is a separate CwiBox-layer line per caption line (BorderStyle=3, near-invisible text so libass draws the box): one continuous box hugging the full line, constant during pops, scaling with per-word type size (spec 2.4.1-2.4.2); off-camera = same color + italic; Roboto Flex is embedded in the ASS `[Fonts]` section AND staged into a `.cwi-fonts/` dir passed to the subtitles filter as fontsdir (this ffmpeg/libass build ignores [Fonts] attachments - fontsdir is what actually loads the real typeface; attachment fontname uses the family name)
- `_compute_opacity_color(opacity, base_hex)` → ASS `&HAABBGGRR` (ASS alpha is INVERTED: 0=opaque)
- `_format_pop_scale(scale)` → ASS \fscx/\fscy tag string
- `_compose_word_spans(event, screen_height)` → sentence + per-word geometry spans (preserves original spacing/punctuation)
- `_sync_points(event)` → sorted onset times (word or syllable level)
- `_build_timed_lines(event, speaker, speaker_color, screen_height, italic_tag)` → one full-sentence line per onset interval
- `_get_exception_toggles(event)` → dict[str, bool]
- Known approximation: during the ~300ms pop the center-aligned line recenters slightly (per-word absolute positioning would need text measurement)

### engine/renderer/styles.py
- `WHITE_90_PCT = "&H1AFFFFFF"`, `WHITE_SOLID = "&H00FFFFFF"`, `BLACK_90_PCT = "&H1A000000"`, `BLACK_SOLID = "&H00000000"` — 8-digit ASS &HAABBGGRR (alpha inverted: 0x1A = 90% opaque)

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
engine.audio_analysis.intonation ← engine.audio_analysis.basic, engine.typography.mapping, engine.asr.models, numpy, soundfile (ffmpeg for non-WAV)
engine.exporters.base       ← engine.core.registry (Plugin ABC)
engine.exporters.srt        ← engine.exporters.base
engine.exporters.vtt        ← engine.exporters.base
engine.exporters.ass        ← engine.exporters.base
engine.exporters.ttml       ← engine.exporters.base
engine.diarization.diarizer ← engine.core.ffmpeg, engine.diarization.models, engine.diarization.nemotron
engine.diarization.reconcile ← engine.diarization.models (stdlib only)
engine.diarization.nemotron ← stdlib only (subprocess + urllib)
engine.diarization.models   ← dataclasses (slots)
engine.active_speaker.active_speaker ← engine.diarization.diarizer, engine.diarization.models
engine.editor.editor        ← schemas.project (Pydantic + stdlib)
engine.editor.api           ← engine.editor.editor (transport-agnostic wrapper)
engine.renderer.renderer    ← schemas.project, engine.renderer.styles, engine.core.ffmpeg (Pydantic + subprocess)
engine.renderer.styles      ← schemas.project (constants)
engine.asr.models           ← dataclasses (self-contained)
engine.asr.transcriber      ← stdlib; faster_whisper LAZY (asr extra)
engine.asr.parakeet         ← engine.asr.longform, engine.asr.models; onnx_asr LAZY (parakeet extra)
engine.asr.longform         ← engine.media.probe, stdlib
engine.asr.backends         ← factory; backend modules LAZY
engine.asr.corrector        ← engine.asr.models (stdlib only)
engine.alignment.models     ← engine.asr.models (dataclasses)
engine.alignment.aligner    ← numpy, soundfile; torch/transformers LAZY (forced mode only, gpu extra)
engine.alignment.syllables  ← engine.asr.models, numpy
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
12. Speaker color assignment is deterministic (crc32 of speaker id, not hash()) and always respects an explicitly set `Speaker.color` (pydantic model_fields_set)

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

## Editor rework in progress (2026-11-23, uncommitted)

All morning changes remain local, with no commit or push. Detailed checks and reproduction notes are in `docs/EDITOR_WORKING_NOTES.md`. Older completed milestones and diagnostic counts above are historical snapshots, not this working tree's current verification totals.

- Quiet black/white/gold editing shell, local-video composition driven by the source clock, stable per-letter motion, seek/frame-step/move/trim and visual group selection/drag. Empty New, JSON open/save, local autosave and stale-session guards work.
- Caption-only batch move/delete/ripple and split/merge, each atomic with one undo. Word/syllable timing is preserved or proportionally retimed. Source video is never cut by these controls.
- Speaker-review queue separates diarization coverage/competing turns from ASR confidence, supports listen/correct/check/bulk assignment, and preserves flags in saved JSON. This does not establish reliable speaker identity accuracy.
- Local render panel transfers the selected source to the local Python service, shows progress/cancel/retry, plays the actual encoded MP4 with fullscreen, and downloads it. Source/sequence mismatch and captions beyond source trigger preflight warnings. Canonical CLI render is also available. MP4 uses H264/yuv420p/AAC/faststart; old outputs survive failed CLI replacement.
- Preview/final font normalization, baseline and wrapping improved. Manual width reaches box companions; custom-opacity boxes remain one rectangle without seams. Browser bold spacing, music glyph fallback, shaping and overlap layout remain approximate. Final video inspection is required.
- Repeatable `npm run test:smoke` generates synthetic media and verifies keyboard seeking, split/merge,move,undo/redo,speaker review,JSONsave/reopen,status-network recovery,realrender/decode/play/download,390px layout,rotated portrait output,two-hour1000caption ruler/scroll-follow,live-API local restore,and quota-failure JSON rescue. Setup in README. Playwright is development-only.
- Latest integrated checkpoint:660Python passed,9skipped;frontend78passed,production build passes,npm audit0. New/rewritten Python service/structure/batch/review/CLI files pass focused lint. Unrelated legacy lint remains. Node20.19+or22.12+required.
- Still open: broad browser/final parity, automatic diarization identity quality and overlapping ASR/SFX detection, full long-video orchestration, native project-file lifecycle and deployment/packaging. Current local HTTP server is for local development, not internet hosting.

### 2026-11-23 approved editor publication

User reviewed the simplified cards and colored speaker timeline lanes, then approved several logical commits and a push. Final local verification:660Python passed/9documented skips,78frontend passed,production build and browser acceptance pass. Exact preview/final parity and automatic identity accuracy remain unsigned.

### Approved polish publication

Workspace tabs: Edit, Text, Color, Speakers and Export are focused views of one project. User approved separate feature commits and separate pushes on 2026-11-23 at15:54IST. Full reviewed-round checks:663Python passed/9skipped,81frontend passed,production build and browser acceptance passed. Remaining feature commits follow.

### Approved polish publication

Source-video brightness, contrast and saturation now persist and reach final FFmpeg output before subtitles. Browser CSS grade is approximate. Caption colors stay unchanged by the video grade.

### Approved polish publication

Per-visible-character spoken color overrides added to dialogue, overlap and custom captions, including final ASS output, JSON validation, reset and buffered color input. Replacing word text clears positional overrides; undo restores them. Per-character fonts/sizes and complex grapheme shaping are not promised.

### Approved polish publication

Lightweight preview uses15fps caption updates instead of30fps. Timeline packing/tracks are memoized and offscreen cards use rendering containment. Expanded acceptance covers workspaces, character color persistence and grading.4xCPU-throttled smoke passed; no proxy transcode or real-device certification.

### Approved polish publication

Reviewed polish publication complete. Actual45s graded MP4 and selected-letter color were visually checked before approval. Known limits remain: approximate browser grade, codepoint-indexed colors, no per-character font/size, no proxy workflow, no real low-end device certification, and no claim of exact preview/final parity.
