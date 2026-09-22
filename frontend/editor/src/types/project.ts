/** TypeScript types mirroring the Python schema models.

These types are kept in sync with schemas/project.py and are
used across the editor components and API client.
*/

// ─── Enums ──────────────────────────────────────────────

export enum SpeakerCategory {
  Main = "main",
  Supporting = "supporting",
  Minor = "minor",
}

export enum EventType {
  Dialogue = "dialogue",
  SoundEffect = "sound_effect",
  Music = "music",
  SpeakerOverlap = "speaker_overlap",
  Custom = "custom",
}

export enum ReviewState {
  Pending = "pending",
  Accepted = "accepted",
  Rejected = "rejected",
  Corrected = "corrected",
}

// ─── Word ────────────────────────────────────────────────

export interface Word {
  text: string;
  start: number;
  end: number;
  size_pct: number;
  weight: number;
  width: number;
  color: string;
  opacity: number;
  italic: boolean;
  confidence: number | null;
  source_model: string | null;
  source_timestamp: number | null;
  manual_override: boolean;
  review_state: ReviewState;
  syllables: WordSyllable[] | null;
}

export interface WordSyllable {
  text: string;
  start: number;
  end: number;
}

// ─── Style ──────────────────────────────────────────────

export interface Style {
  read_ahead_opacity: number;
  pop_scale: number;
  size_pct: number;
  weight: number;
  width: number;
  italic: boolean;
  size_mode: "auto" | "manual";
  weight_mode: "auto" | "manual";
  width_mode: "auto" | "manual";
  color_transition_point: number | null;
  color_transition_duration: number | null;
  pop_duration: number | null;
  pop_easing: "smooth" | "ease_in" | "ease_out";
  syllable_mode: boolean;
  box_opacity: number;
  box_padding: number;
  breakout_permission: boolean;
  minimum_pct: number;
  maximum_pct: number;
}

// ─── CaptionEvent ────────────────────────────────────────

export interface CaptionEvent {
  id: string;
  type: EventType;
  start: number;
  end: number;
  speaker_id: string | null;
  off_camera: boolean;
  text: string;
  style: Style;
  words: Word[];
  confidence: number | null;
  source_model: string | null;
  source_timestamp: number | null;
  manual_override: boolean;
  review_state: ReviewState;
  exception_profile: string | null;
  notes: string;
}

// ─── Speaker ────────────────────────────────────────────

export interface Speaker {
  id: string;
  name: string;
  category: SpeakerCategory;
  role: string | null;
  color: string;
  confidence: number | null;
  source_model: string | null;
  source_timestamp: number | null;
  manual_override: boolean;
  review_state: ReviewState;
  off_camera: boolean;
  active_speaker: boolean;
  notes: string;
}

// ─── VideoInfo ──────────────────────────────────────────

export interface VideoInfo {
  width: number;
  height: number;
  fps: number;
  duration: number;
  pixel_aspect_ratio: [number, number] | null;
  codec: string | null;
  audio_codec: string | null;
  audio_sample_rate: number | null;
  audio_channels: number | null;
  language: string | null;
  source_hash: string | null;
  proxy_path: string | null;
}

// ─── Project ────────────────────────────────────────────

export interface Project {
  schema_version: string;
  design_system: string;
  project_name: string;
  video: VideoInfo;
  speakers: Speaker[];
  events: CaptionEvent[];
  scenes: Record<string, any>[];
  created_at: string | null;
  modified_at: string | null;
  profile_version: string;
  notes: string;
}

// ─── API Response ────────────────────────────────────────

export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  error?: string;
}

// ─── Editor Action Types ─────────────────────────────────

export interface EditAction {
  action_type: string;
  target_id: string;
  before: Record<string, any>;
  after: Record<string, any>;
}

// ─── Inspector Types ─────────────────────────────────────

export interface TypographyState {
  size_pct: number;
  weight: number;
  width: number;
  italic: boolean;
  size_mode: "auto" | "manual";
  weight_mode: "auto" | "manual";
  width_mode: "auto" | "manual";
}

export interface AnimationState {
  pop_scale: number;
  pop_duration: number | null;
  pop_easing: "smooth" | "ease_in" | "ease_out";
  syllable_mode: boolean;
  color_transition_point: number | null;
  color_transition_duration: number | null;
}

export interface BoxState {
  box_opacity: number;
  box_padding: number;
  breakout_permission: boolean;
}

// ─── Transcript Types ────────────────────────────────────

export interface TranscriptEntry {
  text: string;
  start: number;
  end: number;
}

export interface SpeakerInput {
  name: string;
  category?: SpeakerCategory;
  color?: string;
  role?: string;
  off_camera?: boolean;
}
