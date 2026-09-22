import { useState, useEffect } from "react";
import type { CaptionEvent } from "@/types/project";
import type { EditorApiClient } from "@/api/client";

interface InspectorPanelProps {
  api: EditorApiClient | any;
  eventId: string;
  onAction: () => void;
}

export function InspectorPanel({ api, eventId, onAction }: InspectorPanelProps) {
  const [event, setEvent] = useState<CaptionEvent | null>(null);
  const [loading, setLoading] = useState(true);

  const loadEvent = async () => {
    if (!api) {
      setLoading(false);
      return;
    }
    try {
      const result = await api.getEvents?.();
      if (result?.success) {
        const found = result.data?.find((e: CaptionEvent) => e.id === eventId);
        setEvent(found ?? null);
      }
    } catch {
      // silent
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadEvent();
  }, [eventId, onAction]);

  if (loading) {
    return <div className="loading">Loading inspector...</div>;
  }

  if (!event) {
    return (
      <div className="empty-state">
        <span className="empty-state-icon">&#9432;</span>
        <span>Event not found. Select a different event.</span>
      </div>
    );
  }

  const style = event.style;

  return (
    <div>
      <h2>Inspector</h2>
      <div
        style={{
          fontSize: "0.76rem",
          color: "var(--text-400)",
          marginBottom: "var(--sp-4)",
          fontFamily: "var(--font-mono)",
        }}
      >
        {event.id} — {event.type}
      </div>

      {/* Typography Section */}
      <div className="panel panel-section" style={{ animation: "fadeIn 0.2s ease" }}>
        <div style={{ borderBottom: "1px solid var(--border)", paddingBottom: "var(--sp-2)", marginBottom: "var(--sp-3)" }}>
          <h3 style={{ marginBottom: 0, fontSize: "0.8rem", textTransform: "uppercase", letterSpacing: "0.04em", color: "var(--text-200)" }}>Typography</h3>
        </div>

        <div className="inspector-field">
          <label>Size %</label>
          <input
            type="number"
            min="1"
            max="100"
            step="0.5"
            value={style.size_pct}
            onChange={(e) => updateStyle({ size_pct: parseFloat(e.target.value) || 5.0 })}
          />
        </div>

        <div className="inspector-field">
          <label>Weight</label>
          <select
            value={style.weight}
            onChange={(e) => updateStyle({ weight: parseInt(e.target.value) })}
          >
            <option value="100">100 — Thin</option>
            <option value="200">200 — Extra Light</option>
            <option value="300">300 — Light</option>
            <option value="400">400 — Regular</option>
            <option value="500">500 — Medium</option>
            <option value="600">600 — Semi Bold</option>
            <option value="700">700 — Bold</option>
            <option value="800">800 — Extra Bold</option>
            <option value="900">900 — Black</option>
          </select>
        </div>

        <div className="inspector-field">
          <label>Width</label>
          <input
            type="number"
            min="50"
            max="150"
            step="1"
            value={style.width}
            onChange={(e) => updateStyle({ width: parseInt(e.target.value) || 100 })}
          />
        </div>

        <div className="inspector-field">
          <label>Italic</label>
          <input
            type="checkbox"
            checked={style.italic}
            onChange={(e) => updateStyle({ italic: e.target.checked })}
          />
        </div>

        <div style={{ display: "flex", gap: "var(--sp-3)", flexWrap: "wrap" }}>
          <div className="inspector-field" style={{ margin: 0 }}>
            <label style={{ width: "auto", minWidth: "56px" }}>Size</label>
            <select
              value={style.size_mode}
              onChange={(e) => updateStyle({ size_mode: e.target.value as "auto" | "manual" })}
            >
              <option value="auto">Auto</option>
              <option value="manual">Manual</option>
            </select>
          </div>
          <div className="inspector-field" style={{ margin: 0 }}>
            <label style={{ width: "auto", minWidth: "60px" }}>Weight</label>
            <select
              value={style.weight_mode}
              onChange={(e) => updateStyle({ weight_mode: e.target.value as "auto" | "manual" })}
            >
              <option value="auto">Auto</option>
              <option value="manual">Manual</option>
            </select>
          </div>
          <div className="inspector-field" style={{ margin: 0 }}>
            <label style={{ width: "auto", minWidth: "58px" }}>Width</label>
            <select
              value={style.width_mode}
              onChange={(e) => updateStyle({ width_mode: e.target.value as "auto" | "manual" })}
            >
              <option value="auto">Auto</option>
              <option value="manual">Manual</option>
            </select>
          </div>
        </div>
      </div>

      {/* Animation Section */}
      <div className="panel panel-section" style={{ animation: "fadeIn 0.2s ease" }}>
        <div style={{ borderBottom: "1px solid var(--border)", paddingBottom: "var(--sp-2)", marginBottom: "var(--sp-3)" }}>
          <h3 style={{ marginBottom: 0, fontSize: "0.8rem", textTransform: "uppercase", letterSpacing: "0.04em", color: "var(--text-200)" }}>Animation</h3>
        </div>

        <div className="inspector-field">
          <label>Pop Scale</label>
          <input
            type="number"
            min="1.0"
            max="2.0"
            step="0.05"
            value={style.pop_scale}
            onChange={(e) => updateStyle({ pop_scale: parseFloat(e.target.value) || 1.15 })}
          />
        </div>

        <div className="inspector-field">
          <label>Pop Duration</label>
          <input
            type="number"
            min="0"
            max="2"
            step="0.05"
            value={style.pop_duration ?? 0}
            onChange={(e) => updateStyle({ pop_duration: parseFloat(e.target.value) || 0 })}
          />
        </div>

        <div className="inspector-field">
          <label>Easing</label>
          <select
            value={style.pop_easing}
            onChange={(e) => updateStyle({ pop_easing: e.target.value as any })}
          >
            <option value="smooth">Smooth</option>
            <option value="ease_in">Ease In</option>
            <option value="ease_out">Ease Out</option>
          </select>
        </div>

        <div className="inspector-field">
          <label>Syllable Mode</label>
          <input
            type="checkbox"
            checked={style.syllable_mode}
            onChange={(e) => updateStyle({ syllable_mode: e.target.checked })}
          />
        </div>

        <div className="inspector-field">
          <label>Color Transition Pt.</label>
          <input
            type="number"
            min="0"
            max="1"
            step="0.05"
            value={style.color_transition_point ?? 0}
            onChange={(e) => updateStyle({ color_transition_point: parseFloat(e.target.value) || 0 })}
          />
        </div>

        <div className="inspector-field">
          <label>Color Transition Dur.</label>
          <input
            type="number"
            min="0"
            max="2"
            step="0.05"
            value={style.color_transition_duration ?? 0}
            onChange={(e) => updateStyle({ color_transition_duration: parseFloat(e.target.value) || 0 })}
          />
        </div>

        <div className="inspector-field">
          <label>Read-Ahead Opacity</label>
          <input
            type="number"
            min="0"
            max="1"
            step="0.05"
            value={style.read_ahead_opacity}
            onChange={(e) => updateStyle({ read_ahead_opacity: parseFloat(e.target.value) || 0.9 })}
          />
        </div>
      </div>

      {/* Caption Box Section */}
      <div className="panel panel-section" style={{ animation: "fadeIn 0.2s ease" }}>
        <div style={{ borderBottom: "1px solid var(--border)", paddingBottom: "var(--sp-2)", marginBottom: "var(--sp-3)" }}>
          <h3 style={{ marginBottom: 0, fontSize: "0.8rem", textTransform: "uppercase", letterSpacing: "0.04em", color: "var(--text-200)" }}>Caption Box</h3>
        </div>

        <div className="inspector-field">
          <label>Opacity</label>
          <input
            type="number"
            min="0"
            max="1"
            step="0.05"
            value={style.box_opacity}
            onChange={(e) => updateStyle({ box_opacity: parseFloat(e.target.value) || 0.9 })}
          />
        </div>

        <div className="inspector-field">
          <label>Padding</label>
          <input
            type="number"
            min="0"
            max="50"
            step="1"
            value={style.box_padding}
            onChange={(e) => updateStyle({ box_padding: parseInt(e.target.value) || 10 })}
          />
        </div>

        <div className="inspector-field">
          <label>Break Out</label>
          <input
            type="checkbox"
            checked={style.breakout_permission}
            onChange={(e) => updateStyle({ breakout_permission: e.target.checked })}
          />
        </div>

        <div className="inspector-field">
          <label>Min Size %</label>
          <input
            type="number"
            min="1"
            max="20"
            step="0.5"
            value={style.minimum_pct}
            onChange={(e) => updateStyle({ minimum_pct: parseFloat(e.target.value) || 3.0 })}
          />
        </div>

        <div className="inspector-field">
          <label>Max Size %</label>
          <input
            type="number"
            min="5"
            max="50"
            step="0.5"
            value={style.maximum_pct}
            onChange={(e) => updateStyle({ maximum_pct: parseFloat(e.target.value) || 12.0 })}
          />
        </div>
      </div>

      <style>{`
        .inspector-field input[type="number"] {
          width: 80px;
          font-family: var(--font-mono);
          font-size: 0.8rem;
        }
        .inspector-field select {
          font-size: 0.78rem;
          max-width: 120px;
        }
      `}</style>
    </div>
  );

  async function updateStyle(updates: Record<string, any>) {
    if (!api || !event) return;
    try {
      const result = await api.setTypography(event.id, updates);
      if (result?.success) {
        setEvent(result.data);
        onAction();
      }
    } catch (err) {
      console.error("Failed to update style:", err);
    }
  }
}
