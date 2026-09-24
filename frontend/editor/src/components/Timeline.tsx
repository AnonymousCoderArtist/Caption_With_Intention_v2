/** Pro multi-track timeline: ruler · video · audio · captions · words. */
import { useMemo, useState } from "react";
import type { CaptionEvent, Project } from "@/types/project";
import { fmtTime, EVENT_TYPES, prng, readableOn } from "@/lib/theme";
import { Icon } from "@/lib/icons";

const HEAD_W = 132;

interface TimelineProps {
  project: Project | null;
  selectedEventId: string | null;
  time: number;
  onSelectEvent: (id: string) => void;
  onScrub: (t: number) => void;
}

export function Timeline({
  project,
  selectedEventId,
  time,
  onSelectEvent,
  onScrub,
}: TimelineProps) {
  const duration = project?.video.duration ?? 0;
  const [ppx, setPpx] = useState(() =>
    duration > 0 ? Math.max(30, Math.min(140, 1100 / duration)) : 60,
  );

  const contentW = duration * ppx + HEAD_W;

  // waveform bars (deterministic)
  const wave = useMemo(() => {
    const n = 96;
    const arr: number[] = [];
    for (let i = 0; i < n; i++) {
      // shape the waveform around where dialogue happens
      const t = (i / n) * duration;
      const near = project?.events.some(
        (e) => t >= e.start - 0.5 && t <= e.end + 0.3,
      )
        ? 0.7
        : 0.25;
      arr.push(0.15 + prng(`wave${i}`) * near);
    }
    return arr;
  }, [project, duration]);

  const tickStep = ppx >= 60 ? 1 : ppx >= 22 ? 5 : 10;
  const ticks: { t: number; major: boolean }[] = [];
  if (duration > 0) {
    for (let t = 0; t <= duration; t += tickStep) {
      ticks.push({ t, major: t % (tickStep * 5) === 0 || t === 0 });
    }
  }

  const speakerColor = (e: CaptionEvent) => {
    if (e.type === "dialogue" || e.type === "speaker_overlap") {
      return (
        project?.speakers.find((s) => s.id === e.speaker_id)?.color ??
        EVENT_TYPES[e.type]?.color ??
        "#888"
      );
    }
    return EVENT_TYPES[e.type]?.color ?? "#888";
  };

  const selectedEvent = project?.events.find((e) => e.id === selectedEventId);

  const TrackHead = ({ label, color }: { label: string; color?: string }) => (
    <div
      className="tl-track-head"
      style={{ position: "sticky", left: 0 }}
    >
      <span className="dot" style={{ "--dot": color ?? "var(--text-400)" } as React.CSSProperties} />
      {label}
    </div>
  );

  const Lane = ({ children }: { children: React.ReactNode }) => (
    <div
      className="tl-lane"
      style={{ width: duration * ppx, position: "relative" }}
    >
      {children}
    </div>
  );

  const EventClip = ({ e }: { e: CaptionEvent }) => {
    const left = e.start * ppx;
    const width = Math.max(6, (e.end - e.start) * ppx);
    const color = speakerColor(e);
    const ink = readableOn(color);
    const sel = e.id === selectedEventId;
    return (
      <div
        key={e.id}
        className={`tl-clip ${sel ? "selected" : ""}`}
        style={{
          left,
          width,
          background: `linear-gradient(180deg, ${color}, ${color}d9)`,
          color: ink,
        }}
        title={`${e.text} (${fmtTime(e.start)} → ${fmtTime(e.end)})`}
        onClick={() => onSelectEvent(e.id)}
      >
        <span className="clip-label">{e.text || e.type}</span>
      </div>
    );
  };

  return (
    <div className="timeline" style={{ margin: "0 0 var(--sp-4)" }}>
      {/* header */}
      <div className="tl-head">
        <div className="tl-title">
          <Icon name="timeline" size={16} />
          Timeline
          <span className="mono" style={{ fontSize: 10.5, color: "var(--text-400)" }}>
            {duration > 0 ? `${fmtTime(duration)}` : "0:00"}
          </span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <button
            className="subtle"
            onClick={() => setPpx((p) => Math.max(16, p * 0.8))}
            style={{ width: 28, height: 28, padding: 0 }}
            title="Zoom out"
          >
            <Icon name="zoom-out" size={15} />
          </button>
          <div className="tl-zoom">
            <span className="mono">{Math.round(ppx)} px/s</span>
          </div>
          <button
            className="subtle"
            onClick={() => setPpx((p) => Math.min(400, p * 1.25))}
            style={{ width: 28, height: 28, padding: 0 }}
            title="Zoom in"
          >
            <Icon name="zoom-in" size={15} />
          </button>
          <span className="pill">
            {project?.events.length ?? 0} events
          </span>
        </div>
      </div>

      {/* body */}
      <div className="tl-body">
        <div style={{ width: contentW, position: "relative", minHeight: "100%" }}>
          {/* ruler */}
          <div className="tl-ruler" style={{ width: contentW }}>
            <div
              style={{
                position: "sticky",
                left: 0,
                width: HEAD_W,
                height: "100%",
                background: "var(--bg-3)",
                borderRight: "1px solid var(--border-2)",
                display: "flex",
                alignItems: "center",
                justifyContent: "flex-end",
                paddingRight: 10,
                fontSize: 9.5,
                color: "var(--text-400)",
                letterSpacing: "0.1em",
                zIndex: 5,
              }}
            >
              TIME
            </div>
            {ticks.map((tk) => (
              <div
                key={tk.t}
                className={`tl-tick ${tk.major ? "major" : ""}`}
                style={{ left: HEAD_W + tk.t * ppx }}
              >
                {tk.major && <span>{fmtTime(tk.t)}</span>}
              </div>
            ))}
          </div>

          {/* video */}
          <div className="tl-track" style={{ width: contentW, height: 46 }}>
            <TrackHead label="Video" color="var(--text-400)" />
            <Lane>
              <div
                style={{
                  position: "absolute",
                  inset: 5,
                  borderRadius: 6,
                  background:
                    "linear-gradient(90deg,#2a2a3a,#22222f 40%,#262634 70%,#1e1e28)",
                  boxShadow: "inset 0 1px 0 rgba(255,255,255,0.08)",
                  display: "flex",
                  alignItems: "center",
                  padding: "0 12px",
                  color: "var(--text-400)",
                  fontSize: 11,
                  fontWeight: 540,
                  letterSpacing: "0.04em",
                }}
              >
                <Icon name="film" size={13} style={{ marginRight: 8 }} />
                Source · {project?.video.width ?? 1920}×{project?.video.height ?? 1080}
              </div>
            </Lane>
          </div>

          {/* audio */}
          <div className="tl-track" style={{ width: contentW, height: 40 }}>
            <TrackHead label="Audio" color="var(--char-cyan)" />
            <Lane>
              <div className="tl-wave">
                {wave.map((v, i) => (
                  <span key={i} style={{ height: `${v * 100}%` }} />
                ))}
              </div>
            </Lane>
          </div>

          {/* captions tracks */}
          {(
            [
              ["dialogue", "Dialogue", "var(--ev-dialogue)"],
              ["sound_effect", "SFX", "var(--ev-sfx)"],
              ["music", "Music", "var(--ev-music)"],
            ] as const
          ).map(([type, label, color]) => (
            <div
              key={type}
              className="tl-track"
              style={{ width: contentW, height: type === "dialogue" ? 44 : 38 }}
            >
              <TrackHead label={label} color={color} />
              <Lane>
                {project?.events
                  .filter((e) => e.type === type)
                  .map((e) => (
                    <EventClip key={e.id} e={e} />
                  ))}
              </Lane>
            </div>
          ))}

          {/* word-level track (for selected event) */}
          <div className="tl-track" style={{ width: contentW, height: 40 }}>
            <TrackHead label="Words" color="var(--accent)" />
            <Lane>
              {selectedEvent?.words.map((w2, i) => {
                const left = w2.start * ppx;
                const width = Math.max(3, (w2.end - w2.start) * ppx);
                return (
                  <div
                    key={i}
                    className="tl-wordbar"
                    title={w2.text}
                    style={{
                      left,
                      width,
                      background:
                        w2.color.startsWith("#FFFFFF") || w2.color === "#FFFFFF"
                          ? "#fff"
                          : w2.color,
                    }}
                  />
                );
              })}
              {!selectedEvent && (
                <div
                  style={{
                    position: "absolute",
                    inset: 0,
                    display: "flex",
                    alignItems: "center",
                    padding: "0 14px",
                    color: "var(--text-500)",
                    fontSize: 11,
                  }}
                >
                  Select an event to reveal its word timing
                </div>
              )}
            </Lane>
          </div>

          {/* playhead */}
          <div
            className="tl-playhead"
            style={{ left: HEAD_W + time * ppx }}
            onClick={(e) => {
              e.stopPropagation();
            }}
          />
        </div>
      </div>

      {/* scrub-on-ruler handled by transport; keep ref-friendly hook */}
      <span
        style={{ display: "none" }}
        onClick={() => onScrub(0)}
        aria-hidden
      />
    </div>
  );
}
