/** Minimal, crisp stroke icon set (Feather-style, 24px grid).
 *  Inline SVG so the build has no runtime icon dependency.
 */
import React from "react";

export type IconName =
  | "logo"
  | "undo"
  | "redo"
  | "plus"
  | "user"
  | "users"
  | "film"
  | "list"
  | "cursor"
  | "deselect"
  | "copy"
  | "paste"
  | "play"
  | "pause"
  | "skip-back"
  | "step-back"
  | "step-fwd"
  | "skip-fwd"
  | "export"
  | "download"
  | "settings"
  | "search"
  | "sliders"
  | "timeline"
  | "monitor"
  | "trash"
  | "music"
  | "sfx"
  | "close"
  | "chevron"
  | "lock"
  | "check"
  | "zoom-in"
  | "zoom-out"
  | "lock2"
  | "sparkle";

const PATHS: Record<IconName, React.ReactNode> = {
  logo: (
    <>
      <rect x="3" y="5" width="18" height="14" rx="3" />
      <path d="M7 10h7M7 14h4" strokeLinecap="round" />
      <circle cx="16.5" cy="14" r="1.6" fill="currentColor" stroke="none" />
    </>
  ),
  undo: (
    <>
      <path d="M9 14L4 9l5-5" />
      <path d="M4 9h11a5 5 0 0 1 5 5v0a5 5 0 0 1-5 5H9" strokeLinecap="round" />
    </>
  ),
  redo: (
    <>
      <path d="M15 14l5-5-5-5" />
      <path d="M20 9H9a5 5 0 0 0-5 5v0a5 5 0 0 0 5 5h6" strokeLinecap="round" />
    </>
  ),
  plus: <path d="M12 5v14M5 12h14" strokeLinecap="round" />,
  user: (
    <>
      <circle cx="12" cy="8" r="3.5" />
      <path d="M5 20c0-3.3 3.1-6 7-6s7 2.7 7 6" strokeLinecap="round" />
    </>
  ),
  users: (
    <>
      <circle cx="9" cy="8" r="3" />
      <path d="M3 20c0-3 2.7-5 6-5s6 2 6 5" strokeLinecap="round" />
      <path d="M16 5.5a3 3 0 0 1 0 5M21 20c0-2.4-1.4-4.2-3.6-4.8" strokeLinecap="round" />
    </>
  ),
  film: (
    <>
      <rect x="3" y="4" width="18" height="16" rx="2.5" />
      <path d="M7 4v16M17 4v16M3 9h4M3 15h4M17 9h4M17 15h4" />
    </>
  ),
  list: (
    <>
      <path d="M8 6h12M8 12h12M8 18h12" strokeLinecap="round" />
      <circle cx="4" cy="6" r="1.2" fill="currentColor" stroke="none" />
      <circle cx="4" cy="12" r="1.2" fill="currentColor" stroke="none" />
      <circle cx="4" cy="18" r="1.2" fill="currentColor" stroke="none" />
    </>
  ),
  cursor: <path d="M6 4l6 15 2.2-6.2L20 11 6 4z" strokeLinejoin="round" />,
  deselect: (
    <>
      <circle cx="12" cy="12" r="8.5" />
      <path d="M8.5 12h7" strokeLinecap="round" />
    </>
  ),
  copy: (
    <>
      <rect x="9" y="9" width="11" height="11" rx="2.5" />
      <path d="M5 15V6a2 2 0 0 1 2-2h9" strokeLinecap="round" />
    </>
  ),
  paste: (
    <>
      <rect x="6" y="5" width="12" height="16" rx="2.5" />
      <path d="M9 5V4h6v1" />
      <path d="M9 12h6M9 16h4" strokeLinecap="round" />
    </>
  ),
  play: <path d="M7 5l12 7-12 7V5z" strokeLinejoin="round" fill="currentColor" stroke="none" />,
  pause: (
    <>
      <rect x="7" y="5" width="3.6" height="14" rx="1.2" fill="currentColor" stroke="none" />
      <rect x="13.4" y="5" width="3.6" height="14" rx="1.2" fill="currentColor" stroke="none" />
    </>
  ),
  "skip-back": (
    <>
      <path d="M18 5v14L9 12 18 5z" fill="currentColor" stroke="none" />
      <path d="M6.5 5v14" strokeLinecap="round" />
    </>
  ),
  "step-back": (
    <>
      <path d="M17 5v14L9 12l8-7z" fill="currentColor" stroke="none" />
      <path d="M6.5 5v14" strokeLinecap="round" />
    </>
  ),
  "step-fwd": (
    <>
      <path d="M7 5v14l8-7-8-7z" fill="currentColor" stroke="none" />
      <path d="M17.5 5v14" strokeLinecap="round" />
    </>
  ),
  "skip-fwd": (
    <>
      <path d="M6 5v14l9-7-9-7z" fill="currentColor" stroke="none" />
      <path d="M17.5 5v14" strokeLinecap="round" />
    </>
  ),
  export: (
    <>
      <path d="M12 15V4M8 8l4-4 4 4" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M5 15v3a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-3" strokeLinecap="round" />
    </>
  ),
  download: (
    <>
      <path d="M12 4v11M8 11l4 4 4-4" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M5 19h14" strokeLinecap="round" />
    </>
  ),
  settings: (
    <>
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 15a1.6 1.6 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.6 1.6 0 0 0-1.8-.3 1.6 1.6 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.6 1.6 0 0 0-1-1.5 1.6 1.6 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.6 1.6 0 0 0 .3-1.8 1.6 1.6 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.6 1.6 0 0 0 1.5-1 1.6 1.6 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.6 1.6 0 0 0 1.8.3H9a1.6 1.6 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.6 1.6 0 0 0 1 1.5 1.6 1.6 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.6 1.6 0 0 0-.3 1.8V9a1.6 1.6 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.6 1.6 0 0 0-1.5 1z" />
    </>
  ),
  search: (
    <>
      <circle cx="11" cy="11" r="7" />
      <path d="M20 20l-3.5-3.5" strokeLinecap="round" />
    </>
  ),
  sliders: (
    <>
      <path d="M4 7h10M18 7h2M4 17h2M10 17h10" strokeLinecap="round" />
      <circle cx="16" cy="7" r="2.2" />
      <circle cx="8" cy="17" r="2.2" />
    </>
  ),
  timeline: (
    <>
      <path d="M4 7h16M4 12h16M4 17h16" strokeLinecap="round" />
      <rect x="7" y="5.5" width="6" height="3" rx="1" fill="currentColor" stroke="none" />
      <rect x="11" y="10.5" width="7" height="3" rx="1" fill="currentColor" stroke="none" />
      <rect x="6" y="15.5" width="5" height="3" rx="1" fill="currentColor" stroke="none" />
    </>
  ),
  monitor: (
    <>
      <rect x="3" y="4" width="18" height="12" rx="2.5" />
      <path d="M8 20h8M12 16v4" strokeLinecap="round" />
    </>
  ),
  trash: (
    <>
      <path d="M4 7h16M9 7V5a1.5 1.5 0 0 1 1.5-1.5h3A1.5 1.5 0 0 1 15 5v2M6 7l1 13h10l1-13" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M10 11v6M14 11v6" strokeLinecap="round" />
    </>
  ),
  music: (
    <>
      <circle cx="7" cy="17" r="2.6" />
      <circle cx="17" cy="15" r="2.6" />
      <path d="M9.6 17V6.5L19.6 5v10" strokeLinecap="round" strokeLinejoin="round" />
    </>
  ),
  sfx: (
    <>
      <path d="M4 9v6h4l5 4V5L8 9H4z" strokeLinejoin="round" />
      <path d="M16 8.5a4.5 4.5 0 0 1 0 7" strokeLinecap="round" />
    </>
  ),
  close: <path d="M6 6l12 12M18 6L6 18" strokeLinecap="round" />,
  chevron: <path d="M6 9l6 6 6-6" strokeLinecap="round" strokeLinejoin="round" />,
  lock: (
    <>
      <rect x="5" y="11" width="14" height="9" rx="2.5" />
      <path d="M8 11V8a4 4 0 0 1 8 0v3" strokeLinecap="round" />
    </>
  ),
  lock2: (
    <>
      <rect x="5" y="11" width="14" height="9" rx="2.5" />
      <path d="M8 11V8a4 4 0 0 1 7.5-2" strokeLinecap="round" />
    </>
  ),
  check: <path d="M5 12l4.5 4.5L19 7" strokeLinecap="round" strokeLinejoin="round" />,
  "zoom-in": (
    <>
      <circle cx="11" cy="11" r="7" />
      <path d="M20 20l-3.5-3.5M8.5 11h5M11 8.5v5" strokeLinecap="round" />
    </>
  ),
  "zoom-out": (
    <>
      <circle cx="11" cy="11" r="7" />
      <path d="M20 20l-3.5-3.5M8.5 11h5" strokeLinecap="round" />
    </>
  ),
  sparkle: (
    <>
      <path d="M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8L12 3z" strokeLinejoin="round" />
      <path d="M18.5 15l.7 2 2 .7-2 .7-.7 2-.7-2-2-.7 2-.7.7-2z" strokeLinejoin="round" />
    </>
  ),
};

export function Icon({
  name,
  size = 18,
  strokeWidth = 1.8,
  className,
  style,
}: {
  name: IconName;
  size?: number;
  strokeWidth?: number;
  className?: string;
  style?: React.CSSProperties;
}) {
  return (
    <svg
      viewBox="0 0 24 24"
      width={size}
      height={size}
      fill="none"
      stroke="currentColor"
      strokeWidth={strokeWidth}
      className={className}
      style={style}
      aria-hidden="true"
    >
      {PATHS[name]}
    </svg>
  );
}
