import { useState, useEffect } from "react";
import type { Speaker, SpeakerCategory } from "@/types/project";
import type { EditorApiClient } from "@/api/client";

interface SpeakerPanelProps {
  api: EditorApiClient | any;
  onAction: () => void;
}

const CATEGORY_LABELS: Record<string, string> = {
  main: "Main",
  supporting: "Supporting",
  minor: "Minor",
};

export function SpeakerPanel({ api, onAction }: SpeakerPanelProps) {
  const [speakers, setSpeakers] = useState<Speaker[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [name, setName] = useState("");
  const [category, setCategory] = useState<string>("main");
  const [color, setColor] = useState<string>("#E5E517");
  const [msg, setMsg] = useState<string | null>(null);

  const load = async () => {
    const r = await api.getSpeakers?.();
    if (r?.success) setSpeakers(r.data ?? []);
  };

  useEffect(() => { load(); }, [onAction]);

  const add = async () => {
    if (!name.trim()) return;
    const r = await api.addSpeaker({ name: name.trim(), category, color });
    if (r?.success) {
      setMsg(`Added "${name.trim()}"`);
      setName("");
      setShowForm(false);
      await load();
      onAction();
    } else {
      setMsg(`Error: ${r.error}`);
    }
    setTimeout(() => setMsg(null), 2200);
  };

  const remove = async (id: string, n: string) => {
    const r = await api.removeSpeaker(id);
    if (r?.success) {
      setMsg(`Removed "${n}"`);
      await load();
      onAction();
    }
    setTimeout(() => setMsg(null), 2200);
  };

  return (
    <div>
      <h2>Speakers</h2>

      {msg && <div className="success-message" style={{ fontSize: "0.8rem" }}>{msg}</div>}

      <div style={{ marginBottom: "var(--sp-4)" }}>
        {!showForm ? (
          <button onClick={() => setShowForm(true)}>+ Add Speaker</button>
        ) : (
          <div className="panel" style={{ padding: "var(--sp-4)" }}>
            <div className="inspector-field">
              <label>Name</label>
              <input
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Speaker name"
                autoFocus
                onKeyDown={(e) => e.key === "Enter" && add()}
              />
            </div>
            <div className="inspector-field">
              <label>Category</label>
              <select value={category} onChange={(e) => setCategory(e.target.value)}>
                <option value="main">Main</option>
                <option value="supporting">Supporting</option>
                <option value="minor">Minor</option>
              </select>
            </div>
            <div className="inspector-field">
              <label>Color</label>
              <input
                type="color"
                value={color}
                onChange={(e) => setColor(e.target.value)}
                style={{ width: "44px", height: "32px", padding: 0, maxWidth: "unset" }}
              />
            </div>
            <div style={{ display: "flex", gap: "var(--sp-2)", marginTop: "var(--sp-2)" }}>
              <button onClick={add}>Save</button>
              <button className="ghost" onClick={() => setShowForm(false)}>Cancel</button>
            </div>
          </div>
        )}
      </div>

      {speakers.length === 0 ? (
        <div style={{ color: "var(--text-400)", padding: "var(--sp-5) 0", textAlign: "center" }}>
          No speakers yet. Add one to begin.
        </div>
      ) : (
        <div>
          {speakers.map((s) => (
            <div
              key={s.id}
              className="event-card"
              style={{ display: "flex", alignItems: "center", gap: "var(--sp-3)" }}
            >
              <div
                className="color-swatch"
                style={{ backgroundColor: s.color }}
                title={s.name}
              />
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontWeight: 600, fontSize: "0.88rem", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                  {s.name}
                </div>
                <div style={{ fontSize: "0.72rem", color: "var(--text-400)", fontFamily: "var(--font-mono)" }}>
                  {s.id}
                  {s.off_camera && " · off-camera"}
                </div>
              </div>
              <span className={`badge badge-${s.category}`}>
                {CATEGORY_LABELS[s.category] ?? s.category}
              </span>
              <button className="ghost" onClick={() => remove(s.id, s.name)} title="Remove" style={{ padding: "var(--sp-1) var(--sp-2)" }}>✕</button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
