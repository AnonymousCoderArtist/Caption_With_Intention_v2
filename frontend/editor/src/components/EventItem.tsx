import type { CaptionEvent, Speaker } from "@/types/project";
import { fmtTime, EVENT_TYPES } from "@/lib/theme";
import { Icon } from "@/lib/icons";

interface EventItemProps {
  event: CaptionEvent;
  speakers: Speaker[];
  isSelected: boolean;
  onSelect: () => void;
  onDelete: () => void;
}

export function EventItem({
  event,
  speakers,
  isSelected,
  onSelect,
  onDelete,
}: EventItemProps) {
  const type = EVENT_TYPES[event.type] ?? EVENT_TYPES.custom;
  const speaker = speakers.find((s) => s.id === event.speaker_id);

  return (
    <div
      className={`card ev-card ${isSelected ? "selected" : ""}`}
      style={{ "--ev-color": type.color } as React.CSSProperties}
      onClick={onSelect}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => e.key === "Enter" && onSelect()}
    >
      <div className="ev-accent" />

      {/* top row */}
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 7 }}>
        <span className="badge" style={{ background: `${type.color}1f`, color: type.color }}>
          {type.label}
        </span>
        {event.off_camera && (
          <span className="badge badge-mute" style={{ letterSpacing: "0.05em" }}>
            Off-cam
          </span>
        )}
        {event.confidence != null && event.confidence < 0.8 && (
          <span className="badge badge-warning" style={{ letterSpacing: "0.05em" }}>
            {Math.round(event.confidence * 100)}%
          </span>
        )}
        <span
          style={{
            marginLeft: "auto",
            fontFamily: "var(--font-mono)",
            fontSize: 9.5,
            color: "var(--text-500)",
            letterSpacing: "-0.01em",
          }}
        >
          {event.id}
        </span>
      </div>

      {/* text */}
      <div
        style={{
          fontSize: 13.5,
          fontWeight: event.off_camera ? 450 : 540,
          fontStyle: event.off_camera ? "italic" : "normal",
          color: "var(--text-100)",
          lineHeight: 1.4,
          marginBottom: 9,
          overflow: "hidden",
          textOverflow: "ellipsis",
          display: "-webkit-box",
          WebkitLineClamp: 2,
          WebkitBoxOrient: "vertical",
        }}
      >
        {event.text || <span style={{ color: "var(--text-500)" }}>(empty)</span>}
      </div>

      {/* meta row */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 8,
          fontSize: 10.5,
          color: "var(--text-400)",
          fontFamily: "var(--font-mono)",
        }}
      >
        <span>{fmtTime(event.start)}</span>
        <span style={{ color: "var(--text-500)" }}>→</span>
        <span>{fmtTime(event.end)}</span>
        <span style={{ color: "var(--text-500)" }}>·</span>
        <span>{event.words.length}w</span>

        {speaker && (
          <span
            style={{
              marginLeft: "auto",
              display: "inline-flex",
              alignItems: "center",
              gap: 5,
              fontFamily: "var(--font-sans)",
              color: "var(--text-300)",
            }}
          >
            <span
              style={{
                width: 8,
                height: 8,
                borderRadius: "50%",
                background: speaker.color,
                boxShadow: `0 0 6px ${speaker.color}88`,
              }}
            />
            {speaker.name}
          </span>
        )}
      </div>

      {/* hover delete */}
      <button
        className="icon-btn sm"
        style={{
          position: "absolute",
          top: 8,
          right: 8,
          opacity: 0,
          width: 24,
          height: 24,
          color: "var(--text-400)",
          zIndex: 2,
        }}
        title="Delete event"
        onClick={(e) => {
          e.stopPropagation();
          onDelete();
        }}
        onMouseEnter={(e) => (e.currentTarget.style.opacity = "1")}
        onMouseLeave={(e) => (e.currentTarget.style.opacity = isSelected ? "0.5" : "0")}
      >
        <Icon name="trash" size={13} />
      </button>
    </div>
  );
}
