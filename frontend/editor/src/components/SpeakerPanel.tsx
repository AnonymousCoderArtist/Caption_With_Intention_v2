"""Speaker management panel — add, edit, remove, assign palette colors."""

import { useState } from "react";
import type { Speaker, SpeakerCategory } from "@/types/project";

interface SpeakerPanelProps {
  api: any;
  onAction: () => void;
}

const CATEGORY_COLORS: Record<SpeakerCategory | string, string> = {
  main: "var(--color-accent)",
  supporting: "var(--color-bg-tertiary)",
  minor: "var(--color-border)",
};

export function SpeakerPanel({ api, onAction }: SpeakerPanelProps) {
  const [speakers, setSpeakers] = useState<Speaker[]>([]);
  const [showAddForm, setShowAddForm] = useState(false);
  const [newName, setNewName] = useState("");
  const [newCategory, setNewCategory] = useState<string>("main");
  const [newColor, setNewColor] = useState<string>("#E5E517");
  const [message, setMessage] = useState<string | null>(null);

  const loadSpeakers = async () => {
    if (!api) return;
    try {
      const result = await api.getSpeakers?.();
      if (result?.success) {
        setSpeakers(result.data ?? []);
      }
    } catch (err) {
      setMessage(`Error loading speakers: ${err}`);
    }
  };

  const handleAddSpeaker = async () => {
    if (!newName.trim()) return;
    if (!api) return;
    try {
      const result = await api.addSpeaker({
        name: newName.trim(),
        category: newCategory,
        color: newColor,
      });
      if (result?.success) {
        setNewName("");
        setShowAddForm(false);
        setMessage(`Added speaker: ${newName.trim()}`);
        await loadSpeakers();
        onAction();
      } else {
        setMessage(`Error: ${result?.error}`);
      }
      setTimeout(() => setMessage(null), 2000);
    } catch (err) {
      setMessage(`Error adding speaker: ${err}`);
    }
  };

  const handleDeleteSpeaker = async (speakerId: string, name: string) => {
    if (!api) return;
    try {
      const result = await api.removeSpeaker(speakerId);
      if (result?.success) {
        setMessage(`Removed speaker: ${name}`);
        await loadSpeakers();
        onAction();
      } else {
        setMessage(`Error: ${result?.error}`);
      }
      setTimeout(() => setMessage(null), 2000);
    } catch (err) {
      setMessage(`Error removing speaker: ${err}`);
    }
  };

  return (
    <div>
      <h2>Speakers</h2>

      {message && (
        <div
          className="success-message"
          style={{ fontSize: "0.8rem" }}
        >
          {message}
        </div>
      )}

      <div style={{ marginBottom: "var(--spacing-md)" }}>
        {!showAddForm ? (
          <button onClick={() => setShowAddForm(true)}>+ Add Speaker</button>
        ) : (
          <div className="panel" style={{ padding: "var(--spacing-md)" }}>
            <div className="inspector-field">
              <label>Name</label>
              <input
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                placeholder="Speaker name"
                onKeyDown={(e) => {
                  if (e.key === "Enter") handleAddSpeaker();
                }}
              />
            </div>
            <div className="inspector-field">
              <label>Category</label>
              <select
                value={newCategory}
                onChange={(e) => setNewCategory(e.target.value)}
              >
                <option value="main">Main</option>
                <option value="supporting">Supporting</option>
                <option value="minor">Minor</option>
              </select>
            </div>
            <div className="inspector-field">
              <label>Color</label>
              <input
                type="color"
                value={newColor}
                onChange={(e) => setNewColor(e.target.value)}
                style={{ width: "40px", height: "30px", padding: 0 }}
              />
            </div>
            <div style={{ display: "flex", gap: "var(--spacing-sm)", marginTop: "var(--spacing-sm)" }}>
              <button onClick={handleAddSpeaker}>Save</button>
              <button onClick={() => setShowAddForm(false)}>Cancel</button>
            </div>
          </div>
        )}
      </div>

      {speakers.length === 0 ? (
        <div style={{ color: "var(--color-text-muted)" }}>
          No speakers yet. Add one to get started.
        </div>
      ) : (
        <div>
          {speakers.map((speaker) => (
            <div
              key={speaker.id}
              className="event-card"
              style={{ display: "flex", alignItems: "center", gap: "var(--spacing-md)" }}
            >
              <div
                style={{
                  width: "24px",
                  height: "24px",
                  borderRadius: "50%",
                  backgroundColor: speaker.color,
                  flexShrink: 0,
                  border: "2px solid var(--color-border)",
                }}
              />
              <div style={{ flex: 1, minWidth: 0 }}>
                <div
                  style={{
                    fontWeight: 600,
                    fontSize: "0.9rem",
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    whiteSpace: "nowrap",
                  }}
                >
                  {speaker.name}
                </div>
                <div style={{ fontSize: "0.75rem", color: "var(--color-text-muted)" }}>
                  {speaker.id}
                  {speaker.off_camera && " • Off-camera"}
                </div>
              </div>
              <span
                className={`badge badge-${speaker.category}`}
                style={{
                  backgroundColor: CATEGORY_COLORS[speaker.category],
                  color: speaker.category === "main" ? "var(--color-bg-primary)" : "inherit",
                }}
              >
                {speaker.category}
              </span>
              <button
                onClick={() => handleDeleteSpeaker(speaker.id, speaker.name)}
                style={{ color: "var(--color-danger)" }}
                title="Remove speaker"
              >
                ✕
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
