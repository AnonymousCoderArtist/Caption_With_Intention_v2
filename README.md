# Caption With Intention v2

> **Caption With Intention (CWI)** is a revolutionary caption design system for movies and TV shows that transforms closed captions from plain text into a rich, expressive experience — conveying who is speaking, when they speak, and how they sound.
It is for the hearing disabled people. It has won international level award and it needed a opensource project for free to automate this system soo here i am :)
---

## Overview

Around the world, **466 million people** live with hearing disabilities. Since the inception of closed captioning in the 1970s, captions have not meaningfully evolved. **Caption With Intention** addresses three core shortcomings that negatively impact the viewing experience for the Deaf and hard-of-hearing community:

1. **Attribution** — Who is speaking?
2. **Synchronization** — When are they speaking?
3. **Intonation** — How do they sound?

Developed in partnership with the **Chicago Hearing Society** with community validation from February 2024 to December 2024.

---

## The Three Shortcomings

| Shortcoming | Problem | Solution |
|-------------|---------|----------|
| **Attribution** | Captions don't identify who speaks, especially when multiple characters talk, speak quickly, or speak off-camera | Color-coded captions per character |
| **Synchronization** | Captions lag behind dialogue, breaking scene rhythm | Word-by-word color sync precisely when sound begins |
| **Intonation** | No cues for emotion, volume, pitch, or tone | Variable typeface (Roboto Flex) mapping volume → size, pitch/harmonics → weight/width |

---

## Design System at a Glance

### Attribution Colors

| Character Tier | Colors | Count |
|---------------|--------|-------|
| **Main Characters** | Yellow, Blue, Red, Orange, Green, Purple | 6 |
| **Supporting Characters** | Orange, Blue I/II, Yellow, Green I/II/III, Purple I/II, Pink I/II, Cyan | 12 |
| **Minor Characters** | Pastel tones (center of color wheel, 30% saturation, 90% brightness) | 24 |

**Rules:**
- Main characters: colors spaced far apart on spectrum; Hero/Villain colors opposite
- Supporting: visually distant from main character colors
- Off-camera characters: assigned specific colors + italic type

### Synchronization Features

| Feature | Description |
|---------|-------------|
| **Read-Ahead Type** | Full white text at 90% opacity shows complete sentence first |
| **Color Sync** | Words change character color as sound begins (not after) |
| **Guiding the Eye** | 15% type size "pop" motion as each word is spoken |
| **Syllable Variation** | Syllable-by-syllable animation matching speech rhythm |

### Intonation Mapping

| Voice Property | Typeface Mapping |
|---------------|-----------------|
| **Volume** | Type size: 3% (whisper) → 5% (normal) → 12% (yell) |
| **Pitch** | Type weight: Low Hz (80-160) → heavier; High Hz (200+) → lighter |
| **Harmonics** | Type width: Low harmonics → wider; High harmonics → narrower |
| **Baseline** | 160-200 Hz → Roboto Regular 400 (neutral) |

---

## Key Specifications

| Parameter | Value |
|-----------|-------|
| Baseline type size | 5% of screen height |
| Type size range | 3% (min whisper) — 12% (max yell) |
| Typeface | Roboto Flex (variable font, 12 axes) |
| Captions Box | 90% black opacity |
| Work Area | Lower 20% of frame |
| Max lines per frame | 2 |
| Sound effects | White, in brackets `[ ]` |
| Off-camera indicator | Italic type + assigned color |
| Automation | AI-powered (open source, free — future goal) |

---

## Project Structure

```
Caption_With_Intention_v2/
├── README.md                    # This file
├── CAPTION_WITH_INTENTION.md    # Full design system documentation
├── Caption-With-Intention_Design-System_V1.0.pdf  # Official design system PDF
├── captions/                    # Caption outputs / specifications
├── templates/                   # Color/style templates
├── config/                      # Project configuration
├── output/                      # Final deliverables
└── scripts/                     # Automation scripts
```

---

## Automation Goals

**Current:** Applied via Adobe After Effects through operator-based, manually controlled process.

**Future:** AI-based system to fully automate CWI application. The system will be:
- AI-powered
- Open source
- Free of charge

---

## Standards & Compliance

- **FCC regulations** — CWI augments (does not replace) mandated closed captions
- **Standards and Regulations** — See full document

---

## Resources

- [Roboto Flex Typeface](https://github.com/google/fonts/tree/main/ofl/robotoflex) — Variable font download
- [After Effects Project](#) — Template for manual CWI application (TBD)
- [Chicago Hearing Society](https://www.chs.org/) — Community partner

---

## Contributing

This design system is intended to be **constantly updated** based on feedback from the Deaf community. We invite creators, technologists, storytellers, and members of the Deaf community to collaborate and evolve this work.

---

## License

All Rights Reserved

*Design System and Caption Guidelines — Version 1.0 | 2025.1*
*Developed in partnership with the Chicago Hearing Society*
