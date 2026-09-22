import { useEffect, useState } from "react";
import type { CaptionEvent, EditorApiClient } from "@/api/client";

interface EventListProps {
  api: EditorApiClient | any;
  selectedEventId: string | null;
  onSelectEvent: (id: string) => void;
  onAction: () => void;
}

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${String(s).padStart(2, "0")}`;
}

export function EventList({ api, selectedEventId, onSelectEvent, onAction }: EventListProps) {
  const [events, setEvents] = useState<CaptionEvent[]>([]);

  useEffect(() => {
    const load = async () => {
      const r = await api.getEvents?.();
      if (r?.success) setEvents(r.data ?? []);
    };
    load();
  }, [api, onAction]);

  return (
    <div>
      <h2>Caption Events</h2>

      {events.length === 0 ? (
        <div style={{ color: "var(--text-400)", fontSize: "0.82rem" }}>
          No events yet. Create one in the editor.
        </div>
      ) : (
        <div>
          {events.map((event) => (
            <div
              key={event.id}
              className="event-card"
              style={{
                cursor: "pointer",
                padding: "var(--sp-3)",
              }}
              onClick={() => {
                onSelectEvent(event.id);
                onAction();
              }}
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
                    backgroundColor:
                      event.type === "dialogue"
                        ? "var(--accent-bg)"
                        : event.type === "sound_effect"
                          ? "var(--warning-bg)"
                          : event.type === "music"
                            ? "var(--purple-bg)"
                            : "rgba(255,255,255,0.05)",
                    color:
                      event.type === "dialogue"
                        ? "var(--accent)"
                        : event.type === "sound_effect"
                          ? "var(--warning)"
                          : event.type === "music"
                            ? "var(--purple)"
                            : "var(--text-300)",
                  }}
                >
                  {event.type}
                </span>
                <span style={{ fontSize: "0.72rem", color: "var(--text-400)", marginLeft: "auto", fontFamily: "var(--font-mono)" }}>
                  {event.id}
                </span>
              </div>

              <div style={{ fontSize: "0.82rem", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                {event.text || "(empty)"}
              </div>

              <div style={{ display: "flex", gap: "var(--sp-2)", fontSize: "0.7rem", color: "var(--text-400)", fontFamily: "var(--font-mono)", marginTop: "var(--sp-1)" }}>
                <span>{formatTime(event.start)}</span>
                <span>→</span>
                <span>{formatTime(event.end)}</span>
              </div>

              {selectedEventId === event.id && (
                <div style={{ marginTop: "var(--sp-1)", fontSize: "0.72rem", color: "var(--accent)" }}>
                  ← Selected
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
