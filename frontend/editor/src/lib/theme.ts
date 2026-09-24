/** Design tokens & palette helpers for the CWI editor.
 *
 * Colors mirror the Caption With Intention V1.0 attribution system.
 * Keep these in sync with src/styles/global.css.
 */

/* CWI main character colors (V1.0) */
export const MAIN_COLORS: { name: string; hex: string }[] = [
  { name: "CI Main Yellow", hex: "#E5E517" },
  { name: "CI Main Blue/Cyan", hex: "#17E5E5" },
  { name: "CI Main Red", hex: "#E51717" },
  { name: "CI Main Orange", hex: "#E58017" },
  { name: "CI Main Green", hex: "#17E517" },
  { name: "CI Main Pink", hex: "#E517E5" },
];

/* CWI supporting character colors (V1.0) */
export const SUPPORT_COLORS: string[] = [
  "#E85C2E", "#47C2EB", "#EBC247", "#5E82ED", "#C2EB47", "#8C6BED",
  "#82ED5E", "#CC6BED", "#47EB70", "#EB47C2", "#5EEDC9", "#ED5E82",
];

/** Pastel near-white minor-character generator (S30 / B90, 15° steps). */
export function minorColor(index: number): string {
  const hues = [42, 12, 330, 60, 18, 300, 30, 90, 270, 0, 345, 75];
  const h = hues[index % hues.length];
  return hslToHex(h, 30, 90);
}

function hslToHex(h: number, s: number, l: number): string {
  s /= 100;
  l /= 100;
  const a = s * Math.min(l, 1 - l);
  const f = (n: number) => {
    const k = (n + h / 30) % 12;
    const c = l - a * Math.max(-1, Math.min(k - 3, 9 - k, 1));
    return Math.round(255 * c)
      .toString(16)
      .padStart(2, "0");
  };
  return `#${f(0)}${f(8)}${f(4)}`.toUpperCase();
}

/** Hex -> readable contrast color (black or white). */
export function readableOn(hex: string): string {
  const c = hex.replace("#", "");
  const r = parseInt(c.slice(0, 2), 16);
  const g = parseInt(c.slice(2, 4), 16);
  const b = parseInt(c.slice(4, 6), 16);
  const lum = 0.2126 * r + 0.7152 * g + 0.0722 * b;
  return lum > 150 ? "#0c0c0c" : "#ffffff";
}

/** Event type metadata: label + accent color + css var. */
export const EVENT_TYPES: Record<
  string,
  { label: string; color: string; cssVar: string }
> = {
  dialogue: { label: "Dialogue", color: "#E5E517", cssVar: "var(--ev-dialogue)" },
  sound_effect: { label: "SFX", color: "#E58017", cssVar: "var(--ev-sfx)" },
  music: { label: "Music", color: "#17E5E5", cssVar: "var(--ev-music)" },
  speaker_overlap: { label: "Overlap", color: "#E517E5", cssVar: "var(--ev-overlap)" },
  custom: { label: "Custom", color: "#6d6d7e", cssVar: "var(--ev-custom)" },
};

/** Format seconds as m:ss */
export function fmtTime(sec: number): string {
  const s = Math.max(0, sec);
  const m = Math.floor(s / 60);
  const r = Math.floor(s % 60);
  return `${m}:${String(r).padStart(2, "0")}`;
}

/** Format seconds as a pro timecode HH:MM:SS:FF (24fps default). */
export function fmtTimecode(sec: number, fps = 23.976): string {
  const s = Math.max(0, sec);
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const sc = Math.floor(s % 60);
  const f = Math.floor((s - Math.floor(s)) * fps);
  return [h, m, sc, f]
    .map((n) => String(n).padStart(2, "0"))
    .join(":");
}

/** Deterministic pseudo-random in [0,1) from a seed string. */
export function prng(seed: string): number {
  let h = 2166136261;
  for (let i = 0; i < seed.length; i++) {
    h ^= seed.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return ((h >>> 0) % 10000) / 10000;
}
