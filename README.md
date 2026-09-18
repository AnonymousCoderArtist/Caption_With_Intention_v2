# Caption With Intention v2

> **Caption With Intention (CWI)** is a revolutionary caption design system for movies and TV shows that transforms closed captions from plain text into a rich, expressive experience — conveying **who** is speaking, **when** they speak, and **how** they sound.
>
> Built for the Deaf and hard-of-hearing community. Open source. Open future.

---

## Table of Contents

- [About](#about)
- [The Three Shortcomings](#the-three-shortcomings)
- [Design System](#design-system)
- [MVP Automation](#mvp-automation)
- [Project Structure](#project-structure)
- [Quick Start](#quick-start)
- [Development](#development)
- [License](#license)

---

## About

Around the world, **466 million people** live with hearing disabilities. Since the inception of closed captioning in the 1970s, captions have not meaningfully evolved. What was once an innovative solution is now outdated, and its shortcomings negatively impact the viewing experience.

**Caption With Intention** addresses three core shortcomings:

| Shortcoming | Problem | Solution |
|-------------|---------|----------|
| **Attribution** | Captions don't identify who speaks | Color-coded captions per character |
| **Synchronization** | Captions lag behind dialogue | Word-by-word color sync at word onset |
| **Intonation** | No cues for emotion, volume, pitch | Variable typeface (Roboto Flex) mapping voice → typography |

Developed in partnership with the **Chicago Hearing Society** with community validation from February 2024 to December 2024.

---

## Design System

### Attribution Colors

| Character Tier | Colors | Count |
|---------------|--------|-------|
| **Main Characters** | Yellow `#E5E517`, Cyan `#17E5E5`, Red `#E51717`, Orange `#E58017`, Green `#17E517`, Pink `#E517E5` | 6 |
| **Supporting Characters** | 12 spectrum-derived shades | 12 |
| **Minor Characters** | Pastel tones (S=30%, B=90%) | 24 |

- **Main**: distinct colors spaced far apart on spectrum
- **Hero/Villain**: opposite positions in main palette
- **Supporting**: visually distant from main character colors
- **Off-camera**: same color as speaker + *italic* type

### Synchronization

| Feature | Description |
|---------|-------------|
| **Read-Ahead** | Full white text at 90% opacity shows complete sentence first |
| **Color Sync** | Words change to character color at word onset (not completion) |
| **Pop Motion** | 15% type size pop at each spoken word |
| **Syllable Variation** | Syllable-level animation when alignment confidence is sufficient |

### Intonation Mapping

| Voice Property | Typeface Mapping |
|---------------|-----------------|
| **Volume** | Type size: 3% (whisper) → 5% (normal) → 12% (yell) |
| **Pitch** | Weight: 80-160 Hz → heavy; 160-200 Hz → neutral 400; 200+ Hz → light |
| **Harmonics** | Width: low harmonics → wide; high harmonics → narrow |
| **Baseline** | 160-200 Hz → Roboto Regular 400 |

### Caption Box & Work Area

| Parameter | Value |
|-----------|-------|
| Caption box | 90% black opacity |
| Work area | Lower 20% of frame |
| Max lines per frame | 2 |
| Type size range | 3% – 12% of screen height |
| Baseline type size | 5% of screen height |
| Typeface | Roboto Flex (variable font) |

---

## MVP Automation

This project is the **open-source automation engine** for the Caption With Intention design system. It turns published design rules into a deterministic, local-first, AI-assisted caption production system.

### Architecture

```
┌──────────────────────────────────────┐
│ Desktop UI (React + TypeScript)      │
└──────────────┬───────────────────────┘
               │ IPC / WebChannel
┌──────────────▼───────────────────────┐
│ Python Orchestration Layer           │
├──────┬──────────────┬────────────────┤
│ FFmpeg│  AI/Signal  │  CI Rules      │
│ Probe │ Analysis    │ Engine         │
└──────┴──────────────┴────────────────┘
               │
┌──────────────▼───────────────────────┐
│ Canonical CI Project JSON + SQLite   │
└──────────────┬───────────────────────┘
               │
    ┌──────────┴──────────┐
    │                     │
┌───▼──────┐     ┌───────▼──────┐
│ SRT/VTT/ │     │ Burn-in      │
│ TTML/ASS │     │ Render (FFmpeg)│
└──────────┘     └──────────────┘
```

### Key Principles

1. **Deterministic rules** — colors, timing, typography enforced by renderer, not invented by AI
2. **AI is assistive** — proposes metadata; every decision is editable
3. **Local-first** — runs offline after models are installed
4. **Two distribution paths** — compatibility sidecar (SRT/VTT/TTML/ASS) and burned-in visual CI video

### Milestones

| Milestone | Description | Status |
|-----------|-------------|--------|
| M0 | Project foundation (structure, profiles, core engine) | ✅ Complete |
| M1 | Media ingest and metadata | 🔲 Pending |
| M2 | Scene/chunk engine | 🔲 Pending |
| M3 | Caption import/export (SRT/VTT/TTML/ASS) | 🔲 Pending |
| M4 | Deterministic CI renderer | 🔲 Pending |
| M5–M20 | AI pipeline, editor UI, export, packaging | 🔲 Pending |

---

## Project Structure

```
Caption_With_Intention_v2/
├── README.md                     # This file
├── CAPTION_WITH_INTENTION.md     # Full design system documentation
├── Caption-With-Intention_Design-System_V1.0.pdf  # Official design system PDF
├── CaptionWithIntention_Automation_MVP_Spec.md     # MVP engineering spec
├── pyproject.toml                # Python project configuration
├── design_systems/
│   └── caption_with_intention/
│       └── v1.0/                 # Design system profiles (JSON)
│           ├── profile.json
│           ├── colors.json
│           ├── typography.json
│           ├── synchronization.json
│           ├── elements.json
│           ├── exports.json
│           ├── exceptions.json
│           ├── music.json
│           └── sound_effects.json
├── engine/                       # Python engine modules
│   ├── media/                    # FFmpeg probing & ingest
│   ├── project/                  # Project engine (create/open/save)
│   ├── rules/                    # Color, palette, profile loaders
│   ├── typography/               # Audio → typography mapping
│   ├── audio_analysis/           # Loudness, pitch, harmonics
│   ├── logging/                  # Structured JSON logging
│   ├── errors/                   # Error classification
│   ├── scenes/                   # Shot detection & chunking
│   ├── asr/                      # Speech recognition
│   ├── diarization/              # Speaker identification
│   ├── renderer/                 # CI visual rendering
│   ├── exporters/                # SRT/VTT/TTML/ASS export
│   └── ...
├── schemas/                      # Canonical data model definitions
├── frontend/                     # React + TypeScript UI
│   ├── editor/
│   ├── timeline/
│   ├── preview/
│   ├── inspector/
│   └── ...
├── apps/                         # Desktop & CLI apps
├── tests/                        # Unit, integration, fixture tests
├── docs/                         # Documentation & checkpoints
├── scripts/                      # Automation & verification scripts
├── captions/                     # Caption outputs
├── config/                       # Project configuration
├── output/                       # Final deliverables
├── templates/                    # Color/style templates
├── .gitignore
└── .venv/                        # Python virtual environment
```

---

## Quick Start

### Prerequisites

- Python ≥ 3.11
- FFmpeg (with libx264, libx265, libass)
- Node.js ≥ 18 (for frontend development)

### Setup

```bash
# Create virtual environment
uv venv .venv

# Install dependencies
uv pip install -e .

# Or install manually
.venv/bin/pip install pydantic numpy scipy pytest

# Verify installation
.venv/bin/python scripts/verify_m0.py
```

### Running Tests

```bash
.venv/bin/python -m pytest tests/unit/ -v
.venv/bin/python -m pytest tests/integration/ -v
```

---

## Development

### Running the Verification Suite

```bash
.venv/bin/python scripts/verify_m0.py
```

This runs all M0 verification checks:
- Logging system
- Project create/open/save
- Color palette assignment and collision validation
- Typography mapping (volume→size, pitch→weight, harmonics→width)
- Error classification
- Schema validation
- Design system profile loading

### Code Style

- Type hints required on all public functions
- Structured JSON logging via `engine/logging/logger.py`
- Error handling via `engine/errors/errors.py`
- Design constants only in `design_systems/caption_with_intention/v1.0/*.json`

### Commit Convention

- `[M0]` Project foundation milestones
- `[M1]` Media ingest milestones
- `[M4]` Renderer milestones
- etc.

Each milestone is a checkpoint commit for easy rollback and tracking.

---

## License

This project implements the Caption With Intention design system as described in the official design system documentation.

- **Design system material**: Caption With Intention Design System & Caption Guidelines V1.0 (2025.1) — All Rights Reserved
- **Implementation code**: Open source (license TBD — MIT or Apache-2.0 under consideration)
- **Third-party dependencies**: Each verified individually for license compatibility

The design system is implemented as an open-source automation tool. Community contributions are welcome.
