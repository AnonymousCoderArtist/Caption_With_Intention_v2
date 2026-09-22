import { useEffect, useState } from "react";
import type { CaptionEvent, Project } from "@/types/project";
import type { EditorApiClient } from "@/api/client";

interface TimelineProps {
  api: EditorApiClient | any;
  onAction: () => void;
}

const TYPE_COLORS: Record<string, string> = {
  dialogue: "var(--color-accent)",
  sound_effect: "var(--color-warning)",
  music: "#a78bfa",
  speaker_overlap: "var(--color-danger)",
  custom: "var(--color-text-secondary)",
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
  const color = TYPE_COLORS[event.type] ?? "var(--color-border)";

  return (
    <div
      className="timeline-bar"
      style={{
        left: `${left}%`,
        width: `${width}%`,
        backgroundColor: color,
        color: "var(--color-bg-primary)",
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
      // silent — mock API may not have data
    }
  }

  useEffect(() => {
    loadProject();
  }, []);

  const duration = project?.video?.duration ?? 0;

  return (
    <div className="panel" style={{ marginBottom: "var(--sp-5)" }}>
      <h2>
        Timeline
        {duration > 0 && (
          <span
            style={{
              fontSize: "0.78rem",
              fontWeight: 400,
              color: "var(--text-400)",
              marginLeft: "var(--sp-2)",
            }}
          >
            {formatTime(duration)}
          </span>
        )}
      </h2>

      {/* Time ruler */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          fontSize: "0.68rem",
          color: "var(--text-400)",
          padding: "0 0 var(--sp-1) 0",
          fontFamily: "var(--font-mono)",
        }}
      >
        {duration > 0 &&
          Array.from({ length: Math.min(Math.ceil(duration / 10) + 1, 12) }).map((_, i) => (
            <span key={i}>{formatTime(i * 10)}</span>
          ))}
      </div>

      {/* Dialogue track */}
      <div className="timeline-track">
        <span
          style={{
            position: "absolute",
            top: "2px",
            left: "var(--spacing-sm)",
            fontSize: "0.65rem",
            color: "var(--color-text-muted)",
            textTransform: "uppercase",
            letterSpacing: "0.05em",
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

      {duration === 0 && (
        <div style={{ color: "var(--text-400)", fontSize: "0.82rem", marginTop: "var(--sp-2)" }}>
          Build a project from a transcript or load an existing project to see the timeline.
        </div>
      )}
    </div>
  );
}
