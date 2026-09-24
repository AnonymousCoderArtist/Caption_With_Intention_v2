/** The hero: a cinematic 16:9 monitor that live-renders the CWI treatment.
 *
 *  Read-ahead white (90%) -> word-onset color sync -> 15% pop -> variable
 *  size / weight / width / italic, all driven by the playhead.
 */
import { useEffect, useRef, useState } from "react";
import type { CaptionEvent, Project, Word } from "@/types/project";
import { fmtTimecode } from "@/lib/theme";
import { Icon } from "@/lib/icons";

function useSize(ref: React.RefObject<HTMLElement | null>) {
  const [size, setSize] = useState({ w: 0, h: 0 });
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const ro = new ResizeObserver((entries) => {
      const r = entries[0].contentRect;
      setSize({ w: r.width, h: r.height });
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, [ref]);
  return size;
}

/* Smooth pop envelope: fast ease-out attack, gentle ease-in-out settle. */
function easeOutCubic(x: number) {
  return 1 - Math.pow(1 - x, 3);
}
function easeInOutCubic(x: number) {
  return x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2;
}
function popAmount(p: number, amp: number): number {
  if (p <= 0 || p >= 1) return 0;
  const atk = 0.4; // attack occupies first 40% of the window
  const v = p < atk ? easeOutCubic(p / atk) : 1 - easeInOutCubic((p - atk) / (1 - atk));
  return v * amp;
}

/** word -> visual props for the given playhead time */
function wordStyle(word: Word, t: number, monH: number, event: CaptionEvent, isNonDialogue: boolean) {
  const style = event.style;
  const popDur = style.pop_duration && style.pop_duration > 0 ? style.pop_duration : 0.24;
  const onset = t >= word.start;
  const spoken = onset && !isNonDialogue;

  // color: read-ahead white until onset, then speaker color
  const readAhead = style.read_ahead_opacity ?? 0.9;
  const color = spoken ? word.color : `rgba(255,255,255,${readAhead})`;

  // pop (music never animates)
  const amp = style.pop_scale - 1;
  const p = (t - word.start) / popDur;
  const scale = event.type !== "music" ? 1 + popAmount(p, amp) : 1;

  return {
    fontSize: `calc(${monH}px * ${word.size_pct} / 100)`,
    fontWeight: word.weight,
    fontStretch: `${word.width}%`,
    fontStyle: word.italic ? "italic" : "normal",
    color,
    opacity: word.opacity,
    transform: `scale(${scale})`,
    textShadow: spoken ? `0 0 16px ${word.color}55` : "0 1px 2px rgba(0,0,0,0.5)",
  } as React.CSSProperties;
}

export function PreviewMonitor({
  project,
  time,
  fps,
}: {
  project: Project | null;
  time: number;
  fps: number;
}) {
  const frameRef = useRef<HTMLDivElement>(null);
  const { h: monH } = useSize(frameRef);

  const duration = project?.video.duration ?? 0;
  const active =
    project?.events.find((e) => time >= e.start && time < e.end) ?? null;

  // scene background tinted by the active speaker
  const activeColor = active
    ? project?.speakers.find((s) => s.id === active.speaker_id)?.color ??
      "#E5E517"
    : "#E5E517";
  const drift = (Math.sin(time * 0.35) * 30).toFixed(1);
  const drift2 = (Math.cos(time * 0.22) * 24).toFixed(1);

  return (
    <div className="monitor-wrap">
      <div className="monitor">
        <div className="monitor-frame" ref={frameRef} style={{ position: "absolute", inset: 0 }}>
          {/* abstract cinematic scene */}
          <div className="scene">
            <div
              className="orb"
              style={{
                width: "46%",
                height: "46%",
                left: "8%",
                top: "6%",
                background: `radial-gradient(circle, ${activeColor}66, transparent 70%)`,
                transform: `translate(${drift}px, ${drift2}px)`,
                transition: "background 0.6s ease",
              }}
            />
            <div
              className="orb"
              style={{
                width: "40%",
                height: "40%",
                right: "6%",
                top: "18%",
                background: "radial-gradient(circle, rgba(23,229,229,0.4), transparent 70%)",
                transform: `translate(${-drift2}px, ${drift}px)`,
              }}
            />
            <div
              className="orb"
              style={{
                width: "52%",
                height: "40%",
                left: "30%",
                bottom: "-6%",
                background: "radial-gradient(circle, rgba(229,23,229,0.3), transparent 72%)",
                transform: `translate(${drift2}px, ${-drift}px)`,
              }}
            />
            <div className="grain" />
            <div className="skyline" />
            <div className="vignette" />
          </div>

          {/* caption area */}
          <div className="caption-area">
            {active && (
              <div
                key={active.id}
                className="caption-box"
                style={
                  {
                    "--box-opacity": active.style.box_opacity,
                    "--box-pad": `${active.style.box_padding}px`,
                  } as React.CSSProperties
                }
              >
                {(() => {
                  const isND = active.type === "sound_effect" || active.type === "music";
                  const words = active.words.length ? active.words : [{ text: active.text, start: active.start, end: active.end, size_pct: 5, weight: 700, width: 100, color: "#fff", opacity: 1, italic: false, confidence: null, source_model: null, source_timestamp: null, manual_override: false, review_state: "accepted" as const, syllables: null }];
                  // split into up to 2 lines
                  const mid = Math.ceil(words.length / 2);
                  const lines =
                    words.length > 4
                      ? [words.slice(0, mid), words.slice(mid)]
                      : [words];
                  return lines.map((line, li) => (
                    <div className="caption-line" key={li}>
                      {line.map((word, wi) => (
                        <span
                          key={wi}
                          className={`cap-word ${isND ? (active.type === "music" ? "cap-music" : "cap-sfx") : ""}`}
                          style={wordStyle(word as Word, time, monH, active, isND)}
                        >
                          {(word as Word).text}
                        </span>
                      ))}
                    </div>
                  ));
                })()}
              </div>
            )}
          </div>

          {/* corner brackets */}
          <div className="corner tl" />
          <div className="corner tr" />
          <div className="corner bl" />
          <div className="corner br" />

          {/* meta */}
          <div className="monitor-meta">
            <span className={`monitor-rec ${time > 0 ? "playing" : ""}`}>
              <span className="dot" />
              {active ? "CAPTIONS" : "MONITOR"}
            </span>
            <span className="monitor-tc">
              {fmtTimecode(time, fps)}
            </span>
          </div>

          {/* duration bar (faint) */}
          {duration > 0 && (
            <div
              style={{
                position: "absolute",
                left: 40,
                right: 40,
                bottom: 14,
                height: 2,
                background: "rgba(255,255,255,0.14)",
                borderRadius: 2,
                zIndex: 8,
              }}
            >
              <div
                style={{
                  width: `${Math.min(100, (time / duration) * 100)}%`,
                  height: "100%",
                  background: "var(--accent)",
                  borderRadius: 2,
                  boxShadow: "0 0 8px var(--accent-glow)",
                }}
              />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

/** Transport control bar under the monitor. */
export function Transport({
  time,
  duration,
  playing,
  fps,
  onToggle,
  onScrub,
  onStep,
  onSkip,
}: {
  time: number;
  duration: number;
  playing: boolean;
  fps: number;
  onToggle: () => void;
  onScrub: (t: number) => void;
  onStep: (dir: -1 | 1) => void;
  onSkip: (dir: "start" | "end") => void;
}) {
  const barRef = useRef<HTMLDivElement>(null);
  const pct = duration > 0 ? Math.min(100, (time / duration) * 100) : 0;

  const scrubTo = (clientX: number) => {
    const el = barRef.current;
    if (!el) return;
    const r = el.getBoundingClientRect();
    const ratio = Math.min(1, Math.max(0, (clientX - r.left) / r.width));
    onScrub(ratio * duration);
  };

  return (
    <div className="transport">
      <button className="t-btn" onClick={() => onSkip("start")} title="Skip to start">
        <Icon name="skip-back" size={15} />
      </button>
      <button className="t-btn" onClick={() => onStep(-1)} title="Previous frame">
        <Icon name="step-back" size={15} />
      </button>

      <button className="t-btn t-play" onClick={onToggle} title={playing ? "Pause" : "Play"}>
        <Icon name={playing ? "pause" : "play"} size={18} />
      </button>

      <button className="t-btn" onClick={() => onStep(1)} title="Next frame">
        <Icon name="step-fwd" size={15} />
      </button>
      <button className="t-btn" onClick={() => onSkip("end")} title="Skip to end">
        <Icon name="skip-fwd" size={15} />
      </button>

      <div className="scrub">
        <div
          className="scrub-track"
          ref={barRef}
          onPointerDown={(e) => {
            (e.target as HTMLElement).setPointerCapture?.(e.pointerId);
            scrubTo(e.clientX);
            const move = (ev: PointerEvent) => scrubTo(ev.clientX);
            const up = () => {
              window.removeEventListener("pointermove", move);
              window.removeEventListener("pointerup", up);
            };
            window.addEventListener("pointermove", move);
            window.addEventListener("pointerup", up);
          }}
        >
          <div className="scrub-fill" style={{ width: `${pct}%` }} />
          <div className="scrub-knob" style={{ left: `${pct}%` }} />
        </div>
      </div>

      <div className="tc">
        {fmtTimecode(time, fps)}
        <span className="dim"> / {fmtTimecode(duration, fps)}</span>
      </div>
    </div>
  );
}
