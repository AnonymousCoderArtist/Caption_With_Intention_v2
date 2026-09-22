/**EditorAPI TypeScript interface — mirrors engine/editor/api.py.*/

import type { Project, CaptionEvent, Speaker, Style } from "@/types/project";

export interface IEditorAPI {
  getProjectSummary(): Promise<{ success: boolean; data: { project_name: string; speaker_count: number; event_count: number; selected_items: string[] } }>;
  getProject(): Promise<{ success: boolean; data: Project }>;
  undo(): Promise<{ success: boolean; data: { undid: boolean; selected: string[] } }>;
  redo(): Promise<{ success: boolean; data: { redid: boolean; selected: string[] } }>;
  canUndo(): Promise<{ success: boolean; data: { can_undo: boolean } }>;
  canRedo(): Promise<{ success: boolean; data: { can_redo: boolean } }>;
  addSpeaker(params: { name: string; category?: string; color?: string; role?: string; off_camera?: boolean }): Promise<{ success: boolean; data?: Speaker; error?: string }>;
  updateSpeaker(speakerId: string, updates: Partial<Speaker>): Promise<{ success: boolean; data?: Speaker; error?: string }>;
  removeSpeaker(speakerId: string): Promise<{ success: boolean; data?: { removed: string }; error?: string }>;
  getSpeakers(): Promise<{ success: boolean; data: Speaker[]; error?: string }>;
  addEvent(params: { text: string; start: number; end: number; speaker_id?: string; event_type?: string; words?: Array<Record<string, any>> }): Promise<{ success: boolean; data?: CaptionEvent; error?: string }>;
  updateEvent(eventId: string, updates: Partial<CaptionEvent>): Promise<{ success: boolean; data?: CaptionEvent; error?: string }>;
  removeEvent(eventId: string): Promise<{ success: boolean; data?: { removed: string }; error?: string }>;
  getEvents(): Promise<{ success: boolean; data: CaptionEvent[]; error?: string }>;
  setTypography(eventId: string, typography: Record<string, any>): Promise<{ success: boolean; data?: CaptionEvent; error?: string }>;
  copyStyle(eventId: string): Promise<{ success: boolean; data?: { copied_style: Style }; error?: string }>;
  pasteStyle(sourceEventId: string, targetEventId: string): Promise<{ success: boolean; data?: CaptionEvent; error?: string }>;
  select(itemId: string): Promise<{ success: boolean; data: { selected: string[] } }>;
  deselect(itemId: string): Promise<{ success: boolean; data: { selected: string[] } }>;
  selectAll(): Promise<{ success: boolean; data: { selected: string[] } }>;
  clearSelection(): Promise<{ success: boolean; data: { selected: string[] } }>;
  applyToSelection(updates: Record<string, any>): Promise<{ success: boolean; data: { affected: number }; error?: string }>;
}
