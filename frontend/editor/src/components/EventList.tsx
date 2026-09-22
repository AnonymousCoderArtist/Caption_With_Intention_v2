"""Event list with timing display and selection."""

import type { CaptionEvent } from "@/types/project";
import type { EditorApiClient } from "@/api/client";

interface EventListProps {
  api: EditorApiClient | any;
  selectedEventId: string | null;
  onSelectEvent: (id: string) => void;
  onAction: () => void;
}

interface EventItemProps {
  event: CaptionEvent;
  isSelected: boolean;
  onSelect: () => void;
  onDelete: () => void;
}

function formatTime(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  const ms = Math.round((seconds % 1) * 100);
  if (h > 0) {
    return `${h}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}.${String(ms).padStart(2, "0")}`;
  }
  return `${m}:${String(s).padStart(2, "0")}.${String(ms).padStart(2, "0")}`;
}

function EventItem({ event, isSelected, onSelect, onDelete }: EventItemProps) {
  const typeColors: Record<string, string> = {
    dialogue: "var(--color-accent)",
    sound_effect: "var(--color-warning)",
    music: "#a78bfa",
    speaker_overlap: "var(--color-danger)",
    custom: "var(--color-text-secondary)",
  };

  return (
    <div
      className={`event-card ${isSelected ? "selected" : ""}`}
      onClick={onSelect}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "var(--spacing-sm)",
          marginBottom: "var(--spacing-xs)",
        }}
      >
        <span
          className="badge"
          style={{
            backgroundColor: typeColors[event.type] ?? "var(--color-border)",
            color: "var(--color-bg-primary)",
          }}
        >
          {event.type}
        </span>
        {event.off_camera && (
          <span className="badge" style={{ backgroundColor: "var(--color-danger)", color: "white" }}>
            OFF-CAM
          </span>
        )}
        <span style={{ fontSize: "0.75rem", color: "var(--color-text-muted)", marginLeft: "auto" }}>
          {event.id}
        </span>
      </div>

      <div
        style={{
          fontFamily: "var(--font-mono)",
          fontSize: "0.8rem",
          marginBottom: "2px",
        }}
      >
        {event.text || "(empty)"}
      </div>

      <div
        style={{
          display: "flex",
          gap: "var(--spacing-md)",
          fontSize: "0.75rem",
          color: "var(--color-text-muted)",
          fontFamily: "var(--font-mono)",
        }}
      >
        <span>{formatTime(event.start)}</span>
        <span>→</span>
        <span>{formatTime(event.end)}</span>
        <span style={{ marginLeft: "auto" }}>
          {event.words.length} words
        </span>
      </div>

      <button
        onClick={(e) => {
          e.stopPropagation();
          onDelete();
        }}
        style={{
          fontSize: "0.7rem",
          marginTop: "var(--spacing-xs)",
          color: "var(--color-danger)",
          opacity: 0.7,
        }}
      >
        Delete event
      </button>
    </div>
  );
}

export function EventList({
  api,
  selectedEventId,
  onSelectEvent,
  onAction,
}: EventListProps) {
  return (
    <div>
      <h2>Caption Events</h2>
      <div style={{ marginBottom: "var(--spacing-md)", display: "flex", gap: "var(--spacing-sm)" }}>
        <button onClick={() => onSelectEvent("__new__")}>+ New Event</button>
      </div>
      <div>
        {/* Events will be populated by the EventEditor for now — they share the panel */}
      </div>
    </div>
  );
}
