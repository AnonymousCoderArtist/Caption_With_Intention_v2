/** Demo project + in-memory Editor API client.
 *
 * Gives the editor a fully interactive, word-timed scene out of the box —
 * so the UI (timeline, preview monitor, inspector) is alive even when the
 * Python backend is not running. Data mirrors the CaptionEvent/Speaker/Style
 * shapes from @/types/project.
 */
import type {
  ApiResponse,
  CaptionEvent,
  Project,
  Speaker,
  Style,
  Word,
} from "@/types/project";
import { SpeakerCategory, EventType, ReviewState } from "@/types/project";

/* ── word builder ──────────────────────────────────────────── */
let wseq = 0;
function w(
  text: string,
  start: number,
  end: number,
  color: string,
  o: Partial<Word> = {},
): Word {
  wseq++;
  return {
    text,
    start,
    end,
    size_pct: o.size_pct ?? 5,
    weight: o.weight ?? 400,
    width: o.width ?? 100,
    color,
    opacity: 1,
    italic: o.italic ?? false,
    confidence: o.confidence ?? null,
    source_model: o.source_model ?? null,
    source_timestamp: o.source_timestamp ?? null,
    manual_override: o.manual_override ?? false,
    review_state: o.review_state ?? ReviewState.Accepted,
    syllables: o.syllables ?? null,
  };
}

function style(o: Partial<Style> = {}): Style {
  return {
    read_ahead_opacity: 0.9,
    pop_scale: 1.15,
    size_pct: 5,
    weight: 400,
    width: 100,
    italic: false,
    size_mode: "auto",
    weight_mode: "auto",
    width_mode: "auto",
    color_transition_point: null,
    color_transition_duration: null,
    pop_duration: 0.26,
    pop_easing: "smooth",
    syllable_mode: false,
    box_opacity: 0.9,
    box_padding: 10,
    breakout_permission: false,
    minimum_pct: 3,
    maximum_pct: 12,
    ...o,
  };
}

/* ── palette ───────────────────────────────────────────────── */
const WOODY = "#E5E517"; // main yellow
const BUZZ = "#17E5E5"; // main cyan
const PFH = "#E51717"; // main red
const REX = "#E85C2E"; // supporting
const NARR = "#D8DBE6"; // minor pastel

/* ── demo speakers ─────────────────────────────────────────── */
function spk(
  id: string,
  name: string,
  category: SpeakerCategory,
  color: string,
  o: Partial<Speaker> = {},
): Speaker {
  return {
    id,
    name,
    category,
    role: o.role ?? null,
    color,
    confidence: o.confidence ?? 0.98,
    source_model: null,
    source_timestamp: null,
    manual_override: false,
    review_state: ReviewState.Accepted,
    off_camera: o.off_camera ?? false,
    active_speaker: o.active_speaker ?? false,
    notes: o.notes ?? "",
  };
}

function ev(
  id: string,
  type: EventType,
  start: number,
  end: number,
  speaker_id: string | null,
  text: string,
  words: Word[],
  o: Partial<CaptionEvent> = {},
): CaptionEvent {
  return {
    id,
    type,
    start,
    end,
    speaker_id,
    off_camera: o.off_camera ?? false,
    text,
    style: o.style ?? style(),
    words,
    confidence: o.confidence ?? 0.99,
    source_model: null,
    source_timestamp: null,
    manual_override: false,
    review_state: ReviewState.Accepted,
    exception_profile: null,
    notes: "",
  };
}

export function createDemoProject(): Project {
  wseq = 0;
  const speakers: Speaker[] = [
    spk("spk_woody", "Woody", SpeakerCategory.Main, WOODY, { active_speaker: true, role: "hero" }),
    spk("spk_buzz", "Buzz Lightyear", SpeakerCategory.Main, BUZZ, { role: "hero" }),
    spk("spk_pfh", "Mr. Potato Head", SpeakerCategory.Main, PFH),
    spk("spk_rex", "Rex", SpeakerCategory.Supporting, REX),
    spk("spk_narr", "Narrator", SpeakerCategory.Minor, NARR, { off_camera: true }),
  ];

  const events: CaptionEvent[] = [
    ev(
      "evt_001",
      EventType.Dialogue,
      0.6,
      4.2,
      "spk_woody",
      "I can't believe you did this.",
      [
        w("I", 0.6, 0.95, WOODY, { size_pct: 4.5, weight: 400 }),
        w("can't", 1.0, 1.5, WOODY, { size_pct: 5, weight: 450 }),
        w("believe", 1.55, 2.15, WOODY, { size_pct: 7.5, weight: 620, width: 105 }),
        w("you", 2.2, 2.42, WOODY, { size_pct: 5, weight: 400 }),
        w("did", 2.48, 2.7, WOODY, { size_pct: 6, weight: 560 }),
        w("this.", 2.78, 3.4, WOODY, { size_pct: 5.5, weight: 500 }),
      ],
    ),
    ev(
      "evt_002",
      EventType.SoundEffect,
      4.5,
      5.15,
      null,
      "[DOOR SLAM]",
      [w("[DOOR SLAM]", 4.5, 5.15, "#FFFFFF", { size_pct: 10, weight: 800 })],
    ),
    ev(
      "evt_003",
      EventType.Dialogue,
      5.5,
      9.6,
      "spk_buzz",
      "This is fine. Everything is fine.",
      [
        w("This", 5.5, 5.92, BUZZ, { size_pct: 5, weight: 420 }),
        w("is", 5.98, 6.18, BUZZ, { size_pct: 4.5, weight: 380 }),
        w("fine.", 6.24, 6.75, BUZZ, { size_pct: 5.5, weight: 520 }),
        w("Everything", 6.9, 7.6, BUZZ, { size_pct: 8.5, weight: 720, width: 108 }),
        w("is", 7.65, 7.85, BUZZ, { size_pct: 4.5, weight: 380 }),
        w("fine.", 7.9, 8.5, BUZZ, { size_pct: 5.5, weight: 520 }),
      ],
    ),
    ev(
      "evt_004",
      EventType.Dialogue,
      10.0,
      14.0,
      "spk_narr",
      "Meanwhile, far away, the trouble was just beginning.",
      [
        w("Meanwhile,", 10.0, 10.65, NARR, { size_pct: 5, weight: 400, italic: true }),
        w("far", 10.7, 10.95, NARR, { size_pct: 4.5, weight: 380, italic: true }),
        w("away,", 11.0, 11.45, NARR, { size_pct: 5, weight: 420, italic: true }),
        w("the", 11.5, 11.7, NARR, { size_pct: 4.5, weight: 380, italic: true }),
        w("trouble", 11.75, 12.35, NARR, { size_pct: 6.5, weight: 600, width: 104, italic: true }),
        w("was", 12.4, 12.6, NARR, { size_pct: 4.5, weight: 380, italic: true }),
        w("just", 12.65, 12.9, NARR, { size_pct: 5, weight: 450, italic: true }),
        w("beginning.", 12.95, 13.85, NARR, { size_pct: 7, weight: 640, italic: true }),
      ],
      { off_camera: true },
    ),
    ev(
      "evt_005",
      EventType.Music,
      14.5,
      18.6,
      null,
      "[upright brass sting]",
      [w("[upright brass sting]", 14.5, 18.6, "#FFFFFF", { size_pct: 4.5, weight: 400 })],
    ),
    ev(
      "evt_006",
      EventType.Dialogue,
      19.0,
      23.4,
      "spk_pfh",
      "Oh no. No no no, this is a disaster!",
      [
        w("Oh", 19.0, 19.2, PFH, { size_pct: 5, weight: 480 }),
        w("no.", 19.25, 19.55, PFH, { size_pct: 5.5, weight: 560 }),
        w("No", 19.6, 19.8, PFH, { size_pct: 6, weight: 620 }),
        w("no", 19.85, 20.05, PFH, { size_pct: 6.5, weight: 680 }),
        w("no,", 20.1, 20.35, PFH, { size_pct: 7, weight: 740 }),
        w("this", 20.45, 20.7, PFH, { size_pct: 5, weight: 480 }),
        w("is", 20.75, 20.9, PFH, { size_pct: 4.5, weight: 420 }),
        w("a", 20.95, 21.08, PFH, { size_pct: 4.5, weight: 420 }),
        w("disaster!", 21.15, 22.8, PFH, { size_pct: 11, weight: 880, width: 110 }),
      ],
    ),
  ];

  return {
    schema_version: "ci-project-1",
    design_system: "caption-with-intention-v1.0",
    project_name: "Toy Story — Playroom",
    video: {
      width: 1920,
      height: 1080,
      fps: 23.976,
      duration: 24,
      pixel_aspect_ratio: null,
      codec: "h264",
      audio_codec: "aac",
      audio_sample_rate: 48000,
      audio_channels: 2,
      language: "en",
      source_hash: null,
      proxy_path: null,
    },
    speakers,
    events,
    scenes: [],
    created_at: new Date().toISOString(),
    modified_at: new Date().toISOString(),
    profile_version: "v1.0",
    notes: "",
  };
}

/* ── in-memory client ──────────────────────────────────────── */

function clone<T>(v: T): T {
  return typeof structuredClone === "function"
    ? structuredClone(v)
    : (JSON.parse(JSON.stringify(v)) as T);
}

/** EditorApiClient-compatible, operating on in-memory demo data. */
export class DemoClient {
  readonly source = "demo" as const;
  private project: Project;
  private past: Project[] = [];
  private future: Project[] = [];

  constructor() {
    this.project = createDemoProject();
  }

  private commit() {
    this.past.push(clone(this.project));
    if (this.past.length > 60) this.past.shift();
    this.future.length = 0;
    this.project.modified_at = new Date().toISOString();
  }

  private ok<T>(data: T): ApiResponse<T> {
    return { success: true, data };
  }
  private err(error: string): ApiResponse<any> {
    return { success: false, error };
  }

  // ── project ──
  async getProject() {
    return this.ok(clone(this.project));
  }
  async getProjectSummary() {
    return this.ok({
      project_name: this.project.project_name,
      speaker_count: this.project.speakers.length,
      event_count: this.project.events.length,
      selected_items: [] as string[],
    });
  }

  // ── undo / redo ──
  async undo() {
    if (!this.past.length) return this.ok({ undid: false, selected: [] as string[] });
    this.future.push(clone(this.project));
    this.project = this.past.pop()!;
    return this.ok({ undid: true, selected: [] as string[] });
  }
  async redo() {
    if (!this.future.length) return this.ok({ redid: false, selected: [] as string[] });
    this.past.push(clone(this.project));
    this.project = this.future.pop()!;
    return this.ok({ redid: true, selected: [] as string[] });
  }
  async canUndo() {
    return this.ok({ can_undo: this.past.length > 0 });
  }
  async canRedo() {
    return this.ok({ can_redo: this.future.length > 0 });
  }

  // ── speakers ──
  async addSpeaker(p: {
    name: string;
    category?: string;
    color?: string;
    role?: string;
    off_camera?: boolean;
  }) {
    this.commit();
    const id = `spk_${String(this.project.speakers.length + 1).padStart(3, "0")}`;
    const s = spk(
      id,
      p.name,
      (p.category as SpeakerCategory) ?? SpeakerCategory.Main,
      p.color ?? "#E5E517",
      { role: p.role ?? null, off_camera: p.off_camera ?? false },
    );
    this.project.speakers.push(s);
    return this.ok(s);
  }
  async updateSpeaker(speakerId: string, updates: Partial<Speaker>) {
    this.commit();
    const s = this.project.speakers.find((x) => x.id === speakerId);
    if (!s) return this.err("Speaker not found");
    Object.assign(s, updates, { id: s.id });
    return this.ok(clone(s));
  }
  async setSpeakerColor(speakerId: string, color: string) {
    return this.updateSpeaker(speakerId, { color });
  }
  async removeSpeaker(speakerId: string) {
    this.commit();
    const i = this.project.speakers.findIndex((x) => x.id === speakerId);
    if (i >= 0) this.project.speakers.splice(i, 1);
    return this.ok({ removed: speakerId });
  }
  async getSpeakers() {
    return this.ok(clone(this.project.speakers));
  }

  // ── events ──
  async addEvent(p: {
    text: string;
    start: number;
    end: number;
    speaker_id?: string;
    event_type?: string;
    words?: Array<Record<string, any>>;
  }) {
    this.commit();
    const id = `evt_${String(this.project.events.length + 1).padStart(3, "0")}`;
    const color =
      this.project.speakers.find((s) => s.id === p.speaker_id)?.color ?? "#FFFFFF";
    const words: Word[] =
      p.words && p.words.length
        ? p.words.map((x: any) => ({
            text: x.text ?? "word",
            start: x.start ?? p.start,
            end: x.end ?? p.end,
            size_pct: 5,
            weight: 400,
            width: 100,
            color,
            opacity: 1,
            italic: false,
            confidence: null,
            source_model: null,
            source_timestamp: null,
            manual_override: false,
            review_state: ReviewState.Accepted,
            syllables: null,
          }))
        : [];
    const e = ev(
      id,
      (p.event_type as EventType) ?? EventType.Dialogue,
      p.start,
      p.end,
      p.speaker_id ?? null,
      p.text,
      words,
    );
    this.project.events.push(e);
    this.project.events.sort((a, b) => a.start - b.start);
    return this.ok(clone(e));
  }
  async updateEvent(eventId: string, updates: Partial<CaptionEvent>) {
    this.commit();
    const e = this.project.events.find((x) => x.id === eventId);
    if (!e) return this.err("Event not found");
    Object.assign(e, updates, { id: e.id });
    return this.ok(clone(e));
  }
  async removeEvent(eventId: string) {
    this.commit();
    const i = this.project.events.findIndex((x) => x.id === eventId);
    if (i >= 0) this.project.events.splice(i, 1);
    return this.ok({ removed: eventId });
  }
  async getEvents() {
    return this.ok(clone(this.project.events));
  }

  // ── words ──
  async addWord(eventId: string, text: string, start: number, end: number) {
    this.commit();
    const e = this.project.events.find((x) => x.id === eventId);
    if (!e) return this.err("Event not found");
    const color =
      this.project.speakers.find((s) => s.id === e.speaker_id)?.color ?? "#FFFFFF";
    e.words.push(w(text, start, end, color));
    return this.ok(clone(e));
  }
  async updateWord(eventId: string, wordIndex: number, updates: Partial<Word>) {
    this.commit();
    const e = this.project.events.find((x) => x.id === eventId);
    if (!e || !e.words[wordIndex]) return this.err("Word not found");
    Object.assign(e.words[wordIndex], updates);
    e.text = e.words.map((x) => x.text).join(" ");
    return this.ok(clone(e));
  }
  async removeWord(eventId: string, wordIndex: number) {
    this.commit();
    const e = this.project.events.find((x) => x.id === eventId);
    if (!e) return this.err("Event not found");
    e.words.splice(wordIndex, 1);
    return this.ok(clone(e));
  }
  async adjustWordTiming(eventId: string, wordIndex: number, startDelta: number, endDelta: number) {
    this.commit();
    const e = this.project.events.find((x) => x.id === eventId);
    if (!e || !e.words[wordIndex]) return this.err("Word not found");
    const w = e.words[wordIndex];
    w.start = Math.max(e.start, w.start + startDelta);
    w.end = w.start + Math.max(0.05, w.end - w.start + endDelta);
    return this.ok(clone(e));
  }

  // ── timing ──
  async adjustEventTiming(eventId: string, startDelta: number, endDelta: number) {
    this.commit();
    const e = this.project.events.find((x) => x.id === eventId);
    if (!e) return this.err("Event not found");
    const dur = e.end - e.start;
    e.start = Math.max(0, e.start + startDelta);
    e.end = e.start + Math.max(0.1, dur + endDelta);
    const shift = startDelta;
    e.words.forEach((w) => {
      w.start += shift;
      w.end += shift;
    });
    return this.ok(clone(e));
  }

  // ── style ──
  async setTypography(eventId: string, t: Record<string, any>) {
    this.commit();
    const e = this.project.events.find((x) => x.id === eventId);
    if (!e) return this.err("Event not found");
    Object.assign(e.style, t);
    return this.ok(clone(e));
  }
  async setAnimation(eventId: string, a: Record<string, any>) {
    return this.setTypography(eventId, a);
  }
  async setBoxProperties(eventId: string, b: Record<string, any>) {
    return this.setTypography(eventId, b);
  }

  // ── selection ──
  private selected = new Set<string>();
  async select(itemId: string) {
    this.selected.add(itemId);
    return this.ok({ selected: [...this.selected] });
  }
  async deselect(itemId: string) {
    this.selected.delete(itemId);
    return this.ok({ selected: [...this.selected] });
  }
  async selectAll() {
    this.selected = new Set(this.project.events.map((e) => e.id));
    return this.ok({ selected: [...this.selected] });
  }
  async clearSelection() {
    this.selected.clear();
    return this.ok({ selected: [] });
  }
  async getSelection() {
    return this.ok({ selected: [...this.selected] });
  }
  async applyToSelection(updates: Record<string, any>) {
    this.commit();
    let affected = 0;
    this.project.events.forEach((e) => {
      if (this.selected.has(e.id)) {
        Object.assign(e, updates);
        affected++;
      }
    });
    return this.ok({ affected });
  }

  // ── copy / paste style ──
  async copyStyle(eventId: string) {
    const e = this.project.events.find((x) => x.id === eventId);
    if (!e) return this.err("Event not found");
    return this.ok({ copied_style: clone(e.style) });
  }
  async pasteStyle(sourceEventId: string, targetEventId: string) {
    this.commit();
    const src = this.project.events.find((x) => x.id === sourceEventId);
    const dst = this.project.events.find((x) => x.id === targetEventId);
    if (!src || !dst) return this.err("Event not found");
    dst.style = clone(src.style);
    return this.ok(clone(dst));
  }
}
