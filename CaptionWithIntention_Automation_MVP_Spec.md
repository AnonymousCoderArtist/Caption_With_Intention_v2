# Caption With Intention — Open-Source Automation MVP Specification

**Document type:** Full MVP / engineering implementation plan  
**Design-system target:** Caption With Intention Design System & Caption Guidelines V1.0 (2025.1)  
**Product goal:** Turn the published Caption With Intention rules into a local-first, open-source, AI-assisted caption production system that works from very short clips through feature-length video and lets an editor manually override every material decision.

## 0. Product definition

This MVP is not a generic subtitle generator. It is a **cinematic accessibility editor and rendering engine** with four properties:

1. **The design system is deterministic.** Colors, work area, typography limits, animation, box behavior, and rule mapping are enforced by a renderer rather than invented by an LLM.
2. **AI is assistive.** AI proposes transcription, alignment, speaker identity, active-speaker attribution, sound events, syllable timing, and other metadata. Every inferred property remains editable.
3. **Local-first and free.** No mandatory cloud API is required. The application should run offline after models are installed; optional cloud/model accelerators can exist later.
4. **Two distribution paths are first-class.** Export a compatibility caption file such as SRT/VTT/TTML/ASS, and separately render the full visual Caption With Intention treatment directly into a new video file. embed it into that

The original PDF located in the cwd (You can refer that) describes a design system rather than an automated captioning program and states that the future goal is AI-based automation deployed open-source and free. The PDF also says the system is meant to evolve through community input, so the software must treat the rules as versioned configuration rather than hard-coded assumptions.

---

# 1. Source-to-product coverage matrix

The PDF table of contents identifies the exact feature surface we must cover (Every feature in detail is given down below this section):

| Source section | MVP implementation | Status at MVP |
|---|---|---|
| 2.1 Attribution | Main/supporting/minor palettes, speaker mapping, off-camera italics | Required |
| 2.1.1 Main colors | Six CI main colors + distance rules + optional hero/villain opposition | Required |
| 2.1.2 Supporting colors | 12 recommended colors + separation from main palette | Required |
| 2.1.3 Main vs supporting | Contrast/distance validation | Required |
| 2.1.4 Minor characters | Pastel/near-white hue system | Required |
| 2.1.5 Off-camera | Same character color + italics | Required |
| 2.2 Synchronization | Read-ahead layer + onset-synced colored layer | Required |
| 2.2.1 Read-ahead | Complete white sentence at 90% opacity | Required |
| 2.2.2 Color sync | Word changes to character color at word onset | Required |
| 2.2.3 Motion | 15% word pop | Required |
| 2.2.4 Syllable variation | Optional syllable-level animation when warranted! | Required |
| 2.3 Intonation | Size + weight + width mapping | Required |
| 2.3.1 Typeface | Roboto Flex (i got it in the cwd) | Required |
| 2.3.2 Variable font | Weight/width and other axes supported by renderer | Required |
| 2.3.3 Volume | Voice/sound level mapped to type size | Required |
| 2.3.4 Size unit | Percent of screen height | Required |
| 2.3.5 Baseline | 5% screen height | Required |
| 2.3.6 Range | 3%–12% screen height | Required |
| 2.3.7 Pitch/harmonics | Pitch→weight, harmonics→width | Required |
| 2.3.8 Baseline weight/width | 160–200 Hz baseline, Regular 400 | Required |
| 2.3.9 Range | Configurable mapping across voice range | Required |
| 2.3.10 Correlation | Combined acoustic → typography mapping | Required |
| 2.4.1 Caption box | 90% black backdrop | Required |
| 2.4.2 Box size | Dynamic to content, max two lines | Required |
| 2.4.3 Work area | Lower 20% with proportional safety margins | Required |
| 2.4.4 Sound effects | White, bracketed, animated/sized by sound | Required |
| 2.4.5 Music | White music descriptor, symbol treatment, no CI dialogue animation/color | Required |
| 3.1 Exceptions | Editor-controlled per-project/scene/event overrides | Required |
| 3.2 Distribution | Burn-in/open caption workflow + compatible sidecar export | Required |
| 3.3 Existing captions | Import existing closed captions as model/fallback/source | Required |
| 3.4 Standards | Preserve conventional caption track as a separate compatibility layer | Required |
| 3.5 Automation | End-to-end automated proposal pipeline + human review (NOT EVERY FEATURE BUT IF ONE FEATURE NEEDED IT)| Required |
| 3.6 Resources | Project includes font/resource management and third-party notices (All available in cwd) | Required |

The PDF (in cwd) states the system is intended to augment rather than replace regulated closed captioning in the near term, and that current decoder limitations make burned-in/open captions an important distribution route for the full system. The product therefore keeps standard caption export and visual burn-in as separate outputs.

---

# 2. Non-negotiable product requirements

## 2.1 Every visual parameter must be editable

The user must be able to override, at minimum:

- transcript text
- punctuation
- caption start/end time
- individual word start/end time
- syllable boundaries and timings
- speaker identity
- speaker category: main / supporting / minor
- speaker role metadata: optional hero / villain / custom
- speaker color
- Roman vs italic
- read-ahead opacity
- caption box opacity
- caption box padding
- caption box dimensions
- work-area position
- safe-area margins
- maximum line count
- line breaks

THE REST are OPTIONAL or are hidden in advanced setting in UI or something if you create frontend
- baseline size
- per-word size
- minimum size
- maximum size
- font weight
- font width
- optical size / grade / slant where supported and appropriate
- pop scale
- pop timing/curve
- syllable mode on/off
- sound-effect text and brackets
- sound-effect timings
- sound-effect size
- music descriptor text
- music timings
- exception flags
- whether a scene uses full attribution, animation-only, or another project-defined profile
- whether an uncertain AI suggestion is accepted/rejected

All changes must be non-destructive and undoable.

## 2.2 Every AI decision must be reviewable

Every inferred object carries:

- source model
- confidence
- timestamp
- editable value
- original proposed value
- correction history

The editor can accept, reject, split, merge, or manually replace the proposal.

## 2.3 Every video length is a supported input

Target classes:

- Short clips: 1–59 seconds
- Shorts/reels: 1–5 minutes
- Social videos: 5–30 minutes
- Episodes/lectures: 30–90 minutes
- Feature-length: 90–240+ minutes
- Very long recordings: technically unbounded by duration, subject to disk, time, and codec/container limits

The pipeline must be chunked, checkpointed, resumable, and memory-bounded.

---

# 3. User workflow

## 3.1 Create project

User selects a video or a folder of videos.

The application reads:

- duration
- frame rate
- dimensions
- pixel aspect ratio if present
- audio streams
- sample rate
- channel layout
- codec/container
- language metadata when available
- existing subtitle/caption tracks when available

No source file is modified.

## 3.2 Choose source captions

Options:

- Auto-transcribe
- Import SRT
- Import VTT
- Import TTML
- Import ASS/SSA
- Extract an existing embedded caption track
- Hybrid: import existing captions and run AI alignment/enhancement

The imported transcript remains the authoritative text source unless the editor chooses AI replacement.

## 3.3 Analyze

Pipeline stages:

1. Media ingest
2. Scene/shot detection
3. Voice activity detection
4. Speech recognition
5. Word-level alignment
6. Speaker diarization
7. Face detection/tracking
8. Active-speaker detection
9. Cross-chunk speaker reconciliation
10. Pitch analysis
11. Loudness/volume analysis
12. Harmonic/spectral analysis
13. Sound-effect detection
14. Music detection
15. Syllable/phoneme alignment where useful
16. Caption-with-intention rule generation
17. Constraint validation
18. AI review queue creation

## 3.4 Review

The editor works in a timeline with:
All professionally edited in new tabs in ui like Da vinci or premier software.
- video preview
- caption preview
- scene list
- speaker/character list
- word timeline
- waveform/loudness
- pitch curve
- harmonic/spectral information
- confidence overlays
- issue list
- inspector panel

## 3.5 Export

Two primary outputs:

A. **Compatibility output**
- SRT
- VTT
- TTML
- ASS/SSA

B. **Visual CI output**
- burn the rendered Caption With Intention layer into a new video file
- preserve source video as the original
- prefer stream-copy for untouched audio where safe
- allow hardware-accelerated video encoding when available

---

# 4. Complete Caption With Intention rule engine

## 4.1 Attribution engine

### Main character palette


Use the published V1.0 concrete values:

- Main Yellow: `#E5E517`
- Main Blue/Cyan: `#17E5E5`
- Main Red: `#E51717`
- Main Orange: `#E58017`
- Main Green: `#17E517`
- Main Pink: `#E517E5`

Assignment rules:

- primary requirement: distinct colors
- when only three main characters exist, maximize separation on the spectrum
- when the project explicitly marks hero and villain, use opposite positions in the main palette
- the editor can override any automatic assignment

**IF POSSIBLE WE CAN CREATE A FUNCTION OR Automated software to select the respective colours using color pallete Opposite in position (If Possible create a function to automatically select these following these rules, 1 for main character and inside one for minor BUT EVERY COLOR should be different)**

### Supporting palette

Use the 12 published V1.0 values:

`#E85C2E`, `#47C2EB`, `#EBC247`, `#5E82ED`, `#C2EB47`, `#8C6BED`, `#82ED5E`, `#CC6BED`, `#47EB70`, `#EB47C2`, `#5EEDC9`, `#ED5E82`.

Assignment rules (If Possible create a function to automatically select these following these rules, 1 for main character and inside one for minor BUT EVERY COLOR should be different):

- select shades between main colors on the spectrum
- preserve visual distance from the main speaker colors
- run a palette collision validator before final export

### Minor palette

Generate pastel/near-white tones using the published V1.0 approach around `S=30%`, `B=90%` and the specified hue family. Keep a deterministic generator so the same project always maps the same character identity to the same color.

### Off-camera

- same speaker-specific color as that character's normal caption
- italic type
- visual attribution remains available even when the speaker is not visible

### Speaker identity

Every caption event must reference a stable speaker ID rather than storing only a raw label.

---

## 4.2 Synchronization engine

### Read-ahead layer

Every dialogue line initially displays as a complete sentence:

- white
- 90% opacity
- readable ahead of speech

### Color-sync layer

Overlay the same text with the speaker's assigned color, but reveal/change color at the **start of the spoken word**.

The timing anchor is word onset, not word completion.

### Pop animation

At the onset of each spoken word:

- scale toward 115% of its current type size
- return to the normal size
- use a smooth configurable easing curve
- default to the published 15% increase

The renderer must preserve word spacing and line geometry while the active word animates.

### Syllable variation

Support a per-word flag:

- `word_mode`
- `syllable_mode`

When syllable mode is enabled, the engine animates syllable units independently using aligned syllable/phoneme timing.

If alignment confidence is low, default to word mode and flag the event for review rather than inventing syllable timing and continue rather than stopping for this. 

---

## 4.3 Intonation engine

### Typeface

Default CI V1.0 typeface: Roboto Flex.

The renderer must support variable-font axes needed by the design system and preserve the font resource in packaged builds.

### Type size

Unit: percentage of **screen height**, not pixels.

Default values:

- baseline: 5%
- minimum: 3%
- maximum: 12%

Mapping should be derived from measured/local voice level and then clamped to the range.

The system must calculate type size against the actual output frame height, so the visual size remains consistent across 1080p, 4K, 8K, and other dimensions, all handled.

### Volume

Represent volume with type size:

- quieter speech → smaller type
- normal speech → approximately baseline size
- louder speech → larger type

Input signals:

- local RMS/energy
- peak
- short-term loudness
- speech-normalized loudness
- optional human override

### Baseline voice range

Use the V1.0 baseline of approximately 160–200 Hz and neutral Roboto Regular 400 for voices in that range.

### Pitch → weight

Use fundamental frequency as the main pitch signal:

- approximately 80–160 Hz → heavier type
- approximately 160–200 Hz → neutral baseline
- approximately 200 Hz+ → lighter type

Use a smoothed mapping rather than frame-to-frame jitter.

### Harmonics → width

Use harmonic/spectral characteristics to control the width axis:

- stronger lower-frequency harmonic content → wider/expanded type
- stronger higher harmonics → narrower/condensed type

The engine must expose both the measured signal and the mapped typography value for editing.

### Combined mapping

Each word/syllable may therefore have:

- size
- weight
- width
- color
- slant/italic state
- animation state

The mapping engine must be deterministic for a fixed source waveform and parameter profile.

---

# 5. Element rules

## 5.1 Caption box

Default:

- black
- 90% opacity
- behind caption text
- background remains visible through the box

Exception:

- very loud/sudden bursts of speech may break outside the box to express intensity/urgency

This must be a configurable event-level property, not an automatic irreversible decision.

## 5.2 Box sizing

The containing box scales with the amount of caption type.

- dynamic width/height
- adequate padding
- ** no more than two text lines in one frame
- line spacing is explicit and editable
- box geometry is recalculated after variable font sizing

## 5.3 Work area

The work area is the lower 20% of the frame.

No CI caption element should extend outside the work area unless an explicit approved exception is active.

Add proportional safety margins to bottom, left, and right. The baseline V1.0 illustration indicates the work-area/safety relationship; the implementation must keep those margins as named configuration values so future revisions can update them.

## 5.4 Sound effects

Sound effects:

- white
- square brackets `[ ]`
- not assigned character colors
- still follow Caption With Intention animation principles
- loud events can grow and pop synchronized with the effect

Examples:

- `[THUNDER]`
- `[DOOR SLAM]`
- `[LAUGHTER]`

The text itself should remain editable because automatic sound labels can be wrong or overly verbose.

## 5.5 Music

Music descriptors:

- white
- use the design-system musical symbol convention shown in the source PDF
- treated like classic captions
- not word-by-word animated
- do not change character color

The exact glyph/symbol is a design asset/rule and should be stored in the V1.0 design profile rather than guessed at runtime.

---

# 6. Exceptions and fallback behavior

## 6.1 Editor discretion

The PDF explicitly allows editors to omit aspects of CI when a particular film would become distracting. Example: some older or intentionally black-and-white films may be better served with animation without character attribution colors. (we can implement this as we can take a screenshot from middle of video and analyze if its black and white or colourful and act accordingly.)

Implement these scopes:

- project profile
- scene profile
- caption-event profile
- single-word override

Possible toggles:

- attribution colors on/off
- synchronization color layer on/off
- pop animation on/off
- variable size on/off
- pitch weight mapping on/off
- harmonic width mapping on/off
- sound-effect animation on/off
- caption-box breakout permission
- Roman/italic override

## 6.2 Existing-caption fallback

When an area is not fully addressed by the design system, use imported/original closed captions as the guidance source.

This is not only a fallback for AI; it is a product feature. Keep the original imported track alongside the CI track and allow side-by-side comparison.

## 6.3 Standards mode

Keep a conventional caption representation as a separate export layer. The CI visual layer is additive and should not silently replace the baseline accessibility track.

---

# 7. Manual editing system — “edit every bit”

The editor must be able to modify the smallest unit that affects the final frame. Each should have a different Tab in UI

## 7.1 Text editing

- insert/delete text
- merge/split caption events
- punctuation
- capitalization
- profanity/spelling fixes
- speaker labels/identity
- SFX/music descriptor text

## 7.2 Timing editing

- event in/out
- word in/out
- syllable in/out
- drag edges
- nudge by milliseconds
- ripple timing
- snap to word onset
- waveform-assisted alignment
- lock timing to imported caption track

## 7.3 Speaker editing

- create/rename speaker
- merge speaker IDs
- split speaker ID
- change speaker category
- assign color
- mark off-camera/on-camera
- mark active speaker
- lock speaker identity for a scene/project

## 7.4 Typography editing

Per event and per word:

- font size
- weight
- width
- optical size/grade where enabled
- italic
- line spacing
- tracking
- horizontal scale if custom mode is enabled
- color
- opacity

The CI profile should prevent edits that violate the published range unless the user explicitly switches to a “Custom/non-CI” mode.

## 7.5 Animation editing

- pop amount
- pop duration
- easing
- color transition point
- color transition duration
- syllable/word mode
- motion disable

## 7.6 Box editing

- opacity
- padding
- width/height constraints
- work-area margins
- vertical offset within allowed area
- breakout permission
- line spacing

## 7.7 Audio analysis overrides

For any word/syllable:

- override measured volume
- override measured pitch
- override harmonic/width value
- freeze a manually chosen value

---

# 8. AI/ML pipeline

## 8.1 Model strategy

Do not build a monolithic “Caption AI.” Use a pipeline of specialized tools. Everything should work on small chunks rather than the whole video.

### Speech

- VAD
- Whisper-family ASR
- forced alignment for word/phoneme timing

### Speakers

- speaker diarization
- voice embeddings
- global speaker reconciliation

### Visual

PLEASE OPTIMIZE THIS BECAUSE IT WILL TAKE COMPUTERS MUCH RESOURCES.
- face detection
- face tracking
- active-speaker detection
- shot/scene boundaries

### Acoustic

- pitch/F0
- loudness/energy
- harmonic/spectral profile

### Non-speech

- sound-event detection
- music detection

### Language-model assistance

A local LLM can be used for:

- cleaning machine transcription while preserving exact spoken meaning
- proposing sound-effect wording
- grouping ambiguous utterances
- suggesting main/supporting/minor roles from project evidence
- explaining low-confidence cases to the editor

The LLM must not be the final authority over timings, colors, or typography rules.

---

# 9. Long-video architecture

## 9.1 Chunking

Never load an entire movie into RAM for analysis.

Recommended strategy:

- process in 5–10 minute analysis chunks
- maintain 1–2 seconds overlap across chunks
- write results to disk immediately
- checkpoint after every pipeline stage

The exact chunk size should be adaptive based on available RAM/VRAM.

## 9.2 Persistent intermediate project

Suggested structure:

```text
project/
  project.json
  source/
  analysis/
    media.json
    scenes.json
    transcript.json
    words.json
    syllables.json
    speakers.json
    faces.json
    active_speaker.json
    loudness.json
    pitch/
    harmonics/
    sound_events.json
    music.json
    confidence.json
  captions/
    ci_events.json
    review_state.json
  cache/
  renders/
  exports/
  logs/
```

## 9.3 Resume support

Every stage is idempotent and checkpointable.

If a 2-hour film reaches 82% and the application closes, reopening the project resumes from the last completed stage rather than restarting the entire pipeline. AUTO SAVE IS IMPORTANT can be turned of in setting but default its on

## 9.4 Global identity reconciliation

Local chunk speaker IDs must be reconciled into global speaker IDs using voice embeddings and optional face identity clues. Use visual evidence if you are not clear about it not always

Example:

```text
chunk 001 speaker_02 ─┐
chunk 002 speaker_01 ─┼─> global Speaker A
chunk 003 speaker_04 ─┘
```

The editor can merge/split identities manually.

## 9.5 Memory and resource limits

The application must:

- stream media instead of reading complete files into memory
- release chunk-level tensors/models when safe
- use low-resolution proxies for visual analysis
- use original-resolution video only during final render
- throttle concurrent ML jobs based on detected resources
- support CPU-only operation
- support optional GPU acceleration

---

# 10. Editor UI
PLEASE NOTE THAT Each editable property should have a independent tab or section just like Preimer or Da vinci editors.
## 10.1 Main workspace

```text
┌─────────────────────────────────────────────────────────────┐
│ Project | Analyze | Review | Export                         │
├───────────────┬────────────────────────────┬───────────────┤
│ Scenes        │ Video + CI Caption Preview │ Inspector     │
│ Speakers      │                            │               │
│ Issues        │                            │               │
├───────────────┴────────────────────────────┴───────────────┤
│ Time ruler / scene markers                                 │
│ Caption event track                                        │
│ Word/syllable timing track                                 │
│ Speaker track                                              │
│ Waveform / loudness                                        │
│ Pitch                                                     │
│ Harmonics / spectral data                                  │
└─────────────────────────────────────────────────────────────┘
```

## 10.2 Scene browser

Each scene shows:

- start/end
- duration
- number of speakers
- confidence issues
- captions needing review
- color/profile override indicator

## 10.3 Speaker/character browser

Each speaker row:

- color swatch
- global ID
- label
- category
- optional role
- confidence
- number of lines
- number of scenes
- on/off-camera statistics

## 10.4 Inspector

The inspector always exposes the exact properties of the current selection.

Selections:

- project
- scene
- caption event
- word
- syllable
- speaker
- SFX event
- music event

---

# 11. Confidence and AI review queue

Create a dedicated review system.

Example queue:

```text
17 speaker attribution conflicts
29 low-confidence sound effects
12 overlapping-speaker intervals
8 impossible/low-confidence word timings
5 captions exceeding work area
3 captions exceeding two lines
11 low-confidence syllable boundaries
```

Each issue opens the exact timestamp with one-click correction options.

All accepted/rejected AI decisions are stored for future project analytics and optional model-improvement experiments.

---

# 12. Preview renderer requirements

The preview must be frame-accurate enough for caption editing.

Requirements:

- play/pause
- frame step
- timecode entry
- loop selected caption
- loop selected word
- playback speed control
- show/hide original captions
- show/hide CI layer
- compare original vs CI
- safe-area overlay
- work-area overlay
- caption box bounds overlay
- word timing markers
- pitch/loudness cursor

The preview should never permanently modify the source video.

---

# 13. Final render/export requirements

## 13.1 Sidecar outputs

### SRT

Export conventional text + timing only. Do not claim full CI visual fidelity because SRT cannot encode the entire variable typography/animation system.

### VTT

Same principle; preserve supported cue formatting only.

### TTML

Use for environments that accept richer caption metadata where appropriate.

### ASS/SSA

Use as an optional styled subtitle interchange. It can represent more styling than SRT but still should not be treated as the canonical CI representation.

## 13.2 Burned-in video

Required for full-fidelity CI output:

```text
original video
    +
CI render overlay
    ↓
new encoded video
```

Requirements:

- never overwrite source unless user explicitly requests it (ADD a option while exporting)
- configurable output container
- configurable codec/quality
- hardware acceleration when available
- audio stream copied when safe
- preserve frame rate unless the user explicitly changes it
- preserve resolution by default
- render at source frame rate
- deterministic output when the same inputs/settings are reused

## 13.3 Export presets

Provide:

- Social/Short
- 1080p
- 4K
- Source resolution
- Custom

And custom controls for:

- codec
- CRF/quality or bitrate
- frame rate
- audio handling
- output path

---

# 14. Tests and quality gates

## 14.1 Deterministic rule tests

Automated tests must cover:

- palette values
- palette assignment stability
- main/support color collision avoidance
- minor color generator
- off-camera italics
- read-ahead opacity = 90%
- baseline size = 5%
- minimum = 3%
- maximum = 12%
- baseline pitch range
- baseline weight 400
- word onset color timing
- pop scale = 1.15
- maximum two lines
- caption box opacity = 90%
- work-area constraint
- SFX white/bracket rules
- music no-color/no-word-animation rule
- exception profiles

## 14.2 Audio tests

Use synthetic voices/signals to verify:

- louder sound produces larger type
- quieter sound produces smaller type
- lower F0 produces heavier type
- higher F0 produces lighter type
- low harmonic dominance produces wider type
- high harmonic dominance produces narrower type
- smoothing prevents visible jitter

## 14.3 Timeline tests

Verify:

- word color starts at onset
- no word is colored before onset
- pop begins at onset
- syllable mode only affects configured words
- line wrapping remains stable during pop

## 14.4 Long-video stress tests

Minimum acceptance set:

- 10-second clip
- 60-second clip
- 10-minute clip
- 60-minute clip
- 120-minute clip

For every test:

- no memory leak that scales linearly with entire media duration
- resume after forced shutdown
- correct global timecode
- no duplicated/missing boundary words
- speaker IDs remain stable after chunk reconciliation

## 14.5 Export regression

For known fixtures:

- compare generated sidecars against expected text/timing
- render reference frames
- use image-based visual regression for caption geometry/style
- verify no clipping
- verify safe-area compliance
- verify exact frame count/duration

---

# 15. Milestone plan — complete MVP

The MVP is intentionally broken into milestones so the system remains testable at every stage.

## M0 — Project foundation

**Deliverables**

- repository
- Python environment
- frontend shell
- desktop packaging skeleton
- CI V1.0 rule profile directory
- project file format
- structured logging
- error reporting

**Exit criteria**

- create/open/save project
- source video path stored without copying it into memory
- project loads after restart

---

## M1 — Media ingest and metadata

**Implement**

- video probing
- audio stream probing
- duration/fps/resolution extraction
- embedded subtitle discovery
- source integrity hash
- proxy generation

**Exit criteria**

Any supported video can be opened and inspected without full decoding into RAM.

---

## M2 — Scene/chunk engine

**Implement**

- shot detection
- scene list
- adaptive chunking
- overlap handling
- persistent checkpoint files
- resume/retry

**Exit criteria**

A 2-hour test video can be partitioned, stopped midway, reopened, and resumed.

---

## M3 — Caption import/export foundation

**Implement**

- SRT reader/writer
- VTT reader/writer
- TTML reader/writer
- ASS/SSA reader/writer
- embedded caption extraction
- canonical conversion into internal event model

**Exit criteria**

Import/export round trips preserve text and timing within the format's precision.

---

## M4 — Deterministic Caption With Intention renderer

**Implement every visual rule before AI**

- read-ahead layer
- white 90% opacity
- speaker-colored overlay
- word-onset sync
- 15% pop
- Roman/italic
- 3–12% type-size range
- 5% baseline
- pitch→weight
- harmonics→width
- 90% black box
- lower 20% work area
- max two lines
- dynamic box sizing
- SFX rules
- music rules
- exception profiles

**Exit criteria**

A handcrafted JSON timeline produces a visually correct CI result without any AI dependency.

---

## M5 — Full manual editor

**Implement**

All of these features in different section or different view tabs with detail property editor.

- caption event editing
- word editing
- syllable editing
- timing editor
- speaker editor
- palette assignment
- typography inspector
- animation inspector
- box/work-area inspector
- scene overrides
- undo/redo
- copy/paste style
- multi-select edits

**Exit criteria**

A human editor can build a complete CI caption project manually from an existing transcript.

---

## M6 — Speech recognition + word alignment

**Implement**

- VAD
- local ASR
- word timestamps
- forced alignment
- confidence
- transcript correction

**Exit criteria**

Auto-generated word timelines are editable and can drive the renderer accurately enough for review.

---

## M7 — Speaker diarization

**Implement**

- local speaker diarization
- voice embeddings
- global speaker IDs
- merge/split speakers
- confidence
- cross-chunk identity reconciliation

**Exit criteria**

Multi-speaker scenes produce stable speaker identities with an editor override path.

---

## M8 — Visual speaker attribution (ONLY USE THIS WHEN THE SPEAKER DIARIZATION Confidence is LOW)

**Implement**

- face detection
- face tracking
- active speaker detection
- audio speaker ↔ face matching
- on-camera/off-camera inference
- conflict reporting

**Exit criteria**

For test scenes, the application can propose who is speaking and whether the speaker is off-camera; uncertain cases are visibly flagged.

---

## M9 — Audio intonation analysis
All of these can be independently shown in differnt view

**Implement**

- loudness/energy analysis
- F0/pitch extraction
- harmonic/spectral analysis
- smoothing
- word-level acoustic aggregation
- mapping into CI typography values

**Exit criteria**

Synthetic test audio passes all volume/pitch/harmonics mapping tests.

---

## M10 — Syllable/phoneme synchronization

**Implement**

- phoneme alignment
- syllable grouping
- confidence
- automatic decision whether word-level or syllable-level animation should be used
- manual syllable editor

**Exit criteria**

The editor can enable syllable variation for selected words and verify the exact timing visually.

---

## M11 — Sound-effect and music pipeline

**Implement**

- non-speech audio detection
- SFX classification
- music detection
- event confidence
- editable SFX labels
- SFX loudness-driven sizing/pop
- music descriptor rules

**Exit criteria**

A test scene containing dialogue + effects + music produces three correct event categories.

---

## M12 — AI review queue

**Implement**

- issue types
- confidence thresholds
- scene jump-to-issue
- accept/reject
- manual correction
- issue resolution state
- correction log

**Exit criteria**

The user can finish a long video by reviewing only flagged/uncertain events instead of inspecting every frame.

---

## M13 — Long-video production engine

**Implement**

- bounded-memory processing
- parallelizable chunks
- model lifecycle management
- cache reuse
- crash recovery
- disk-space checks
- processing ETA
- progress by stage
- global timeline reconciliation

**Exit criteria**

A 2-hour test video completes on a supported machine without requiring the whole file in memory, and a simulated crash resumes successfully.

---

## M14 — Professional timeline UI

**Implement**

- scene track
- speaker track
- caption track
- word track
- syllable track
- waveform
- loudness graph
- pitch graph
- issue markers
- safe/work areas
- frame stepping
- loop tools
- zoom/pan

**Exit criteria**

All timeline elements remain synchronized while scrubbing and editing.

---

## M15 — Full export system

**Implement**

Sidecars:

- SRT
- VTT
- TTML
- ASS/SSA

Video:

- full CI burn-in
- source-resolution default
- source-fps default
- configurable codec/quality
- audio-copy option
- hardware acceleration detection

**Exit criteria**

A finished project creates both compatibility caption files and a burned-in visual CI video.

---

## M16 — Render correctness and regression framework

**Implement**

- golden reference projects
- frame-level rendering tests
- image diffs
- typography metric tests
- timing tests
- codec/output validation

**Exit criteria**

Future renderer changes can be tested against known-good visual output.

---

## M17 — Accessibility and usability validation

**Implement**

- keyboard navigation
- screen-reader-friendly metadata where practical
- large-text UI options
- high-contrast editor mode
- non-color-only speaker identity indicators in the editor
- accessibility review workflow
- community testing protocol

**Exit criteria**

The editing application itself is usable without requiring color perception as the only identifier.

---

## M18 — Packaging and offline distribution

**Implement**

- Windows package
- Linux package
- macOS package where practical
- model installer/download manager
- checksum verification
- offline model cache
- third-party license inventory
- crash logs with user control

**Exit criteria**

A fresh machine can install the application and complete an end-to-end local workflow without a mandatory API account.

---

## M19 — CLI and batch mode

**Implement**

Commands such as:

```bash
ci-captionv2 analyze input.mp4
ci-captionv2 review project.ci
ci-captionv2 render project.ci --output output.mp4
ci-captionv2 export project.ci --format srt
ci-captionv2 batch ./jobs/
```

**Exit criteria**

A folder of videos can be queued and processed unattended while preserving per-project logs and failure states.

---

## M20 — MVP release gate

The MVP is complete only when ALL of the following are true:

- every V1.0 feature in the source PDF has a software representation
- every material visual rule is deterministic
- every material property can be edited manually
- automatic analysis can run locally
- long-video processing is chunked/resumable
- standard sidecar exports work
- burned-in video export works
- original media remains untouched
- confidence/review workflow exists
- regression fixtures pass
- third-party licensing is documented
- project files remain reusable after restarting the application

---

# 16. Internal canonical data model

The renderer should consume a versioned structured project, not SRT directly.

Example conceptual schema:

```json
{
  "schema_version": "ci-project-1",
  "design_system": "caption-with-intention-v1.0",
  "video": {
    "width": 1920,
    "height": 1080,
    "fps": 23.976,
    "duration": 7321.4
  },
  "speakers": [
    {
      "id": "spk_01",
      "name": "Character A",
      "category": "main",
      "role": "hero",
      "color": "#E5E517"
    }
  ],
  "events": [
    {
      "id": "evt_001",
      "type": "dialogue",
      "start": 112.420,
      "end": 115.900,
      "speaker_id": "spk_01",
      "off_camera": false,
      "text": "I cannot believe you did this.",
      "style": {
        "read_ahead_opacity": 0.90,
        "pop_scale": 1.15,
        "size_mode": "auto",
        "weight_mode": "auto",
        "width_mode": "auto"
      },
      "words": [
        {
          "text": "I",
          "start": 112.420,
          "end": 112.510,
          "size_pct": 5.0,
          "weight": 400,
          "width": 100,
          "color": "#E5E517"
        }
      ]
    }
  ]
}
```

Additional event types:

- `dialogue`
- `sound_effect`
- `music`
- `speaker_overlap`
- `custom`

Additional metadata per event/object:

- `confidence`
- `source_model`
- `source_timestamp`
- `manual_override`
- `review_state`
- `notes`

---

# 17. Rule/profile configuration

Never scatter design constants throughout the source code.

Suggested structure:

```text
design_systems/
  caption_with_intention/
    v1.0/
      profile.json
      colors.json
      typography.json
      synchronization.json
      elements.json
      exports.json
      exceptions.json
      music.json
      sound_effects.json
```

This allows future community revisions without breaking old projects.

Projects store the exact profile version they were created against.

---

# 18. Technical architecture

```text
                    ┌──────────────────────┐
                    │ Desktop UI           │
                    │ React + TypeScript   │
                    └──────────┬───────────┘
                               │ IPC/WebChannel
                    ┌──────────▼───────────┐
                    │ Python application   │
                    │ orchestration         │
                    └──────────┬───────────┘
                               │
      ┌────────────────────────┼─────────────────────────┐
      │                        │                         │
┌─────▼─────┐            ┌─────▼─────┐            ┌─────▼─────┐
│ Media     │            │ AI/Signal │            │ CI Engine │
│ FFmpeg    │            │ Analysis  │            │ Rules     │
└─────┬─────┘            └─────┬─────┘            └─────┬─────┘
      │                        │                         │
      └────────────────────────┼─────────────────────────┘
                               │
                    ┌──────────▼───────────┐
                    │ Canonical CI Project │
                    │ JSON/SQLite/cache    │
                    └──────────┬───────────┘
                               │
              ┌────────────────┴────────────────┐
              │                                 │
      ┌───────▼────────┐                ┌───────▼────────┐
      │ Sidecar export │                │ Burn-in render │
      │ SRT/VTT/TTML/  │                │ CI overlay +   │
      │ ASS            │                │ FFmpeg         │
      └────────────────┘                └────────────────┘
```

Recommended implementation approach:

- Python for orchestration, media/ML integration and project engine
- React + TypeScript for editor UI
- PySide6 as a practical Python-first desktop shell for the initial MVP (OPTIONAL DO IT AT LAST PRIORITY)
- FFmpeg for media probing, decode/encode and final muxing
- local ML models behind stable internal interfaces
- SQLite/JSON for project state and indexed events
- Canvas/WebGL preview renderer for interactive captions

---

# 19. Suggested repository

```text
caption-with-intention/
├── apps/
│   ├── desktop/
│   └── cli/
├── frontend/
│   ├── editor/
│   ├── timeline/
│   ├── preview/
│   ├── inspector/
│   ├── speaker-panel/
│   └── export-panel/
├── engine/
│   ├── ingest/
│   ├── media/
│   ├── scenes/
│   ├── asr/
│   ├── alignment/
│   ├── diarization/
│   ├── face_tracking/
│   ├── active_speaker/
│   ├── audio_analysis/
│   ├── sound_events/
│   ├── music/
│   ├── caption_generation/
│   ├── rules/
│   ├── typography/
│   ├── animation/
│   ├── renderer/
│   ├── exporters/
│   └── validation/
├── design_systems/
│   └── caption_with_intention/v1.0/
├── schemas/
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── fixtures/
│   ├── audio/
│   ├── timing/
│   └── visual_regression/
├── docs/
├── THIRD_PARTY_LICENSES/
└── README.md
```

---

# 20. Performance targets

These are product targets rather than claims about guaranteed speed on every computer.

## Short video

- interactive preview should begin quickly
- analysis should show stage progress rather than a single spinner

## Long video

- RAM usage should be bounded by configured working-set limits
- processing should continue from checkpoints after restart
- CPU-only fallback must exist
- optional GPU acceleration should be used when available

## Render

- use source resolution and frame rate by default
- avoid unnecessarily transcoding unchanged audio
- use hardware encoder when explicitly supported/detected

## Project storage

Intermediate data must be streamable/deletable independently. The user can clear regenerable caches without deleting the project definition or editorial decisions.

---

# 21. Failure handling

The application must distinguish:

- fatal project corruption
- model unavailable
- insufficient disk space
- unsupported codec
- GPU memory exhaustion
- low AI confidence
- conflicting speaker attribution
- malformed caption source
- output encode failure

For recoverable problems:

1. save current state
2. mark the stage failed
3. preserve already-completed stages
4. show an actionable error
5. allow retry of the failed stage only

Never silently discard user edits because an AI stage failed.

---

# 22. Community feedback and validation

Because the source system was developed with Deaf and Hard of Hearing community participation and is intended to evolve, build community validation into the project rather than treating it as post-MVP marketing.

Recommended MVP process:

- create A/B test export: conventional captions vs CI
- recruit voluntary Deaf/HoH testers
- collect structured feedback about attribution, sync, tone, readability and distraction
- keep all collected research data opt-in and privacy-preserving
- version feedback against design-system profile versions

Do not automatically change the design rules from feedback. Instead:

```text
feedback
  ↓
research report
  ↓
proposed rule revision
  ↓
new design-system profile
  ↓
visual regression
  ↓
community validation
```

---

# 23. Licensing and branding plan

The PDF is marked All Rights Reserved. The project should therefore keep a clean separation between:

- our original implementation code
- third-party open-source libraries/models/fonts
- Caption With Intention descriptive/design-system material
- any official logos/brand assets

Do not ship copied proprietary artwork, official After Effects project files, or official logos unless the applicable rights explicitly permit redistribution.

Use the documented functional rules as an implementation target and include attribution/source notes in the project's documentation. Verify every dependency/model/font license before distribution.

Suggested code license for this project: choose an OSI-approved license such as MIT or Apache-2.0 after checking all dependency/model constraints.

---

# 24. MVP definition of done

The MVP is **not** “AI generated subtitles.” It is done only when a user can:

1. Import a clip, episode, or movie-length video.
2. Import existing captions or transcribe locally.
3. Run automated analysis.
4. Get stable speakers across chunks.
5. See on/off-camera attribution.
6. Get word-level timing.
7. Get optional syllable-level timing.
8. Map volume to 3–12% typography with 5% baseline.
9. Map pitch to weight.
10. Map harmonics to width.
11. Get character colors according to the V1.0 palettes and hierarchy rules.
12. Get read-ahead text at 90% white.
13. Get word-onset color sync.
14. Get 15% pop animation.
15. Get a 90% black caption box.
16. Stay within the lower 20% work area and max two lines by default.
17. Represent sound effects in white brackets with synchronized animation.
18. Represent music according to the design-system music treatment.
19. Apply scene/project exceptions.
20. Compare against original captions.
21. Review only low-confidence/constraint-violating cases.
22. Manually edit every material parameter.
23. Save and resume without losing work.
24. Export SRT/VTT/TTML/ASS.
25. Burn the full visual CI treatment into a new video.
26. Process short and long videos using the same project model.
27. Recover from an interrupted analysis/render.
28. Run regression tests before release.

---

# 25. Recommended implementation order

The most important sequencing decision is:

```text
1. Canonical project model
2. Deterministic CI renderer
3. Manual editor
4. Import/export
5. ASR + alignment
6. Speaker diarization
7. Visual active speaker
8. Audio intonation
9. SFX/music
10. Long-video orchestration
11. Review queue
12. Final burn-in
13. Packaging/batch/CLI
14. Community validation
```

Do not reverse the order and start with an LLM. The deterministic renderer is the product core; AI is the acceleration layer.

---

# 26. First proof-of-concept fixture

Build one 30–60 second test scene that includes:

- two visible speakers
- one rapid back-and-forth exchange
- one off-camera voice
- quiet speech
- loud speech
- low-pitch voice
- high-pitch voice
- a word spoken syllable-by-syllable
- one loud SFX such as a crash/thunder-like event
- a music segment
- at least one caption needing two lines
- a scene that intentionally disables attribution color

The proof is successful when the same canonical event file can:

- render in the live preview
- be manually edited
- export a compatibility sidecar
- burn into the source-resolution video
- pass automated rule tests

---

# 27. Final engineering principle

**Probabilistic understanding + deterministic design + human override + resumable rendering.**

That is the architecture that gives this project a realistic path from Shorts to feature-length video while still honoring every published V1.0 rule and allowing an editor to correct every individual decision.
