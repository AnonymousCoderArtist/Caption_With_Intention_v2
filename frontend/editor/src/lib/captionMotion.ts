/** Browser counterpart of the reviewed Python stability envelope.
 * These constants are regression-tested, not guessed in the UI component.
 */
import type { CaptionEvent, Word } from '@/types/project';
// libass uses REAL_DIM with OS/2 Win ascent + descent rather than CSS em.
// Bundled Roboto Flex: 2048 units/em, Win ascent 2461, descent 600.
// Glyph scaling only. Motion distances remain in ASS screen pixels.
export const ASS_EM_SCALE = 2048 / (2461 + 600);
export const MOTION = { riseMs: 60, settleMs: 140, maxSettleMs: 320, overlapMs: 80,
  lift: .12, pitchMod: .02, emphasisRatio: 1.55, sizeRiseMs: 90,
  sizeSettleMs: 140, escalationHold: .45 } as const;
const clamp = (v: number, lo: number, hi: number) => Math.max(lo, Math.min(hi, v));
export function envelope(ms: number, settleMs: number = MOTION.settleMs) {
  if (ms <= 0 || ms >= MOTION.riseMs + settleMs) return 0;
  if (ms < MOTION.riseMs) return .5 - .5 * Math.cos(Math.PI * ms / MOTION.riseMs);
  return .5 + .5 * Math.cos(Math.PI * (ms - MOTION.riseMs) / settleMs);
}
export function letterLift(word: Word, j: number, count: number, time: number, base: number, strength: number) {
  if (strength <= 1) return 0;
  const duration = Math.max(0, word.end - word.start);
  const onset = word.start + j / Math.max(1, count) * duration;
  const explicit = word.letter_pitches?.[j];
  let syllablePitch: number | null | undefined;
  if (explicit == null && word.syllables?.some(s => s.pitch_hz)) {
    let cursor = 0;
    for (const syllable of word.syllables) {
      cursor += Array.from(syllable.text).filter(c=>! /\s/.test(c)).length;
      syllablePitch = syllable.pitch_hz;
      if (j < cursor) break;
    }
  }
  const pitch = explicit ?? syllablePitch ?? word.pitch_hz;
  const mod = pitch ? clamp((pitch - 180) / 70, -1, 1) : 0;
  const settle = Math.min(MOTION.maxSettleMs, Math.max(MOTION.settleMs,
    duration * 1000 / Math.max(1, count) + MOTION.overlapMs));
  return clamp((strength - 1) / .25, 0, 2) * base * (MOTION.lift + mod * MOTION.pitchMod)
    * envelope((time - onset) * 1000, settle);
}
export function effectiveSize(word: Word, event: CaptionEvent) {
  if (event.style.size_mode === 'manual') return event.style.size_pct;
  if (word.source_model && !word.manual_override && word.size_pct < 5 * MOTION.emphasisRatio) return 5;
  return word.size_pct;
}
export function sizeAt(word: Word, event: CaptionEvent, time: number, base: number) {
  let target = base * effectiveSize(word, event) / 5;
  if (target >= base * (event.style.escalation_gate ?? 1.3)) {
    const held = Math.max(0, Math.min(time, word.end) - word.start - MOTION.escalationHold);
    target = Math.min(base * event.style.maximum_pct / 5,
      target * Math.min(event.style.escalation_max ?? 1.8, 1 + (event.style.escalation_rate ?? .8) * held));
  }
  if (time <= word.start || time >= word.end + MOTION.sizeSettleMs / 1000) return base;
  const rise = Math.min(MOTION.sizeRiseMs / 1000, Math.max(.001, (word.end - word.start) / 2));
  let mix = 1;
  if (time < word.start + rise) mix = .5 - .5 * Math.cos(Math.PI * (time - word.start) / rise);
  else if (time > word.end) mix = .5 + .5 * Math.cos(Math.PI * (time - word.end) * 1000 / MOTION.sizeSettleMs);
  return base + (target - base) * mix;
}
export function letterSpoken(word: Word, j: number, count: number, time: number) {
  return time >= word.start + j / Math.max(1, count) * Math.max(0, word.end - word.start);
}
export function activeCaptionEvents(events: CaptionEvent[], time: number) {
  return events.filter(e => time >= e.start && time < e.end).sort((a, b) => {
    const aSfx = a.type === 'sound_effect' || a.type === 'music';
    const bSfx = b.type === 'sound_effect' || b.type === 'music';
    return Number(bSfx) - Number(aSfx) || b.start - a.start;
  });
}
