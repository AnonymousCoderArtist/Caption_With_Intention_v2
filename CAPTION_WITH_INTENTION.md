# Caption With Intention — Design System

> **Caption With Intention** is a revolutionary caption design system for movies and TV shows that transforms closed captions from plain text into a rich, expressive experience — conveying **who** is speaking, **when** they speak, and **how** they sound.

---

## Table of Contents

1. [Introduction](#introduction)
2. [The Three Shortcomings](#the-three-shortcomings)
   - [Attribution](#1-attribution)
   - [Synchronization](#2-synchronization)
   - [Intonation](#3-intonation)
3. [Community Validation](#community-validation)
4. [About the Chicago Hearing Society](#about-the-chicago-hearing-society)
5. [The Design System](#the-design-system)
   - [2.1 Solving for Attribution](#21-solving-for-attribution)
     - [Color Selection for Main Characters](#color-selection-for-main-characters)
     - [Color Selection for Supporting Characters](#color-selection-for-supporting-characters)
     - [Color Combination: Main vs Supporting](#color-combination-main-vs-supporting)
     - [Color Selection for Minor Characters](#color-selection-for-minor-characters)
     - [Off-camera Characters](#off-camera-characters)
   - [2.2 Solving for Synchronization](#22-solving-for-synchronization)
     - [The Read-Ahead Type](#the-read-ahead-type)
     - [Color Sync](#color-sync)
     - [Guiding the Eye With Motion](#guiding-the-eye-with-motion)
     - [Syllable Variation](#syllable-variation)
   - [2.3 Solving for Intonation](#23-solving-for-intonation)
     - [The Typeface (Roboto Flex)](#the-typeface)
     - [Volume](#volume)
     - [Type Size Unit of Measure](#type-size-unit-of-measure)
     - [Baseline Type Size](#baseline-type-size)
     - [Type Size Range](#type-size-range)
     - [Pitch and Harmonics](#pitch-and-harmonics)
     - [Baseline Type Weight and Width](#baseline-type-weight-and-width)
     - [Type Weight and Width Range](#type-weight-and-width-range)
     - [Relationship Between Pitch, Harmonics, and Roboto Flex](#relationship-between-pitch-harmonics-and-roboto-flex)
   - [2.4 Elements Rules](#24-elements-rules)
     - [The Captions Box](#the-captions-box)
     - [Captions Containing Box — Size](#captions-containing-box--size)
     - [The Work Area](#the-work-area)
     - [Working With Sound Effects](#working-with-sound-effects)
     - [Working With Music](#working-with-music)
6. [Other Considerations](#other-considerations)
   - [Exceptions](#exceptions)
   - [Distribution](#distribution)
   - [Current Closed Captions as Model](#current-closed-captions-as-model)
   - [Standards and Regulations](#standards-and-regulations)
   - [Automation](#automation)
7. [Resources](#resources)

---

## Introduction

Around the world, **466 million people** live with hearing disabilities. To watch film and television, they rely on captions — yet since the inception of closed captioning in the 1970s, captions have not evolved. What was once an innovative solution is now outdated, and its shortcomings negatively impact the viewing experience.

This document introduces a new approach to designing and animating captions, helping the Deaf and hard-of-hearing community experience the craft of film and storytelling like never before.

### The Vision

> "Together, we can make sure that everyone not only sees the words on screen, but understands the **intention** behind them."

---

## The Three Shortcomings

Three main issues have impacted how the Deaf and hard-of-hearing communities enjoy film and storytelling. Often, two or three of these shortcomings combine on screen at the same time to significantly impact a scene's enjoyment and comprehension.

### 1. Attribution

**Problem:** Today's captions don't clearly and consistently identify who is speaking. Moments where several characters speak at once, in quick succession, or when a character speaks off-screen, can be unnecessarily confusing for a deaf viewer.

**Example (The Dark Knight):** Commissioner Gordon sits alone in the police station when the Joker speaks from off-camera: "Does it depress you, Commissioner?" For hearing viewers, the voice and tone immediately reveal who's speaking. But standard closed captions often omit speaker identification, making it unclear who's talking and stripping the scene of its tension.

**Solution:** Color-coded captions — each character gets their own distinct color.

### 2. Synchronization

**Problem:** Traditional captions are not synced precisely to the words spoken. With humor and emotion, timing is everything, and much of their impact can be missed.

**Example (Die Hard):** A bomb detonates — sudden, loud, and immediate. But in standard captioning, there's a noticeable delay. While the explosion unfolds on screen, the captions still read: "Bomb is exploding in 3, 2, 1..." This desynchronization breaks the rhythm of the scene, making the moment feel disjointed.

**Solution:** Word-by-word color changes synced precisely when the sound begins (not after).

### 3. Intonation

**Problem:** Captions lack cues for intonation and emotion. Aside from occasional exclamation points or ALL CAPS, captions provide very little information about the tone or emotional nuances of speakers.

**Example (Star Wars: The Empire Strikes Back):** When Darth Vader reveals "I am your father," Luke's response — "No, no. That's not true." — is packed with disbelief and emotional collapse. Hearing viewers feel this through intonation: the cracking voice, rising pitch, and raw intensity. Standard captions flatten it into plain text, losing the emotional weight.

**Solution:** Variable typeface (Roboto Flex) that conveys volume (size) and pitch/harmonics (weight/width).

---

## Community Validation

The input of the Deaf and Hard of Hearing community was essential to the development of Caption With Intention. In partnership with the **Chicago Hearing Society (CHS)**, in-person and online research was conducted from **February 2024 to December 2024** to:

1. Identify key issues with existing captions
2. Test possible solutions on acclaimed films
3. Gather systematic feedback from the Deaf community

**Methodology:**
- Custom tablet system for voting on preferred design variations
- Individual interviews for deeper insights
- Test screenings with community participants

**Key Participants:**
- **Karla Giese** — Chicago Hearing Society
- **Michelle Porter** — Test Screening #2, Chicago Hearing Society
- **Jason Weiland** — Chicago Hearing Society

---

## About the Chicago Hearing Society

The **Chicago Hearing Society (CHS)**, originally founded in 1916 as the Chicago League for the Hard of Hearing, has been serving the Deaf, DeafBlind, and Hard of Hearing communities for over a century.

**Key programs:**
- Illinois' first mental health counseling service for Deaf individuals
- A.R.M.E.D. — mentorship initiative connecting Deaf adults with at-risk Deaf youth
- Interpreting services, audiology, and American Sign Language classes

CHS continues to lead with core values of **advocacy, inclusion, and education**, empowering individuals to connect, belong, and thrive.

---

## The Design System

The following chapters provide all of the details necessary for anyone to caption films with this innovative design system. This new approach intends to be constantly updated and improved based on feedback from the Deaf community.

---

### 2.1 Solving for Attribution

**Caption With Intention** offers a surprisingly simple solution for character attribution: **by using different colors for each character's captions, the audience can quickly identify who is speaking.**

The system specifies colors that are carefully chosen to be:
- **Distinct** — clearly different from each other
- **Easily recognizable** — immediately identifiable
- **Highly visible** — visible against any caption backdrop

---

#### Color Selection for Main Characters

The color spectrum consists of **six main colors**: Yellow, Blue, Red, Orange, Green, and Purple.

| Character | Name | RGB | HEX |
|-----------|------|-----|-----|
| #01 | CI Main Yellow | R:229 G:229 B:23 | `#E5E517` |
| #02 | CI Main Blue | R:23 G:229 B:229 | `#17E5E5` |
| #03 | CI Main Red | R:229 G:23 B:23 | `#E51717` |
| #04 | CI Main Orange | R:229 G:128 B:23 | `#E58017` |
| #05 | CI Main Green | R:23 G:229 B:23 | `#17E517` |
| #06 | CI Main Purple/Pink | R:229 G:23 B:229 | `#E517E5` |

**Guidelines:**
- If a film features **3 main characters**, their colors should be **spaced as far apart as possible** on the spectrum
- If the film defines a **Hero and Villain**, their colors should be **opposite each other** on the spectrum

**Film Examples:**

| Film | Year | Director | Characters Assigned |
|------|------|----------|-------------------|
| Toy Story | 1995 | John Lasseter | Woody (Yellow), Buzz Lightyear (Blue), Mr. Potato Head (Red), Rex (Orange), Hamm (Green) |
| Kramer vs Kramer | 1979 | Robert Benton | Ted Kramer, Joana Kramer, Billy Kramer, Margaret Phelps |
| Rocky | 1976 | John G. Avildsen | Rocky, Adrian, Paulie, Apollo, Mickey |

---

#### Color Selection for Supporting Characters

After selecting main characters, supporting character colors should fall **between the main colors on the spectrum**. **12 recommended colors** are specified:

| # | Name | RGB | HEX |
|---|------|-----|-----|
| 1 | CI Support Orange | R:232 G:92 B:46 | `#E85C2E` |
| 2 | CI Support Blue I | R:71 G:194 B:235 | `#47C2EB` |
| 3 | CI Support Yellow | R:235 G:194 B:71 | `#EBC247` |
| 4 | CI Support Blue II | R:94 G:130 B:237 | `#5E82ED` |
| 5 | CI Support Green I | R:194 G:235 B:71 | `#C2EB47` |
| 6 | CI Support Purple I | R:140 G:107 B:237 | `#8C6BED` |
| 7 | CI Support Green II | R:130 G:237 B:94 | `#82ED5E` |
| 8 | CI Support Purple II | R:204 G:107 B:237 | `#CC6BED` |
| 9 | CI Support Green III | R:71 G:235 B:112 | `#47EB70` |
| 10 | CI Support Pink I | R:235 G:71 B:194 | `#EB47C2` |
| 11 | CI Support Cyan | R:94 G:237 B:201 | `#5EEDC9` |
| 12 | CI Support Pink II | R:237 G:94 B:130 | `#ED5E82` |

---

#### Color Combination: Main vs Supporting Characters

Supporting character colors should be **visually distant** from main character colors. For example, if a main character is represented in red, avoid nearby hues like orange or magenta for supporting roles, as they can visually blend and create confusion.

The system recommends pairing **contrasting hues** to preserve clarity and enhance storytelling.

---

#### Color Selection for Minor Characters

Minor characters are assigned colors from the **center of the color wheel**, where tones are more **pastel and closer to white**. This establishes a hierarchy of character importance while maintaining basic attribution rules.

**Minor character color formula:** `H: [varying hue], S: 30%, B: 90%`

Colors are spaced at 15-degree intervals across the full hue spectrum (0° to 342°), producing 24 pastel color options.

---

#### Off-camera Characters

Attribution rules also apply to off-camera characters and voices. While traditional systems indicate off-screen voice with italics, Caption With Intention goes further by **associating a specific color** with each off-camera character.

**Example (Scream, 1996):** When a voice is heard off-screen in Wes Craven's Scream, the system assigns a specific color to that character, making it immediately clear WHO is speaking even when not seen on camera.

**Rule:** On-camera characters use **Roman type**, off-camera characters use **Italic type** (with their assigned color).

---

### 2.2 Solving for Synchronization

By syncing perfectly with the rhythm and speed of each character's dialogue, this system enables the Deaf community to better grasp the pacing and overall energy of a scene. Synchronization is handled by **changing the color of each word precisely as it is spoken.**

---

#### The Read-Ahead Type

Every line of dialogue should **first appear in white as a complete sentence** (similar to current caption systems). This allows the Deaf community to read ahead at their own pace.

**Specifications:**
- Read-ahead text displayed in **full white at 90% opacity**
- Synchronized spoken words then change color word-by-word

**Example (Star Wars: Episode V – The Empire Strikes Back, 1980):**
- First: "No, I am your father" appears in white at 90% opacity (read-ahead)
- Then: Each word changes to the speaker's color as it's spoken

---

#### Color Sync

In addition to white read-ahead text, **colored text representing each character is overlaid word by word**. Each word changes color **as soon as the sound begins** to be pronounced — not after.

**Key rule:** If someone says "inexplicable," the word changes color when "In" is spoken, not when "ble" is spoken. This word-level precision is a feature unavailable in previous caption systems.

**Example (Steve Jobs, 2015):** Danny Boyle's film demonstrates precise word-level color syncing.

---

#### Guiding the Eye With Motion

To further ensure synchronization, each word undergoes a **15% increase in type size** (a "pop" motion) as it changes color, then returns to its original size. This visual motion guides the viewer's eye to the exact part of the caption being spoken.

**Example (Casino Royale, 2006):** "We need to talk" — each word pops as it's spoken, making it impossible to miss which word corresponds to which sound.

---

#### Syllable Variation

In certain instances, it may enhance clarity to **emphasize one syllable at a time** through animation, matching how the word is actually spoken.

**Example (Casino Royale, 2006):** "Unbelievable" — when spoken broken into syllables ("Un-be-liev-a-ble"), the visual animation mirrors that same syllable-by-syllable breakdown, maintaining visual sync with what is heard.

---

### 2.3 Solving for Intonation

Caption With Intention provides crucial intonation information for deaf viewers that was missing in previous captioning systems. Using a **single variable typeface**, the system graphically conveys details about the **volume** and **pitch** of speakers — allowing Deaf viewers to understand intonation in film and TV for the first time.

---

#### The Typeface

The typeface used is **Roboto Flex** — one of the most adaptable and screen-friendly typefaces in the world. It was selected for:
- **Clarity** — sharp and readable across all viewing platforms
- **Flexibility** — 12 customizable axes (weight, width, grade, slant, optical size)
- **Expressiveness** — ability to capture the full range of human voice

Roboto Flex is a **variable font** that consolidates multiple styles into a single file, enhancing design flexibility while improving performance and consistency.

---

#### Volume

Volume is conveyed through **type size** (height of the type):

| Volume Level | Type Size | Visual Effect |
|-------------|-----------|---------------|
| Whisper (-48 to -54 dB) | ~3% of screen height | Very small type — noticeably smaller than baseline |
| Normal speaking (~0 dB) | 5% of screen height (baseline) | Standard readable size |
| Loud/Yelling (-6 to -18 dB) | Up to 12% of screen height | Very large type — dramatically bigger than baseline |

**Rule:** Louder voices = larger, taller type. Quieter voices = smaller, shorter type. Both relative to the baseline type size.

---

#### Type Size Unit of Measure

Type size is defined as a **percentage of the screen height** for standard 16x9 and all widescreen formats. This is absolute to the visual experience, ensuring type size remains visually consistent regardless of:
- Screen resolution (1080p, 4K, 8K)
- Display technology
- Future formats

---

#### Baseline Type Size

The baseline type size for **normal speaking volume** is **5% of the overall screen height**.

| Aspect Ratio | Baseline Size |
|-------------|---------------|
| 1.85:1 (Academy Flat / Widescreen) | 5% |
| 2.39:1 (CinemaScope / Anamorphic) | 5% |
| 1.43:1 (IMAX) | 5% |
| 16:9 (HDTV Standard) | 5% |

This aligns with many traditional captioning standards while allowing scaling within the prescribed range.

---

#### Type Size Range

| Limit | Value | Meaning |
|-------|-------|---------|
| Smallest | 3% of screen height | Whispering — noticeably smaller, signals quiet voice |
| Baseline | 5% of screen height | Normal speaking volume |
| Largest | 12% of screen height | Yelling/very loud — dramatically larger |

**Determination methods:**
- **Subjective** — by human ear assessment
- **Objective** — based on technical waveform analysis

---

#### Pitch and Harmonics

Pitch (fundamental frequency) and harmonics determine how a voice sounds. The variable typeface maps these directly to type characteristics:

| Voice Characteristic | Pitch Range | Type Weight | Type Width |
|---------------------|-------------|-------------|------------|
| Deep/Bass (low harmonics) | 80–160 Hz | Heavier weight | Wider/Expanded |
| Normal | 160–200 Hz | Regular (Roboto Regular 400) | Normal |
| High-pitched (high harmonics) | 200+ Hz | Lighter weight | Narrower/Condensed |

**Why it works:** Low-pitched voices have stronger low-frequency harmonics → feel fuller and deeper → heavier, expanded typeface is a natural match. High-pitched voices emphasize higher harmonics → sound lighter and sharper → lighter, condensed typeface matches their tonal quality.

---

#### Baseline Type Weight and Width

**Baseline frequency range:** 160–200 Hz (approximate, within the typical human voice range of 80–250 Hz).

Voices within this range are displayed using **Roboto Regular 400** (neutral type weight). All captions within this vocal range maintain this as a default.

---

#### Type Weight and Width Range

| Parameter | Range | Mapping |
|-----------|-------|---------|
| Font Weight | 100–900 | Pitch: Low Hz → heavier; High Hz → lighter |
| Font Width (Width axis) | Condensed–Expanded | Harmonics: Low harmonics → wider; High harmonics → narrower |

**Pitch vs Font Weight mapping:**
- 80 Hz → ~700 weight (bold/heavy)
- 160 Hz → 400 weight (regular — baseline)
- 250 Hz → ~300 weight (light)

**Harmonics vs Font Width mapping:**
- 100 Hz (low harmonics) → Expanded/wide
- 500 Hz (mid harmonics) → Normal width
- 1000 Hz (high harmonics) → Condensed/narrow

---

#### Relationship Between Pitch, Harmonics, and Roboto Flex

In both sound and typography, certain characteristics naturally align:

- **Low-pitched voices** → Stronger low-frequency harmonics → Fuller, deeper sound → **Heavier-weight, expanded typeface** (a condensed or thin style would contradict their tonal quality)
- **High-pitched voices** → Higher harmonics → Lighter, sharper sound → **Lighter-weight, condensed typeface** (an expanded, bold typeface would feel mismatched)

By maintaining this **direct correlation between sound and typography**, Caption With Intention ensures captions visually capture the nuances of speech, making tone and emotion perceptible to Deaf and hard-of-hearing audiences.

---

### 2.4 Elements Rules

---

#### The Captions Box

Captions appear within a **Captions Box** on screen, colored **90% black**. This serves two purposes:
1. Allows the film's background to remain visible
2. Provides an essential backdrop ensuring captions are easily readable (especially important for colored captions at varying weights)

**Exception:** For very loud or sudden bursts of speech, captions may **break out of the box** to represent the intensity or urgency of the voice.

---

#### Captions Containing Box — Size

- The Captions Box scales with the amount of type
- Dialogue captions and the box scale **in relation to each other**
- Maximum **2 lines** of captions per frame
- Adequate spacing between multiple lines

---

#### The Work Area

The work area defines where the Captions Box and captions appear:
- Occupies the **lower 20% of the frame**
- No elements extend beyond this area
- Additional **safety margins** at bottom, left, and right edges proportional to the 20%

**Margins:**
- Bottom: 5%
- Left/Right: 2.5% each
- Containing Box Area: proportionally scaled

---

#### Working With Sound Effects

Sound effects appear in:
- **White** text
- **Within brackets [ ]** (similar to classic captioning)
- Follow CWI animation and design rules

**Example:** Loud thunder → sound effect brackets **increase in size and "pop"** in sync with the actual sound.

---

#### Working With Music

Music is indicated using a **special symbol** (the `[ ]` symbol with a specific notation) on either side of the musical description.

**Rules:**
- Musical descriptors are in **white text**
- They are treated like classic captions — **no animation, no color changes**
- The symbol appears on both sides: `[ jazz ]` or similar notation

---

## 3.0 Other Considerations

### 3.1 Exceptions

Some movies might benefit from **not using** specific aspects of Caption With Intention.

**Example (Casablanca, 1942):** Old movies or movies intentionally shot in black and white might get distracting with different colors for attribution. In such cases, it's recommended to use **only the animation aspect** of Caption With Intention.

These exceptions are at the **discretion of the editor**.

### 3.2 Distribution

Caption With Intention is purposely timed to encourage the filmmaking and technology communities to develop and implement technology for wide availability.

**Current limitation:** Technology used to decode closed captioning has limitations that prevent support for CWI features.

**Interim distribution:** Until technology is developed and widely adopted, film content encoded with CWI can be distributed with **open captions (burned in)** across:
- Streaming services
- Cinema
- Broadcast

### 3.3 Current Closed Captions as Model

Closed captions are one of the most important inclusion initiatives of our time — available on billions of devices following a globally recognized standard.

**CWI's approach:**
- Builds on CC success
- Addresses visual design and implementation shortcomings
- Maintains familiarity of traditional captions
- Introduces new features without overwhelming the viewer
- Non-addressed areas **default to original closed captions** for guidance

### 3.4 Standards and Regulations

Closed captioning is regulated and mandated by the **FCC**. Caption With Intention is intended to **augment rather than replace** closed captions in the near term.

**Rule:** Use of Captions With Intention should be **in addition to** the regulated and mandated use of the Closed Captions system.

### 3.5 Automation

**Current method:** Applied using readily available industry tools (e.g., **Adobe After Effects**) through an **operator-based, manually controlled process**.

**Ultimate goal:** An **AI-based technology system** to fully automate the application of Captions With Intention. Once developed, this system will be deployed as:
- **Open source**
- **Free of charge**

### 3.6 Resources

Access all resources required to implement CWI:

- **Roboto Flex Typeface** — Download the variable font file
- **After Effects Project** — Download the AE template for manual application

---

## Resources

| Resource | Description |
|----------|-------------|
| **Roboto Flex** | Variable typeface with 12 customizable axes |
| **After Effects Project** | Template for manual CWI application |
| **Chicago Hearing Society** | Community partner and validation organization |
| **FCC** | Regulatory body for closed captioning standards |

---

## Key Specifications Summary

| Parameter | Value |
|-----------|-------|
| Main character colors | 6 (Yellow, Blue, Red, Orange, Green, Purple) |
| Supporting character colors | 12 |
| Minor character colors | 24 (pastel, center of color wheel) |
| Baseline type size | 5% of screen height |
| Type size range | 3% (min) — 12% (max) |
| Baseline type weight | Roboto Regular 400 (160-200 Hz) |
| Type weight range | 100–900 |
| Type width range | Condensed–Expanded |
| Baseline frequency | 160–200 Hz |
| Read-ahead opacity | 90% white |
| Motion pop | 15% size increase |
| Captions Box opacity | 90% black |
| Work area | Lower 20% of frame |
| Max caption lines per frame | 2 |
| Voice off-camera indicator | Italic + assigned color |
| Sound effects | White + brackets `[ ]` |
| Music indicator | Special symbol on both sides |

---

## Film Case Studies

| Film | Year | Director | Demonstrated Feature |
|------|------|----------|---------------------|
| Toy Story | 1995 | John Lasseter | Main character color assignment |
| Kramer vs Kramer | 1979 | Robert Benton | Multi-character color differentiation |
| Rocky | 1976 | John G. Avildsen | Ensemble cast color mapping |
| The Dark Knight | 2008 | Christopher Nolan | Attribution (off-camera Joker) |
| Die Hard | 1988 | John McTiernan | Synchronization |
| Star Wars: Episode V | 1980 | Irvin Kershner | Read-ahead type, Color Sync |
| Steve Jobs | 2015 | Danny Boyle | Word-level Color Sync |
| Casino Royale | 2006 | Martin Campbell | Motion guidance, Syllable variation |
| Glengarry Glen Ross | 1992 | James Foley | Volume (type size variation) |
| Finding Nemo | 2003 | Andrew Stanton, Lee Unkrich | Pitch and Harmonics |
| Avatar | 2009 | James Cameron | Captions Box (opacity levels) |
| Green Book | 2018 | Peter Farrelly | Multi-line Captions Box, Work Area |
| Casablanca | 1942 | Michael Curtiz | Exception handling |
| Scream | 1996 | Wes Craven | Off-camera character attribution |

---

*Design System and Caption Guidelines*
*Version 1.0 | 2025.1*
*All Rights Reserved*
*Developed in partnership with the Chicago Hearing Society*
