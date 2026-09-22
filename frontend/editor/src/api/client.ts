/** API client for the Editor API service layer.

This client is transport-agnostic — it wraps a transport function
that sends JSON requests and receives JSON responses.
The default implementation uses a direct in-process reference,
but it can be swapped for HTTP/IPC/WebChannel by changing
the `transport` function.
*/

import type {
  ApiResponse,
  CaptionEvent,
  Project,
  Speaker,
  Word,
  Style,
  TranscriptEntry,
  SpeakerInput,
  TypographyState,
  AnimationState,
  BoxState,
} from "@/types/project";

export type { ApiResponse, CaptionEvent, Project, Speaker, Word, Style, TranscriptEntry, SpeakerInput, TypographyState, AnimationState, BoxState };

// ─── Transport Interface ──────────────────────────────────

export type TransportFn = (
  action: string,
  params?: Record<string, any>,
) => Promise<ApiResponse<any>>;

// ─── API Client ───────────────────────────────────────────

export class EditorApiClient {
  private transport: TransportFn;

  constructor(transport: TransportFn) {
    this.transport = transport;
  }

  // ─── Project ────────────────────────────────────────────

  async getProject(): Promise<ApiResponse<Project>> {
    return this.transport("get_project");
  }

  async getProjectSummary(): Promise<ApiResponse<Record<string, any>>> {
    return this.transport("get_project_summary");
  }

  // ─── Undo / Redo ────────────────────────────────────────

  async undo(): Promise<ApiResponse<{ undid: boolean; selected: string[] }>> {
    return this.transport("undo");
  }

  async redo(): Promise<ApiResponse<{ redid: boolean; selected: string[] }>> {
    return this.transport("redo");
  }

  async canUndo(): Promise<ApiResponse<{ can_undo: boolean }>> {
    return this.transport("can_undo");
  }

  async canRedo(): Promise<ApiResponse<{ can_redo: boolean }>> {
    return this.transport("can_redo");
  }

  // ─── Speakers ───────────────────────────────────────────

  async addSpeaker(params: {
    name: string;
    category?: string;
    color?: string;
    role?: string;
    off_camera?: boolean;
  }): Promise<ApiResponse<Speaker>> {
    return this.transport("add_speaker", params);
  }

  async updateSpeaker(
    speakerId: string,
    updates: Partial<Speaker>,
  ): Promise<ApiResponse<Speaker>> {
    return this.transport("update_speaker", { speaker_id: speakerId, ...updates });
  }

  async removeSpeaker(speakerId: string): Promise<ApiResponse<{ removed: string }>> {
    return this.transport("remove_speaker", { speaker_id: speakerId });
  }

  async getSpeakers(): Promise<ApiResponse<Speaker[]>> {
    return this.transport("get_speakers");
  }

  // ─── Events ─────────────────────────────────────────────

  async addEvent(params: {
    text: string;
    start: number;
    end: number;
    speaker_id?: string;
    event_type?: string;
    words?: Array<Record<string, any>>;
  }): Promise<ApiResponse<CaptionEvent>> {
    return this.transport("add_event", params);
  }

  async updateEvent(
    eventId: string,
    updates: Partial<CaptionEvent>,
  ): Promise<ApiResponse<CaptionEvent>> {
    return this.transport("update_event", { event_id: eventId, ...updates });
  }

  async removeEvent(eventId: string): Promise<ApiResponse<{ removed: string }>> {
    return this.transport("remove_event", { event_id: eventId });
  }

  async getEvents(): Promise<ApiResponse<CaptionEvent[]>> {
    return this.transport("get_events");
  }

  // ─── Words ──────────────────────────────────────────────

  async addWord(
    eventId: string,
    text: string,
    start: number,
    end: number,
  ): Promise<ApiResponse<CaptionEvent>> {
    return this.transport("add_word", {
      event_id: eventId,
      text,
      start,
      end,
    });
  }

  async updateWord(
    eventId: string,
    wordIndex: number,
    updates: Partial<Word>,
  ): Promise<ApiResponse<CaptionEvent>> {
    return this.transport("update_word", {
      event_id: eventId,
      word_index: wordIndex,
      ...updates,
    });
  }

  async removeWord(
    eventId: string,
    wordIndex: number,
  ): Promise<ApiResponse<CaptionEvent>> {
    return this.transport("remove_word", {
      event_id: eventId,
      word_index: wordIndex,
    });
  }

  // ─── Syllables ──────────────────────────────────────────

  async addSyllable(
    eventId: string,
    wordIndex: number,
    text: string,
    start: number,
    end: number,
  ): Promise<ApiResponse<CaptionEvent>> {
    return this.transport("add_syllable", {
      event_id: eventId,
      word_index: wordIndex,
      text,
      start,
      end,
    });
  }

  async updateSyllable(
    eventId: string,
    wordIndex: number,
    syllableIndex: number,
    updates: Record<string, any>,
  ): Promise<ApiResponse<CaptionEvent>> {
    return this.transport("update_syllable", {
      event_id: eventId,
      word_index: wordIndex,
      syllable_index: syllableIndex,
      ...updates,
    });
  }

  // ─── Timing ─────────────────────────────────────────────

  async adjustEventTiming(
    eventId: string,
    startDelta: number,
    endDelta: number,
  ): Promise<ApiResponse<CaptionEvent>> {
    return this.transport("adjust_event_timing", {
      event_id: eventId,
      start_delta: startDelta,
      end_delta: endDelta,
    });
  }

  async adjustWordTiming(
    eventId: string,
    wordIndex: number,
    startDelta: number,
    endDelta: number,
  ): Promise<ApiResponse<CaptionEvent>> {
    return this.transport("adjust_word_timing", {
      event_id: eventId,
      word_index: wordIndex,
      start_delta: startDelta,
      end_delta: endDelta,
    });
  }

  // ─── Typography ─────────────────────────────────────────

  async setTypography(
    eventId: string,
    typography: TypographyState,
  ): Promise<ApiResponse<CaptionEvent>> {
    return this.transport("set_typography", {
      event_id: eventId,
      ...typography,
    });
  }

  // ─── Animation ──────────────────────────────────────────

  async setAnimation(
    eventId: string,
    animation: AnimationState,
  ): Promise<ApiResponse<CaptionEvent>> {
    return this.transport("set_animation", {
      event_id: eventId,
      ...animation,
    });
  }

  // ─── Box Properties ─────────────────────────────────────

  async setBoxProperties(
    eventId: string,
    box: BoxState,
  ): Promise<ApiResponse<CaptionEvent>> {
    return this.transport("set_box_properties", {
      event_id: eventId,
      ...box,
    });
  }

  // ─── Speaker Editor ─────────────────────────────────────

  async setSpeakerColor(
    speakerId: string,
    color: string,
  ): Promise<ApiResponse<Speaker>> {
    return this.transport("set_speaker_color", {
      speaker_id: speakerId,
      color,
    });
  }

  async setSpeakerCategory(
    speakerId: string,
    category: string,
  ): Promise<ApiResponse<Speaker>> {
    return this.transport("set_speaker_category", {
      speaker_id: speakerId,
      category,
    });
  }

  async setSpeakerOffCamera(
    speakerId: string,
    offCamera: boolean,
  ): Promise<ApiResponse<Speaker>> {
    return this.transport("set_speaker_off_camera", {
      speaker_id: speakerId,
      off_camera: offCamera,
    });
  }

  async assignPaletteColor(
    speakerId: string,
    color: string,
  ): Promise<ApiResponse<Speaker>> {
    return this.transport("assign_palette_color", {
      speaker_id: speakerId,
      color,
    });
  }

  // ─── Scene Overrides ────────────────────────────────────

  async setSceneOverride(
    sceneId: string,
    overrides: Record<string, any>,
  ): Promise<ApiResponse<Record<string, any>>> {
    return this.transport("set_scene_override", {
      scene_id: sceneId,
      overrides,
    });
  }

  // ─── Multi-Select ───────────────────────────────────────

  async select(itemId: string): Promise<ApiResponse<{ selected: string[] }>> {
    return this.transport("select", { item_id: itemId });
  }

  async deselect(itemId: string): Promise<ApiResponse<{ selected: string[] }>> {
    return this.transport("deselect", { item_id: itemId });
  }

  async selectAll(): Promise<ApiResponse<{ selected: string[] }>> {
    return this.transport("select_all");
  }

  async clearSelection(): Promise<ApiResponse<{ selected: [] }>> {
    return this.transport("clear_selection");
  }

  async applyToSelection(
    updates: Record<string, any>,
  ): Promise<ApiResponse<{ affected: number }>> {
    return this.transport("apply_to_selection", updates);
  }

  async getSelection(): Promise<ApiResponse<{ selected: string[] }>> {
    return this.transport("get_selection");
  }

  // ─── Copy / Paste Style ─────────────────────────────────

  async copyStyle(eventId: string): Promise<ApiResponse<{ copied_style: Style }>> {
    return this.transport("copy_style", { source_event_id: eventId });
  }

  async pasteStyle(
    sourceEventId: string,
    targetEventId: string,
  ): Promise<ApiResponse<CaptionEvent>> {
    return this.transport("paste_style", {
      source_event_id: sourceEventId,
      target_event_id: targetEventId,
    });
  }

  // ─── Build from Transcript ──────────────────────────────

  async buildFromTranscript(
    transcript: TranscriptEntry[],
    videoWidth: number = 1920,
    videoHeight: number = 1080,
    fps: number = 23.976,
    speakers?: SpeakerInput[],
  ): Promise<ApiResponse<Project>> {
    return this.transport("build_from_transcript", {
      transcript,
      video_width: videoWidth,
      video_height: videoHeight,
      fps,
      speakers,
    });
  }

  // ─── Style ──────────────────────────────────────────────

  async getDefaultStyle(): Promise<ApiResponse<Style>> {
    return this.transport("get_default_style");
  }

  async getSpeakerPaletteColors(): Promise<ApiResponse<string[]>> {
    return this.transport("get_speaker_palette_colors");
  }
}

// ─── In-process transport (for direct Python interop) ────

export function createInProcessTransport(
  apiInstance: any,
): TransportFn {
  return async (action: string, params?: Record<string, any>) => {
    const method = (apiInstance as any)[action];
    if (!method) {
      return { error: `Unknown action: ${action}` };
    }
    try {
      const result = params ? await method(params) : await method();
      return result;
    } catch (exc) {
      return { error: String(exc) };
    }
  };
}
