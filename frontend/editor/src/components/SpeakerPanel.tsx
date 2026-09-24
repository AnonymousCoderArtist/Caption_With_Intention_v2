import { useState } from "react";
import type { Speaker } from "@/types/project";
import { MAIN_COLORS, SUPPORT_COLORS } from "@/lib/theme";
import { Icon } from "@/lib/icons";

const CATEGORY_LABELS: Record<string, string> = {
  main: "Main",
  supporting: "Supporting",
  minor: "Minor",
};

interface SpeakerPanelProps {
  speakers: Speaker[];
  onAdd: (p: { name: string; category: string; color: string }) => void;
  onDelete: (id: string) => void;
  onColor: (id: string, color: string) => void;
  onCategory: (id: string, category: string) => void;
}

function SwatchStrip({
  value,
  onPick,
}: {
  value: string;
  onPick: (hex: string) => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const main = MAIN_COLORS.map((c) => c.hex);
  return (
    <div>
      <div className="palette-row" style={{ marginBottom: 8 }}>
        {main.map((hex) => (
          <button
            key={hex}
            className={`swatch ${value.toUpperCase() === hex ? "sel" : ""}`}
            style={{ color: hex, background: hex, width: 22, height: 22 }}
            onClick={() => onPick(hex)}
            title={hex}
            type="button"
          />
        ))}
        <button
          className="swatch"
          style={{
            width: 22,
            height: 22,
            background: "var(--bg-5)",
            color: "var(--text-300)",
            border: "1px solid var(--border-2)",
            display: "grid",
            placeItems: "center",
          }}
          onClick={() => setExpanded((v) => !v)}
          title="More colors"
          type="button"
        >
          <Icon name="plus" size={12} />
        </button>
      </div>
      {expanded && (
        <div className="palette-row animate-in">
          {SUPPORT_COLORS.map((hex) => (
            <button
              key={hex}
              className={`swatch ${value.toUpperCase() === hex ? "sel" : ""}`}
              style={{ color: hex, background: hex, width: 20, height: 20 }}
              onClick={() => onPick(hex)}
              title={hex}
              type="button"
            />
          ))}
        </div>
      )}
    </div>
  );
}

export function SpeakerPanel({
  speakers,
  onAdd,
  onDelete,
  onColor,
  onCategory,
}: SpeakerPanelProps) {
  const [showForm, setShowForm] = useState(false);
  const [name, setName] = useState("");
  const [category, setCategory] = useState("main");
  const [color, setColor] = useState("#E5E517");

  const handleAdd = () => {
    if (!name.trim()) return;
    onAdd({ name: name.trim(), category, color });
    setName("");
    setCategory("main");
    setColor("#E5E517");
    setShowForm(false);
  };

  return (
    <div>
      {/* header */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          marginBottom: "var(--sp-4)",
        }}
      >
        <span className="mono" style={{ fontSize: 10, color: "var(--text-500)", letterSpacing: "0.04em" }}>
          {speakers.length} {speakers.length === 1 ? "speaker" : "speakers"}
        </span>
        <button onClick={() => setShowForm((v) => !v)} style={{ padding: "6px 12px", fontSize: 11.5 }}>
          {showForm ? (
            <Icon name="close" size={13} />
          ) : (
            <Icon name="plus" size={13} strokeWidth={2.4} />
          )}
          {showForm ? "Cancel" : "Add"}
        </button>
      </div>

      {/* add form */}
      {showForm && (
        <div className="card animate-in" style={{ marginBottom: "var(--sp-4)" }}>
          <div className="field-row">
            <label className="field-label">Name</label>
            <div className="field-input">
              <input
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. Woody"
                autoFocus
                onKeyDown={(e) => e.key === "Enter" && handleAdd()}
              />
            </div>
          </div>
          <div className="field-row">
            <label className="field-label">Category</label>
            <div className="field-input">
              <select value={category} onChange={(e) => setCategory(e.target.value)}>
                <option value="main">Main</option>
                <option value="supporting">Supporting</option>
                <option value="minor">Minor</option>
              </select>
            </div>
          </div>
          <div style={{ marginBottom: 10 }}>
            <div className="label" style={{ marginBottom: 8 }}>
              Color
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <input
                type="color"
                value={color}
                onChange={(e) => setColor(e.target.value)}
                style={{ flexShrink: 0 }}
              />
              <span style={{ fontSize: 11, color: "var(--text-400)", fontFamily: "var(--font-mono)" }}>
                {color}
              </span>
            </div>
            <div style={{ marginTop: 10 }}>
              <SwatchStrip value={color} onPick={setColor} />
            </div>
          </div>
          <button className="primary" onClick={handleAdd} style={{ width: "100%" }}>
            <Icon name="check" size={14} />
            Add Speaker
          </button>
        </div>
      )}

      {/* list / empty */}
      {speakers.length === 0 ? (
        <div className="empty-state">
          <div className="empty-icon">
            <Icon name="users" size={24} />
          </div>
          <div className="empty-title">No speakers yet</div>
          <div className="empty-body">
            Each character in your scene gets a distinct caption color.
          </div>
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {speakers.map((s) => (
            <div
              key={s.id}
              className="card"
              style={{
                display: "flex",
                alignItems: "center",
                gap: 10,
                padding: "10px 12px",
              }}
            >
              <input
                type="color"
                value={s.color}
                onChange={(e) => onColor(s.id, e.target.value)}
                style={{
                  width: 26,
                  height: 26,
                  padding: 2,
                  borderRadius: "50%",
                  background: s.color,
                  border: "2px solid rgba(255,255,255,0.14)",
                  boxShadow: `0 0 10px ${s.color}44`,
                  flexShrink: 0,
                  cursor: "pointer",
                }}
                title={`Color ${s.color}`}
              />

              <div style={{ flex: 1, minWidth: 0 }}>
                <div
                  style={{
                    fontSize: 13,
                    fontWeight: 580,
                    color: "var(--text-100)",
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    whiteSpace: "nowrap",
                    display: "flex",
                    alignItems: "center",
                    gap: 6,
                  }}
                >
                  {s.name}
                  {s.off_camera && (
                    <span
                      style={{
                        fontSize: 9,
                        color: "var(--text-400)",
                        letterSpacing: "0.06em",
                        textTransform: "uppercase",
                        border: "1px solid var(--border-2)",
                        padding: "1px 5px",
                        borderRadius: 99,
                      }}
                    >
                      Off-cam
                    </span>
                  )}
                </div>
                <div style={{ marginTop: 3 }}>
                  <select
                    value={s.category}
                    onChange={(e) => onCategory(s.id, e.target.value)}
                    style={{
                      width: "auto",
                      fontSize: 10,
                      padding: "3px 22px 3px 8px",
                      background: "var(--bg-5)",
                      border: "1px solid var(--border)",
                      color: "var(--text-300)",
                      borderRadius: 99,
                      maxWidth: 130,
                    }}
                  >
                    <option value="main">{CATEGORY_LABELS.main}</option>
                    <option value="supporting">{CATEGORY_LABELS.supporting}</option>
                    <option value="minor">{CATEGORY_LABELS.minor}</option>
                  </select>
                </div>
              </div>

              <button
                className="icon-btn sm"
                style={{ opacity: 0, color: "var(--text-400)" }}
                title="Remove speaker"
                onClick={() => onDelete(s.id)}
                onMouseEnter={(e) => (e.currentTarget.style.opacity = "1")}
                onMouseLeave={(e) => (e.currentTarget.style.opacity = "0")}
              >
                <Icon name="trash" size={13} />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
