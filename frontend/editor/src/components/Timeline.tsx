import { useEffect, useState } from "react";
import type { CaptionEvent, Project } from "@/types/project";
import type { EditorApiClient } from "@/api/client";

interface TimelineProps {
  api: EditorApiClient | any;
  onAction: () => void;
}

const TYPE_COLORS: Record<string, string> = {
  dialogue: "#4a9eff",
  sound_effect: "#d4a040",
  music: "#9070d0",
  speaker_overlap: "#e06060",
  custom: "#8287a0",
};

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${String(s).padStart(2, "0")}`;
}

function EventBar({
  event,
  projectDuration,
  onClick,
}: {
  event: CaptionEvent;
  projectDuration: number;
  onClick: () => void;
}) {
  if (projectDuration <= 0) return null;

  const left = (event.start / projectDuration) * 100;
  const width = Math.max(
    ((event.end - event.start) / projectDuration) * 100,
    0.3,
  );
  const color = TYPE_COLORS[event.type] ?? "#8287a0";

  return (
    <div
      className="timeline-bar"
      style={{
        left: `${left}%`,
        width: `${width}%`,
        backgroundColor: color,
        color: "var(--bg-0)",
      }}
      onClick={onClick}
      title={`${event.text || event.type} (${formatTime(event.start)} - ${formatTime(event.end)})`}
    >
      {width > 4 ? event.text.slice(0, 20) : ""}
    </div>
  );
}

export function Timeline({ api, onAction }: TimelineProps) {
  const [project, setProject] = useState<Project | null>(null);

  async function loadProject() {
    if (!api) return;
    try {
      const result = await api.getProject?.();
      if (result?.success) {
        setProject(result.data);
      }
    } catch {
      // silent
    }
  }

  useEffect(() => {
    loadProject();
  }, []);

  const duration = project?.video?.duration ?? 0;

  const rulerMarks = duration > 0
    ? Array.from({ length: Math.min(Math.ceil(duration / 10) + 1, 20) }).map((_, i) => i * 10)
    : [];

  return (
    <div className="panel" style={{ marginBottom: "var(--sp-4)", animation: "fadeIn 0.2s ease" }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "var(--sp-3)" }}>
        <h2 style={{ marginBottom: 0, border: "none", padding: 0 }}>Timeline</h2>
        {duration > 0 && (
          <span
            style={{
              fontSize: "0.78rem",
              fontWeight: 400,
              color: "var(--text-400)",
              fontFamily: "var(--font-mono)",
            }}
          >
            {formatTime(duration)}
          </span>
        )}
      </div>

      {/* Time ruler */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          fontSize: "0.66rem",
          color: "var(--text-400)",
          padding: "0 0 var(--sp-1) 0",
          fontFamily: "var(--font-mono)",
          marginBottom: "var(--sp-1)",
          borderBottom: "1px solid var(--border)",
          paddingBottom: "var(--sp-1)",
        }}
      >
        {rulerMarks.map((t) => (
          <span key={t}>{formatTime(t)}</span>
        ))}
      </div>

      {/* Playhead + Tracks */}
      <div style={{ position: "relative" }}>
        {duration > 0 && (
          <div
            style={{
              position: "absolute",
              top: 0,
              bottom: 0,
              left: "0px",
              width: "1px",
              background: "var(--danger)",
              zIndex: 10,
              pointerEvents: "none",
            }}
          />
        )}

        {/* Dialogue track */}
        <div className="timeline-track">
          <span
            style={{
              position: "absolute",
              top: "2px",
              left: "var(--sp-2)",
              fontSize: "0.62rem",
              color: "var(--text-400)",
              textTransform: "uppercase",
              letterSpacing: "0.06em",
              zIndex: 5,
            }}
          >
            Dialogue
          </span>
          {project?.events
            ?.filter((e) => e.type === "dialogue")
            .map((event) => (
              <EventBar
                key={event.id}
                event={event}
                projectDuration={duration}
                onClick={() => {}}
              />
            ))}
        </div>

        {/* SFX track */}
        <div className="timeline-track" style={{ height: "26px" }}>
          <span
            style={{
              position: "absolute",
              top: "2px",
              left: "var(--sp-2)",
              fontSize: "0.62rem",
              color: "var(--text-400)",
              textTransform: "uppercase",
              letterSpacing: "0.06em",
              zIndex: 5,
            }}
          >
            SFX
          </span>
          {project?.events
            ?.filter((e) => e.type === "sound_effect")
            .map((event) => (
              <EventBar
                key={event.id}
                event={event}
                projectDuration={duration}
                onClick={() => {}}
              />
            ))}
        </div>

        {/* Music track */}
        <div className="timeline-track" style={{ height: "26px" }}>
          <span
            style={{
              position: "absolute",
              top: "2px",
              left: "var(--sp-2)",
              fontSize: "0.62rem",
              color: "var(--text-400)",
              textTransform: "uppercase",
              letterSpacing: "0.06em",
              zIndex: 5,
            }}
          >
            Music
          </span>
          {project?.events
            ?.filter((e) => e.type === "music")
            .map((event) => (
              <EventBar
                key={event.id}
                event={event}
                projectDuration={duration}
                onClick={() => {}}
              />
            ))}
        </div>
      </div>

      {duration === 0 && (
        <div style={{ color: "var(--text-400)", fontSize: "0.82rem", marginTop: "var(--sp-2)" }}>
          Build a project from a transcript or load an existing project to see the timeline.
        </div>
      )}
    </div>
  );
}
