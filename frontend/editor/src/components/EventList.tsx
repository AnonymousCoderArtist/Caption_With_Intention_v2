import { useMemo, useState } from "react";
import type { CaptionEvent, Speaker } from "@/types/project";
import { EventItem } from "./EventItem";
import {speakerReviewReasons} from "@/lib/speakerReview";
import { Icon } from "@/lib/icons";

interface EventListProps {
  events: CaptionEvent[];
  speakers: Speaker[];
  selectedEventId: string | null;
  selectedIds?:string[];
  onSelect: (id: string, additive?:boolean) => void;
  onDelete: (id: string) => void;
  onNew: () => void;
}

export function EventList({
  events,
  speakers,
  selectedEventId,
  selectedIds,
  onSelect,
  onDelete,
  onNew,
}: EventListProps) {
  const [query, setQuery] = useState("");
  const [reviewOnly,setReviewOnly]=useState(false);
  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    const candidates=reviewOnly?events.filter(e=>speakerReviewReasons(e,speakers).length):events;
    if (!q) return candidates;
    return candidates.filter(
      (e) =>
        e.text.toLowerCase().includes(q) ||
        e.id.toLowerCase().includes(q) ||
        e.type.toLowerCase().includes(q) ||
        speakers.find((s) => s.id === e.speaker_id)?.name.toLowerCase()
          .includes(q),
    );
  }, [events, query, speakers,reviewOnly]);

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
          aria-label="Search captions"
          placeholder="Search text, speaker, type…"
          style={{ background: "var(--bg-3)" }}
        />
      </div>

      <label className="review-filter"><input type="checkbox" checked={reviewOnly} onChange={e=>setReviewOnly(e.target.checked)}/> Speaker review · {events.filter(e=>speakerReviewReasons(e,speakers).length).length}</label>
      {/* list / empty */}
      {filtered.length === 0 ? (
        <div className="empty-state">
          <div className="empty-icon">
            <Icon name="list" size={24} />
          </div>
          <div className="empty-title">
            {query ? "No matching events" : reviewOnly ? "Speaker review complete" : "No caption events"}
          </div>
          <div className="empty-body">
            {query
              ? "Try a different search term."
              : reviewOnly ? "No captions match this review filter. Turn it off to see all captions." : "Build your project from a transcript, or add events by hand."}
          </div>
          {!query && !reviewOnly && (
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
              isSelected={selectedIds?.includes(event.id)??selectedEventId === event.id}
              onSelect={additive => onSelect(event.id,additive)}
              onDelete={() => onDelete(event.id)}
            />
          ))}
        </div>
      )}
    </div>
  );
}
