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
  return (
    <div
      className={`event-card ${isSelected ? "selected" : ""}`}
      onClick={onSelect}
      style={{ animation: "fadeIn 0.15s ease" }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "var(--sp-2)",
          marginBottom: "var(--sp-1)",
        }}
      >
        <span className={`badge badge-${event.type}`}>
          {event.type}
        </span>
        <span style={{ fontSize: "0.7rem", color: "var(--text-400)", marginLeft: "auto", fontFamily: "var(--font-mono)" }}>
          {event.id}
        </span>
      </div>

      <div
        style={{
          fontFamily: "var(--font-sans)",
          fontSize: "0.84rem",
          marginBottom: "3px",
          overflow: "hidden",
          textOverflow: "ellipsis",
          whiteSpace: "nowrap",
          color: "var(--text-200)",
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
          alignItems: "center",
        }}
      >
        <span>{formatTime(event.start)}</span>
        <span style={{ color: "var(--text-500)" }}>&#8594;</span>
        <span>{formatTime(event.end)}</span>
      </div>

      <button
        onClick={(e) => {
          e.stopPropagation();
          onDelete();
        }}
        className="event-delete-btn"
        style={{
          fontSize: "0.68rem",
          marginTop: "var(--sp-1)",
          color: "var(--danger)",
          opacity: 0,
          padding: "var(--sp-1) var(--sp-2)",
          background: "transparent",
          border: "none",
          cursor: "pointer",
          transition: "opacity var(--t-fast)",
        }}
      >
        &#10005; Delete
      </button>

      <style>{`
        .event-card:hover .event-delete-btn {
          opacity: 0.7;
        }
        .event-card:hover .event-delete-btn:hover {
          opacity: 1;
        }
      `}</style>
    </div>
  );
}
