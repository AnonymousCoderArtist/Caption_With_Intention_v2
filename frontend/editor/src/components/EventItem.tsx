import type { CaptionEvent } from "@/types/project";

interface EventItemProps {
  event: CaptionEvent;
  isSelected: boolean;
  onSelect: () => void;
  onDelete: () => void;
}

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${String(s).padStart(2, "0")}`;
}

export function EventItem({ event, isSelected, onSelect, onDelete }: EventItemProps) {
  const typeColors: Record<string, string> = {
    dialogue: "var(--accent)",
    sound_effect: "var(--warning)",
    music: "#a78bfa",
    speaker_overlap: "var(--danger)",
    custom: "var(--text-secondary)",
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
          gap: "var(--sp-2)",
          marginBottom: "var(--sp-1)",
        }}
      >
        <span
          className={`badge badge-${event.type}`}
          style={{
            backgroundColor: typeColors[event.type] ?? "var(--border)",
            color: "var(--bg-0)",
          }}
        >
          {event.type}
        </span>
        <span style={{ fontSize: "0.72rem", color: "var(--text-400)", marginLeft: "auto", fontFamily: "var(--font-mono)" }}>
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
          gap: "var(--sp-2)",
          fontSize: "0.7rem",
          color: "var(--text-400)",
          fontFamily: "var(--font-mono)",
        }}
      >
        <span>{formatTime(event.start)}</span>
        <span>→</span>
        <span>{formatTime(event.end)}</span>
      </div>

      <button
        onClick={(e) => {
          e.stopPropagation();
          onDelete();
        }}
        style={{
          fontSize: "0.68rem",
          marginTop: "var(--sp-1)",
          color: "var(--danger)",
          opacity: 0.8,
          padding: "var(--sp-1)",
        }}
      >
        Delete event
      </button>
    </div>
  );
}
