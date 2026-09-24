import { useMemo, useState } from "react";
import type { CaptionEvent, Speaker } from "@/types/project";
import { EventItem } from "./EventItem";
import { Icon } from "@/lib/icons";

interface EventListProps {
  events: CaptionEvent[];
  speakers: Speaker[];
  selectedEventId: string | null;
  onSelect: (id: string) => void;
  onDelete: (id: string) => void;
  onNew: () => void;
}

export function EventList({
  events,
  speakers,
  selectedEventId,
  onSelect,
  onDelete,
  onNew,
}: EventListProps) {
  const [query, setQuery] = useState("");
  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return events;
    return events.filter(
      (e) =>
        e.text.toLowerCase().includes(q) ||
        e.id.toLowerCase().includes(q) ||
        e.type.toLowerCase().includes(q) ||
        speakers.find((s) => s.id === e.speaker_id)?.name.toLowerCase()
          .includes(q),
    );
  }, [events, query, speakers]);

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", minHeight: 0 }}>
      {/* header */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "0 2px var(--sp-3)",
        }}
      >
        <span
          className="mono"
          style={{ fontSize: 10, color: "var(--text-500)", letterSpacing: "0.04em" }}
        >
          {events.length} {events.length === 1 ? "event" : "events"}
        </span>
        <button className="primary" onClick={onNew} style={{ padding: "6px 12px", fontSize: 11.5 }}>
          <Icon name="plus" size={13} strokeWidth={2.4} />
          New
        </button>
      </div>

      {/* search */}
      <div className="searchbox" style={{ margin: "0 0 var(--sp-3)" }}>
        <Icon name="search" size={14} />
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search text, speaker, type…"
          style={{ background: "var(--bg-3)" }}
        />
      </div>

      {/* list / empty */}
      {filtered.length === 0 ? (
        <div className="empty-state">
          <div className="empty-icon">
            <Icon name="list" size={24} />
          </div>
          <div className="empty-title">
            {query ? "No matching events" : "No caption events"}
          </div>
          <div className="empty-body">
            {query
              ? "Try a different search term."
              : "Build your project from a transcript, or add events by hand."}
          </div>
          {!query && (
            <button className="primary" onClick={onNew} style={{ marginTop: 4 }}>
              <Icon name="plus" size={14} strokeWidth={2.4} />
              Create event
            </button>
          )}
        </div>
      ) : (
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            gap: 8,
          }}
        >
          {filtered.map((event) => (
            <EventItem
              key={event.id}
              event={event}
              speakers={speakers}
              isSelected={selectedEventId === event.id}
              onSelect={() => onSelect(event.id)}
              onDelete={() => onDelete(event.id)}
            />
          ))}
        </div>
      )}
    </div>
  );
}
