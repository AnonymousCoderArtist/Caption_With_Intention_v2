import type { CaptionEvent, Speaker, Word } from "@/types/project";
import { EVENT_TYPES } from "@/lib/theme";
import { Icon, type IconName } from "@/lib/icons";

interface InspectorPanelProps {
  event: CaptionEvent | null;
  speakers: Speaker[];
  onUpdateEvent: (id: string, updates: Partial<CaptionEvent>) => void;
  onUpdateStyle: (id: string, updates: Record<string, any>) => void;
  onAddWord: (id: string) => void;
  onUpdateWord: (id: string, idx: number, updates: Partial<Word>) => void;
  onRemoveWord: (id: string, idx: number) => void;
}

function Toggle({
  on,
  onClick,
  label,
}: {
  on: boolean;
  onClick: () => void;
  label?: string;
}) {
  return (
    <button
      className={`toggle ${on ? "on" : ""}`}
      onClick={onClick}
      role="switch"
      aria-checked={on}
      title={label}
    />
  );
}

function Section({
  icon,
  title,
  children,
}: {
  icon: IconName;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="panel panel-section">
      <div className="panel-section-head">
        <h3>
          <Icon name={icon} size={14} />
          {title}
        </h3>
      </div>
      <div className="panel-section-body">{children}</div>
    </div>
  );
}

function Field({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="inspector-field">
      <label>{label}</label>
      {children}
    </div>
  );
}

function Num({
  value,
  min,
  max,
  step,
  unit,
  onChange,
}: {
  value: number;
  min: number;
  max: number;
  step: number;
  unit?: string;
  onChange: (v: number) => void;
}) {
  return (
    <div className="with-unit">
      <input
        type="number"
        value={value}
        min={min}
        max={max}
        step={step}
        onChange={(e) => onChange(parseFloat(e.target.value) || 0)}
      />
      {unit && <span className="unit">{unit}</span>}
    </div>
  );
}

function Slider({
  value,
  min,
  max,
  step,
  onChange,
  fmt,
}: {
  value: number;
  min: number;
  max: number;
  step: number;
  onChange: (v: number) => void;
  fmt?: (v: number) => string;
}) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
      <input
        type="range"
        value={value}
        min={min}
        max={max}
        step={step}
        onChange={(e) => onChange(parseFloat(e.target.value))}
      />
      <span
        className="mono"
        style={{ fontSize: 11, color: "var(--text-300)", width: 42, textAlign: "right" }}
      >
        {fmt ? fmt(value) : value}
      </span>
    </div>
  );
}

export function InspectorPanel({
  event,
  speakers,
  onUpdateEvent,
  onUpdateStyle,
  onAddWord,
  onUpdateWord,
  onRemoveWord,
}: InspectorPanelProps) {
  if (!event) {
    return (
      <div className="scroll" style={{ display: "flex", alignItems: "center" }}>
        <div className="empty-state" style={{ padding: 24 }}>
          <div className="empty-icon">
            <Icon name="sliders" size={24} />
          </div>
          <div className="empty-title">No event selected</div>
          <div className="empty-body">
            Select a caption event to inspect &amp; edit its text, timing,
            typography, animation and box.
          </div>
        </div>
      </div>
    );
  }

  const st = event.style;
  const type = EVENT_TYPES[event.type] ?? EVENT_TYPES.custom;

  return (
    <div style={{ display: "flex", flexDirection: "column", minHeight: 0 }}>
      {/* header */}
      <div
        style={{
          padding: "14px 16px 12px",
          borderBottom: "1px solid var(--border)",
          background: "linear-gradient(180deg, var(--bg-4), var(--bg-3))",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <h2 style={{ marginBottom: 0, marginRight: "auto" }}>Inspector</h2>
          <span className="badge" style={{ background: `${type.color}1f`, color: type.color }}>
            {type.label}
          </span>
        </div>
        <div
          style={{
            marginTop: 8,
            fontFamily: "var(--font-mono)",
            fontSize: 11,
            color: "var(--text-400)",
            display: "flex",
            alignItems: "center",
            gap: 8,
          }}
        >
          <span style={{ color: "var(--accent-text)" }}>{event.id}</span>
          {event.confidence != null && (
            <span>
              · conf {Math.round(event.confidence * 100)}%
            </span>
          )}
        </div>
      </div>

      {/* body */}
      <div className="scroll" style={{ padding: 16 }}>
        {/* text */}
        <div className="inspector-field" style={{ flexDirection: "column", alignItems: "stretch", gap: 6, marginBottom: 12 }}>
          <label style={{ width: "auto" }}>Text</label>
          <textarea
            rows={2}
            value={event.text}
            onChange={(e) => onUpdateEvent(event.id, { text: e.target.value })}
            style={{ minHeight: 44 }}
          />
        </div>

        {/* timing */}
        <div style={{ display: "flex", gap: 10, marginBottom: 12 }}>
          <div style={{ flex: 1 }}>
            <Field label="Start">
              <Num
                value={Math.round(event.start * 100) / 100}
                min={0}
                max={event.end}
                step={0.01}
                unit="s"
                onChange={(v) => onUpdateEvent(event.id, { start: v })}
              />
            </Field>
          </div>
          <div style={{ flex: 1 }}>
            <Field label="End">
              <Num
                value={Math.round(event.end * 100) / 100}
                min={event.start + 0.1}
                max={600}
                step={0.01}
                unit="s"
                onChange={(v) => onUpdateEvent(event.id, { end: v })}
              />
            </Field>
          </div>
        </div>

        {/* speaker + type */}
        <div style={{ display: "flex", gap: 10, marginBottom: 12 }}>
          <div style={{ flex: 1 }}>
            <Field label="Speaker">
              <select
                value={event.speaker_id ?? ""}
                onChange={(e) => onUpdateEvent(event.id, { speaker_id: e.target.value || null })}
              >
                <option value="">— none —</option>
                {speakers.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name}
                  </option>
                ))}
              </select>
            </Field>
          </div>
          <div style={{ flex: 1 }}>
            <Field label="Type">
              <select
                value={event.type}
                onChange={(e) => onUpdateEvent(event.id, { type: e.target.value as CaptionEvent["type"] })}
              >
                <option value="dialogue">Dialogue</option>
                <option value="sound_effect">Sound FX</option>
                <option value="music">Music</option>
                <option value="speaker_overlap">Overlap</option>
                <option value="custom">Custom</option>
              </select>
            </Field>
          </div>
        </div>

        {/* off-camera */}
        <div className="inspector-field" style={{ marginBottom: 16 }}>
          <label>Off-camera (italic)</label>
          <Toggle
            on={event.off_camera}
            onClick={() => onUpdateEvent(event.id, { off_camera: !event.off_camera })}
            label="Off-camera"
          />
        </div>

        {/* words */}
        <div style={{ marginBottom: 16 }}>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              marginBottom: 8,
            }}
          >
            <div className="label" style={{ fontSize: 11, letterSpacing: "0.08em" }}>
              WORDS ({event.words.length})
            </div>
            <button
              className="subtle"
              onClick={() => onAddWord(event.id)}
              style={{ fontSize: 11, padding: "4px 8px" }}
            >
              <Icon name="plus" size={12} strokeWidth={2.4} />
              Add word
            </button>
          </div>

          {event.words.length === 0 ? (
            <div style={{ fontSize: 11.5, color: "var(--text-400)", padding: "10px 12px", background: "var(--bg-3)", borderRadius: 8 }}>
              No words yet. Add them or build from transcript.
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              {event.words.map((w2, idx) => (
                <div key={idx} className="word-row">
                  <span className="w-idx">{idx + 1}</span>
                  <input
                    className="w-text"
                    value={w2.text}
                    onChange={(e) => onUpdateWord(event.id, idx, { text: e.target.value })}
                    style={{ fontSize: 12.5 }}
                  />
                  <input
                    type="number"
                    step={0.01}
                    value={Math.round(w2.start * 100) / 100}
                    onChange={(e) => onUpdateWord(event.id, idx, { start: parseFloat(e.target.value) || 0 })}
                    style={{ width: 56, padding: "5px 6px", fontSize: 11 }}
                    title="word start (s)"
                  />
                  <input
                    type="number"
                    step={0.01}
                    value={Math.round(w2.end * 100) / 100}
                    onChange={(e) => onUpdateWord(event.id, idx, { end: parseFloat(e.target.value) || 0 })}
                    style={{ width: 56, padding: "5px 6px", fontSize: 11 }}
                    title="word end (s)"
                  />
                  <button
                    className="w-del"
                    onClick={() => onRemoveWord(event.id, idx)}
                    title="Delete word"
                  >
                    <Icon name="close" size={13} />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* typography */}
        <Section icon="sliders" title="Typography">
          <Field label="Size">
            <Num value={st.size_pct} min={1} max={20} step={0.5} unit="%" onChange={(v) => onUpdateStyle(event.id, { size_pct: v })} />
          </Field>
          <Field label="Weight">
            <select value={st.weight} onChange={(e) => onUpdateStyle(event.id, { weight: parseInt(e.target.value) })}>
              {[100, 200, 300, 400, 500, 600, 700, 800, 900].map((w3) => (
                <option key={w3} value={w3}>{w3}</option>
              ))}
            </select>
          </Field>
          <Field label="Width">
            <Num value={st.width} min={75} max={125} step={1} unit="%" onChange={(v) => onUpdateStyle(event.id, { width: v })} />
          </Field>
          <div className="inspector-field">
            <label>Italic</label>
            <Toggle on={st.italic} onClick={() => onUpdateStyle(event.id, { italic: !st.italic })} label="Italic" />
          </div>
          <div style={{ height: 8 }} />
          <div style={{ display: "flex", gap: 8 }}>
            {([
              ["Size", "size_mode", st.size_mode],
              ["Weight", "weight_mode", st.weight_mode],
              ["Width", "width_mode", st.width_mode],
            ] as const).map(([lab, key, val]) => (
              <div key={key} style={{ flex: 1 }}>
                <div className="label" style={{ marginBottom: 5, fontSize: 9.5, letterSpacing: "0.08em" }}>
                  {lab}
                </div>
                <select
                  value={val}
                  onChange={(e) => onUpdateStyle(event.id, { [key]: e.target.value })}
                  style={{ width: "100%", padding: "5px 24px 5px 8px", fontSize: 11 }}
                >
                  <option value="auto">Auto</option>
                  <option value="manual">Manual</option>
                </select>
              </div>
            ))}
          </div>
        </Section>

        {/* animation */}
        <Section icon="sparkle" title="Animation">
          <Field label="Pop scale">
            <Slider value={st.pop_scale} min={1} max={1.6} step={0.05} onChange={(v) => onUpdateStyle(event.id, { pop_scale: v })} fmt={(v) => `${Math.round(v * 100)}%`} />
          </Field>
          <Field label="Pop duration">
            <Num value={st.pop_duration ?? 0} min={0} max={2} step={0.05} unit="s" onChange={(v) => onUpdateStyle(event.id, { pop_duration: v })} />
          </Field>
          <Field label="Easing">
            <select value={st.pop_easing} onChange={(e) => onUpdateStyle(event.id, { pop_easing: e.target.value })}>
              <option value="smooth">Smooth</option>
              <option value="ease_in">Ease in</option>
              <option value="ease_out">Ease out</option>
            </select>
          </Field>
          <div className="inspector-field">
            <label>Syllable mode</label>
            <Toggle on={st.syllable_mode} onClick={() => onUpdateStyle(event.id, { syllable_mode: !st.syllable_mode })} label="Syllable mode" />
          </div>
          <Field label="Read-ahead opacity">
            <Slider value={st.read_ahead_opacity} min={0} max={1} step={0.05} onChange={(v) => onUpdateStyle(event.id, { read_ahead_opacity: v })} fmt={(v) => `${Math.round(v * 100)}%`} />
          </Field>
        </Section>

        {/* caption box */}
        <Section icon="film" title="Caption Box">
          <Field label="Opacity">
            <Slider value={st.box_opacity} min={0} max={1} step={0.05} onChange={(v) => onUpdateStyle(event.id, { box_opacity: v })} fmt={(v) => `${Math.round(v * 100)}%`} />
          </Field>
          <Field label="Padding">
            <Num value={st.box_padding} min={0} max={50} step={1} unit="px" onChange={(v) => onUpdateStyle(event.id, { box_padding: v })} />
          </Field>
          <div className="inspector-field">
            <label>Breakout allowed</label>
            <Toggle on={st.breakout_permission} onClick={() => onUpdateStyle(event.id, { breakout_permission: !st.breakout_permission })} label="Breakout" />
          </div>
          <div style={{ display: "flex", gap: 10 }}>
            <div style={{ flex: 1 }}>
              <Field label="Min size">
                <Num value={st.minimum_pct} min={1} max={20} step={0.5} unit="%" onChange={(v) => onUpdateStyle(event.id, { minimum_pct: v })} />
              </Field>
            </div>
            <div style={{ flex: 1 }}>
              <Field label="Max size">
                <Num value={st.maximum_pct} min={3} max={50} step={0.5} unit="%" onChange={(v) => onUpdateStyle(event.id, { maximum_pct: v })} />
              </Field>
            </div>
          </div>
        </Section>

        <div style={{ height: 12 }} />
      </div>
    </div>
  );
}
