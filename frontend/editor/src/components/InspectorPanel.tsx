import { useId } from "react";
import {speakerReviewReasons} from "@/lib/speakerReview";
import { DraftNumber } from "./DraftNumber";
import {DraftColor} from "./DraftColor";
import { DraftText } from "./DraftText";
import type { CaptionEvent, Speaker, Word } from "@/types/project";
import { EVENT_TYPES } from "@/lib/theme";
import { Icon, type IconName } from "@/lib/icons";

interface InspectorPanelProps {
  event: CaptionEvent | null;
  onAudition?:()=>void;
  onNextSpeakerReview?:()=>void;
  hasMedia?:boolean;
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
      aria-label={label}
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
  const id = useId();
  return (
    <div className="inspector-field" role="group" aria-labelledby={id}>
      <label id={id}>{label}</label>
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
  max?: number;
  step: number;
  unit?: string;
  onChange: (v: number) => void;
}) {
  return (
    <div className="with-unit">
      <DraftNumber
        value={value}
        min={min}
        max={max}
        step={step}
        onCommit={onChange}
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
  onAudition,
  onNextSpeakerReview,
  hasMedia,
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
    <div key={event.id} style={{ display: "flex", flexDirection: "column", minHeight: 0 }}>
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
          <span className="ev-kind">
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
          <DraftText key={event.id} multiline
            rows={2}
            value={event.text}
            onCommit={text => onUpdateEvent(event.id, { text })}
            style={{ minHeight: 44 }}
          />
          <span className="field-note">Word-count changes redistribute word timing across this caption. Undo restores the original.</span>
        </div>

        {/* timing */}
        <div className="paired-fields" style={{ display: "flex", gap: 10, marginBottom: 12 }}>
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
                step={0.01}
                unit="s"
                onChange={(v) => onUpdateEvent(event.id, { end: v })}
              />
            </Field>
          </div>
        </div>

        {['dialogue','speaker_overlap'].includes(event.type)&&<div className="speaker-review-box">
          <b>{event.speaker_reviewed?'Speaker checked':'Speaker attribution'}</b>
          {speakerReviewReasons(event,speakers).map(reason=><p key={reason}>{reason}</p>)}
          {event.speaker_coverage!=null&&<p>Diarization coverage: {Math.round(event.speaker_coverage*100)}%. This is timing coverage, not identity certainty.</p>}
          <p>Listen to this turn, choose the speaker below, then mark it checked. Text confidence is separate.</p>
          <button className="ghost" disabled={!hasMedia} onClick={onAudition}>Listen to turn</button>
          <button className="ghost" onClick={onNextSpeakerReview}>Next unchecked turn</button>
          <button className="ghost" onClick={()=>onUpdateEvent(event.id,{speaker_reviewed:!event.speaker_reviewed,manual_override:true})}>{event.speaker_reviewed?'Reopen speaker review':'Mark speaker checked'}</button>
        </div>}
        {/* speaker + type */}
        <div className="paired-fields" style={{ display: "flex", gap: 10, marginBottom: 12 }}>
          <div style={{ flex: 1 }}>
            <Field label="Speaker">
              <select
                value={event.speaker_id ?? ""}
                onChange={(e) => onUpdateEvent(event.id, { speaker_id: e.target.value || null,speaker_reviewed:false,manual_override:true })}
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
                <div key={idx}>
                <div className="word-row">
                  <span className="w-idx">{idx + 1}</span>
                  <DraftText key={`${event.id}-${idx}`}
                    aria-label={`Word ${idx + 1} text`}
                    className="w-text"
                    value={w2.text}
                    onCommit={text => onUpdateWord(event.id, idx, { text })}
                    style={{ fontSize: 12.5 }}
                  />
                  <DraftNumber
                    step={0.01}
                    value={Math.round(w2.start * 100) / 100}
                    onCommit={v => onUpdateWord(event.id, idx, { start: v })}
                    style={{ width: 56, padding: "5px 6px", fontSize: 11 }}
                    title="word start (s)"
                  />
                  <DraftNumber
                    step={0.01}
                    value={Math.round(w2.end * 100) / 100}
                    onCommit={v => onUpdateWord(event.id, idx, { end: v })}
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
                <details className="word-properties"><summary>Word {idx + 1} properties</summary>
                  <div className="word-property-grid">
                    {([['Size %','size_pct',1,50,.5],['Weight','weight',100,1000,10],['Width %','width',25,151,1],['Opacity','opacity',0,1,.05],['Pitch Hz','pitch_hz',0,2000,1]] as const).map(([label,key,min,max,step]) => <label key={key}>{label}<DraftNumber aria-label={`Word ${idx+1} ${label}`} value={Math.round((w2[key] ?? 0)*100)/100} min={min} max={max} step={step} onCommit={value => onUpdateWord(event.id,idx,{[key]:value})}/></label>)}
                    <label>Italic<input type="checkbox" checked={w2.italic} onChange={e => onUpdateWord(event.id,idx,{italic:e.target.checked})}/></label>
                    <label>Manual override<input type="checkbox" checked={w2.manual_override} onChange={e => onUpdateWord(event.id,idx,{manual_override:e.target.checked})}/></label>
                  </div>
                  {['dialogue','speaker_overlap','custom'].includes(event.type)&&<div className="character-colors"><p className="field-note">Character color overrides the speaker color only when spoken. Reset returns to speaker color. Editing this word's text clears its character overrides.</p>{Array.from(w2.text).filter(c=>! /\s/.test(c)).map((char,ci)=><label key={ci} title={`Character ${ci+1}: ${char}`}><span>{char===' '?'␣':char}</span><DraftColor aria-label={`Word ${idx+1} character ${ci+1} color`} value={w2.character_colors?.[ci]??w2.color} onCommit={color=>{const colors=[...(w2.character_colors??Array(Array.from(w2.text).filter(c=>! /\s/.test(c)).length).fill(null))];colors[ci]=color;onUpdateWord(event.id,idx,{character_colors:colors});}}/></label>)}<button className="subtle" onClick={()=>onUpdateWord(event.id,idx,{character_colors:null})}>Reset character colors</button></div>}
                  <label className="json-field">Syllables (JSON)<textarea aria-label={`Word ${idx+1} syllables JSON`} key={JSON.stringify(w2.syllables)} defaultValue={JSON.stringify(w2.syllables,null,2)} onBlur={e => {try {const value=JSON.parse(e.target.value);if(value!==null&&(!Array.isArray(value)||value.some((s:any)=>typeof s.text!=='string'||!Number.isFinite(s.start)||!Number.isFinite(s.end)||s.start<w2.start||s.end>w2.end||s.end<=s.start)))throw new Error();onUpdateWord(event.id,idx,{syllables:value});e.target.setCustomValidity('');}catch{e.target.setCustomValidity('Use null or an array of text/start/end syllables inside this word.');e.target.reportValidity();}}}/></label>
                  <label className="json-field">Letter pitches (JSON)<textarea aria-label={`Word ${idx+1} letter pitches JSON`} key={JSON.stringify(w2.letter_pitches)} defaultValue={JSON.stringify(w2.letter_pitches??null)} onBlur={e => {try{const value=JSON.parse(e.target.value);if(value!==null&&(!Array.isArray(value)||value.some((v:any)=>v!==null&&(!Number.isFinite(v)||v<0))))throw new Error();onUpdateWord(event.id,idx,{letter_pitches:value});e.target.setCustomValidity('');}catch{e.target.setCustomValidity('Use null or an array of non-negative pitches/nulls.');e.target.reportValidity();}}}/></label>
                </details>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* typography */}
        <Section icon="sliders" title="Typography">
          <Field label="Size">
            <Num value={st.size_pct} min={1} max={20} step={0.5} unit="%" onChange={(v) => onUpdateStyle(event.id, { size_pct: v, size_mode:"manual" })} />
          </Field>
          <Field label="Weight">
            <select value={st.weight} onChange={(e) => onUpdateStyle(event.id, { weight: parseInt(e.target.value), weight_mode:"manual" })}>
              {[100, 200, 300, 400, 500, 600, 700, 800, 900].map((w3) => (
                <option key={w3} value={w3}>{w3}</option>
              ))}
            </select>
          </Field>
          <Field label="Width">
            <Num value={st.width} min={75} max={125} step={1} unit="%" onChange={(v) => onUpdateStyle(event.id, { width: v, width_mode:"manual" })} />
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
          <Field label="Letter lift">
            <Slider value={st.pop_scale} min={1} max={1.6} step={0.05} onChange={(v) => onUpdateStyle(event.id, { pop_scale: v })} fmt={(v) => `${Math.round(v * 100)}%`} />
          </Field>
          <p className="field-note">Stable preview and final render use a fixed 60 ms rise and bounded settle. Legacy duration/easing and syllable mode remain saved but do not override the continuous letter wave.</p>
          <Field label="Legacy duration">
            <Num value={st.pop_duration ?? 0} min={0} max={2} step={0.05} unit="s" onChange={(v) => onUpdateStyle(event.id, { pop_duration: v })} />
          </Field>
          <Field label="Legacy easing">
            <select value={st.pop_easing} onChange={(e) => onUpdateStyle(event.id, { pop_easing: e.target.value })}>
              <option value="smooth">Smooth</option>
              <option value="ease_in">Ease in</option>
              <option value="ease_out">Ease out</option>
            </select>
          </Field>
          <div className="inspector-field">
            <label>Legacy syllable mode</label>
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
            <label>Legacy breakout flag</label>
            <Toggle on={st.breakout_permission} onClick={() => onUpdateStyle(event.id, { breakout_permission: !st.breakout_permission })} label="Breakout" />
          </div>
          <p className="field-note">Stable renderer applies automatic loud-burst breakout. This legacy flag and minimum size remain saved but do not override that path. Maximum size caps held-emphasis growth, not every manual word size.</p>
          <div style={{ display: "grid", gridTemplateColumns:"1fr", gap: 10 }}>
            <div style={{ flex: 1 }}>
              <Field label="Legacy min size">
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

        <Section icon="sliders" title="Held emphasis">
          <Field label="Growth / s"><Num value={st.escalation_rate ?? .8} min={0} max={5} step={.1} onChange={v=>onUpdateStyle(event.id,{escalation_rate:v})}/></Field>
          <Field label="Growth cap"><Num value={st.escalation_max ?? 1.8} min={1} max={5} step={.1} onChange={v=>onUpdateStyle(event.id,{escalation_max:v})}/></Field>
          <Field label="Loudness gate"><Num value={st.escalation_gate ?? 1.3} min={1} max={5} step={.1} onChange={v=>onUpdateStyle(event.id,{escalation_gate:v})}/></Field>
        </Section>
        <Section icon="list" title="Review">
          <Field label="Status"><select aria-label="Review status" value={event.review_state} onChange={e=>onUpdateEvent(event.id,{review_state:e.target.value as any})}>{['pending','accepted','rejected','corrected'].map(v=><option key={v}>{v}</option>)}</select></Field>
          <label className="json-field">Notes<DraftText multiline aria-label="Caption notes" value={event.notes} onCommit={notes=>onUpdateEvent(event.id,{notes})}/></label>
        </Section>
        <div style={{ height: 12 }} />
      </div>
    </div>
  );
}
