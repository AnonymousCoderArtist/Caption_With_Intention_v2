"""Event editor — add/edit caption events, words, syllables, and timing.

This is the primary workhorse panel where users build and
edit caption projects manually.
"""

import { useState, useEffect, useMemo } from "react";
import type { CaptionEvent, Word, Speaker } from "@/types/project";
import type { EditorApiClient } from "@/api/client";
import { EventItem } from "./EventItem";

interface EventEditorProps {
  api: EditorApiClient | any;
  selectedEventId: string | null;
  onSelectEvent: (id: string | null) => void;
  onAction: () => void;
}

interface NewEventFormProps {
  api: EditorApiClient | any;
  speakers: Speaker[];
  onCreated: (event: CaptionEvent) => void;
  onCancel: () => void;
}

function NewEventForm({ api, speakers, onCreated, onCancel }: NewEventFormProps) {
  const [text, setText] = useState("");
  const [start, setStart] = useState<number>(0);
  const [end, setEnd] = useState<number>(1);
  const [speakerId, setSpeakerId] = useState<string>("");
  const [eventType, setEventType] = useState<string>("dialogue");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!text.trim()) return;
    if (!api) return;
    try {
      const result = await api.addEvent({
        text: text.trim(),
        start,
        end,
        speaker_id: speakerId || null,
        event_type: eventType,
      });
      if (result?.success) {
        onCreated(result.data);
      }
    } catch (err) {
      console.error("Failed to add event:", err);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="panel" style={{ marginBottom: "var(--spacing-lg)" }}>
      <h3>New Caption Event</h3>
      <div className="inspector-field">
        <label>Text</label>
        <input
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Enter caption text..."
          autoFocus
          onKeyDown={(e) => {
            if (e.key === "Enter") handleSubmit(e);
          }}
        />
      </div>
      <div style={{ display: "flex", gap: "var(--spacing-md)", flexWrap: "wrap" }}>
        <div className="inspector-field">
          <label>Start</label>
          <input
            type="number"
            step="0.01"
            value={start}
            onChange={(e) => setStart(parseFloat(e.target.value) || 0)}
            min={0}
          />
        </div>
        <div className="inspector-field">
          <label>End</label>
          <input
            type="number"
            step="0.01"
            value={end}
            onChange={(e) => setEnd(parseFloat(e.target.value) || 1)}
            min={start + 0.01}
          />
        </div>
        <div className="inspector-field">
          <label>Speaker</label>
          <select value={speakerId} onChange={(e) => setSpeakerId(e.target.value)}>
            <option value="">No speaker</option>
            {speakers.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </select>
        </div>
        <div className="inspector-field">
          <label>Type</label>
          <select value={eventType} onChange={(e) => setEventType(e.target.value)}>
            <option value="dialogue">Dialogue</option>
            <option value="sound_effect">Sound Effect</option>
            <option value="music">Music</option>
            <option value="speaker_overlap">Speaker Overlap</option>
            <option value="custom">Custom</option>
          </select>
        </div>
      </div>
      <div style={{ display: "flex", gap: "var(--spacing-sm)", marginTop: "var(--spacing-sm)" }}>
        <button type="submit">Add Event</button>
        <button type="button" onClick={onCancel}>
          Cancel
        </button>
      </div>
    </form>
  );
}

export function EventEditor({
  api,
  selectedEventId,
  onSelectEvent,
  onAction,
}: EventEditorProps) {
  const [events, setEvents] = useState<CaptionEvent[]>([]);
  const [speakers, setSpeakers] = useState<Speaker[]>([]);
  const [editingEvent, setEditingEvent] = useState<CaptionEvent | null>(null);
  const [showNewForm, setShowNewForm] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const loadEvents = async () => {
    if (!api) return;
    try {
      const result = await api.getEvents?.();
      if (result?.success) {
        setEvents(result.data ?? []);
      }
    } catch {
      // mock api may fail
    }
  };

  const loadSpeakers = async () => {
    if (!api) return;
    try {
      const result = await api.getSpeakers?.();
      if (result?.success) {
        setSpeakers(result.data ?? []);
      }
    } catch {
      // silent
    }
  };

  useEffect(() => {
    loadEvents();
    loadSpeakers();
  }, []);

  useEffect(() => {
    if (selectedEventId && selectedEventId !== "__new__") {
      const found = events.find((e) => e.id === selectedEventId);
      setEditingEvent(found ?? null);
    } else {
      setEditingEvent(null);
    }
  }, [selectedEventId, events]);

  const handleDeleteEvent = async (eventId: string) => {
    if (!api) return;
    try {
      const result = await api.removeEvent(eventId);
      if (result?.success) {
        setMessage("Event deleted");
        setEditingEvent(null);
        onSelectEvent(null);
        await loadEvents();
        onAction();
      }
      setTimeout(() => setMessage(null), 2000);
    } catch (err) {
      setMessage(`Error: ${err}`);
    }
  };

  const handleWordAdd = async (eventId: string) => {
    if (!api || !editingEvent) return;
    const words = editingEvent.words;
    const lastEnd = words.length > 0 ? words[words.length - 1].end : eventId ? events.find(e => e.id === eventId)?.end ?? 0 : 0;
    const wordStart = lastEnd;
    const wordEnd = wordStart + 0.3;
    try {
      const result = await api.addWord(eventId, "new", wordStart, wordEnd);
      if (result?.success) {
        setMessage("Word added");
        await loadEvents();
        onAction();
      }
      setTimeout(() => setMessage(null), 1500);
    } catch (err) {
      setMessage(`Error: ${err}`);
    }
  };

  const handleTimingChange = async (
    field: "start" | "end",
    value: number,
  ) => {
    if (!api || !selectedEventId || selectedEventId === "__new__") return;
    try {
      if (field === "start") {
        const current = editingEvent?.start ?? 0;
        const delta = value - current;
        await api.adjustEventTiming(selectedEventId, delta, 0);
      } else {
        const current = editingEvent?.end ?? 1;
        const delta = value - current;
        await api.adjustEventTiming(selectedEventId, 0, delta);
      }
      await loadEvents();
      onAction();
    } catch (err) {
      setMessage(`Error: ${err}`);
    }
  };

  const handleSpeakerChange = async (speakerId: string | null) => {
    if (!api || !selectedEventId || selectedEventId === "__new__") return;
    try {
      await api.updateEvent(selectedEventId, { speaker_id: speakerId });
      await loadEvents();
      onAction();
    } catch (err) {
      setMessage(`Error: ${err}`);
    }
  };

  const handleTypeChange = async (type: string) => {
    if (!api || !selectedEventId || selectedEventId === "__new__") return;
    try {
      await api.updateEvent(selectedEventId, { type });
      await loadEvents();
      onAction();
    } catch (err) {
      setMessage(`Error: ${err}`);
    }
  };

  const handleTextChange = async (text: string) => {
    if (!api || !selectedEventId || selectedEventId === "__new__") return;
    try {
      await api.updateEvent(selectedEventId, { text });
      // Update local state
      setEditingEvent((prev) => (prev ? { ...prev, text } : prev));
    } catch (err) {
      setMessage(`Error: ${err}`);
    }
  };

  const handleWordTextChange = async (
    wordIndex: number,
    text: string,
  ) => {
    if (!api || !selectedEventId) return;
    try {
      await api.updateWord(selectedEventId, wordIndex, { text });
      await loadEvents();
      onAction();
    } catch (err) {
      setMessage(`Error: ${err}`);
    }
  };

  const handleWordTimingChange = async (
    wordIndex: number,
    field: "start" | "end",
    value: number,
  ) => {
    if (!api || !selectedEventId) return;
    try {
      await api.adjustWordTiming(selectedEventId, wordIndex, field === "start" ? value - (editingEvent?.words?.[wordIndex]?.start ?? 0) : 0, field === "end" ? value - (editingEvent?.words?.[wordIndex]?.end ?? 0) : 0);
      await loadEvents();
      onAction();
    } catch (err) {
      setMessage(`Error: ${err}`);
    }
  };

  const selectedEvent = selectedEventId && selectedEventId !== "__new__"
    ? events.find((e) => e.id === selectedEventId) ?? null
    : null;

  return (
    <div>
      <h2>Event Editor</h2>

      {message && (
        <div className="success-message" style={{ fontSize: "0.85rem" }}>
          {message}
        </div>
      )}

      {/* Event list */}
      <div style={{ marginBottom: "var(--spacing-lg)" }}>
        <h3 style={{ marginBottom: "var(--spacing-sm)" }}>All Events</h3>
        {events.length === 0 ? (
          <div style={{ color: "var(--color-text-muted)" }}>
            No events yet. Create one below.
          </div>
        ) : (
          events.map((event) => (
            <EventItem
              key={event.id}
              event={event}
              isSelected={selectedEventId === event.id}
              onSelect={() => {
                onSelectEvent(event.id);
                setEditingEvent(event);
              }}
              onDelete={() => handleDeleteEvent(event.id)}
            />
          ))
        )}
      </div>

      {/* New event form */}
      {showNewForm && (
        <NewEventForm
          api={api}
          speakers={speakers}
          onCreated={(event) => {
            setEvents((prev) => [...prev, event]);
            setShowNewForm(false);
            onSelectEvent(event.id);
            setEditingEvent(event);
            onAction();
          }}
          onCancel={() => setShowNewForm(false)}
        />
      )}

      {!showNewForm && !selectedEvent && (
        <button onClick={() => setShowNewForm(true)}>+ Create New Event</button>
      )}

      {/* Selected event detail */}
      {selectedEvent && (
        <div className="panel" style={{ marginTop: "var(--spacing-lg)" }}>
          <h3>
            {selectedEvent.id}
            <span
              style={{
                marginLeft: "var(--spacing-sm)",
                fontSize: "0.8rem",
                fontWeight: 400,
                color: "var(--color-text-muted)",
              }}
            >
              {selectedEvent.type}
            </span>
          </h3>

          {/* Timing */}
          <div style={{ display: "flex", gap: "var(--spacing-lg)", flexWrap: "wrap", marginBottom: "var(--spacing-md)" }}>
            <div className="inspector-field">
              <label>Start</label>
              <input
                type="number"
                step="0.01"
                value={selectedEvent.start}
                onChange={(e) => handleTimingChange("start", parseFloat(e.target.value) || 0)}
                min={0}
              />
            </div>
            <div className="inspector-field">
              <label>End</label>
              <input
                type="number"
                step="0.01"
                value={selectedEvent.end}
                onChange={(e) => handleTimingChange("end", parseFloat(e.target.value) || 1)}
                min={selectedEvent.start + 0.01}
              />
            </div>
            <div className="inspector-field">
              <label>Speaker</label>
              <select
                value={selectedEvent.speaker_id ?? ""}
                onChange={(e) => handleSpeakerChange(e.target.value || null)}
              >
                <option value="">No speaker</option>
                {speakers.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name}
                  </option>
                ))}
              </select>
            </div>
            <div className="inspector-field">
              <label>Type</label>
              <select
                value={selectedEvent.type}
                onChange={(e) => handleTypeChange(e.target.value)}
              >
                <option value="dialogue">Dialogue</option>
                <option value="sound_effect">Sound Effect</option>
                <option value="music">Music</option>
                <option value="speaker_overlap">Speaker Overlap</option>
                <option value="custom">Custom</option>
              </select>
            </div>
          </div>

          {/* Text */}
          <div className="inspector-field" style={{ marginBottom: "var(--spacing-lg)" }}>
            <label>Text</label>
            <textarea
              value={selectedEvent.text}
              onChange={(e) => handleTextChange(e.target.value)}
              rows={2}
              style={{ fontFamily: "var(--font-sans)" }}
            />
          </div>

          {/* Words */}
          <div style={{ marginBottom: "var(--spacing-md)" }}>
            <h3 style={{ fontSize: "0.9rem", marginBottom: "var(--spacing-sm)" }}>
              Words ({selectedEvent.words.length})
            </h3>
            {selectedEvent.words.length === 0 ? (
              <div style={{ color: "var(--color-text-muted)", fontSize: "0.85rem" }}>
                No words yet. Add them manually or build from transcript.
              </div>
            ) : (
              selectedEvent.words.map((word, idx) => (
                <WordRow
                  key={`${word.text}-${idx}`}
                  word={word}
                  index={idx}
                  eventStart={selectedEvent.start}
                  eventEnd={selectedEvent.end}
                  onTextChange={(text) => handleWordTextChange(idx, text)}
                  onStartChange={(v) => handleWordTimingChange(idx, "start", v)}
                  onEndChange={(v) => handleWordTimingChange(idx, "end", v)}
                />
              ))
            )}
            <button
              onClick={() => handleWordAdd(selectedEvent.id)}
              style={{ marginTop: "var(--spacing-sm)" }}
            >
              + Add Word
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Word Row ──────────────────────────────────────

function WordRow({
  word,
  index,
  eventStart,
  eventEnd,
  onTextChange,
  onStartChange,
  onEndChange,
}: {
  word: Word;
  index: number;
  eventStart: number;
  eventEnd: number;
  onTextChange: (text: string) => void;
  onStartChange: (value: number) => void;
  onEndChange: (value: number) => void;
}) {
  return (
    <div
      className="event-card"
      style={{
        padding: "var(--spacing-sm)",
        marginBottom: "var(--spacing-xs)",
        display: "flex",
        alignItems: "center",
        gap: "var(--spacing-sm)",
        flexWrap: "wrap",
      }}
    >
      <span
        style={{
          fontSize: "0.7rem",
          color: "var(--color-text-muted)",
          fontFamily: "var(--font-mono)",
          width: "24px",
          textAlign: "center",
        }}
      >
        {index + 1}
      </span>
      <input
        value={word.text}
        onChange={(e) => onTextChange(e.target.value)}
        style={{
          width: "100px",
          fontSize: "0.85rem",
          fontWeight: word.weight >= 600 ? 600 : 400,
        }}
      />
      <div className="inspector-field" style={{ margin: 0 }}>
        <label style={{ width: "auto" }}>S</label>
        <input
          type="number"
          step="0.01"
          value={word.start}
          onChange={(e) => onStartChange(parseFloat(e.target.value) || 0)}
          min={eventStart}
          max={word.end}
          style={{ width: "80px" }}
        />
      </div>
      <div className="inspector-field" style={{ margin: 0 }}>
        <label style={{ width: "auto" }}>E</label>
        <input
          type="number"
          step="0.01"
          value={word.end}
          onChange={(e) => onEndChange(parseFloat(e.target.value) || 1)}
          min={word.start}
          max={eventEnd}
          style={{ width: "80px" }}
        />
      </div>
      <span style={{ fontSize: "0.7rem", color: "var(--color-text-muted)", fontFamily: "var(--font-mono)" }}>
        {word.size_pct}% / {word.weight}w
      </span>
    </div>
  );
}
