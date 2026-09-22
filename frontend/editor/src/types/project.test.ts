import { describe, expect, it } from "vitest";
import {
  SpeakerCategory,
  EventType,
  ReviewState,
  type Word,
  type Style,
  type CaptionEvent,
  type Speaker,
  type Project,
} from "@/types/project";

describe("Type definitions", () => {
  it("SpeakerCategory has correct values", () => {
    expect(SpeakerCategory.Main).toBe("main");
    expect(SpeakerCategory.Supporting).toBe("supporting");
    expect(SpeakerCategory.Minor).toBe("minor");
  });

  it("EventType has correct values", () => {
    expect(EventType.Dialogue).toBe("dialogue");
    expect(EventType.SoundEffect).toBe("sound_effect");
    expect(EventType.Music).toBe("music");
  });

  it("ReviewState has correct values", () => {
    expect(ReviewState.Pending).toBe("pending");
    expect(ReviewState.Accepted).toBe("accepted");
    expect(ReviewState.Rejected).toBe("rejected");
    expect(ReviewState.Corrected).toBe("corrected");
  });

  it("Word type has all required fields", () => {
    const word: Word = {
      text: "test",
      start: 0.0,
      end: 1.0,
      size_pct: 5.0,
      weight: 400,
      width: 100,
      color: "#FFFFFF",
      opacity: 1.0,
      italic: false,
      confidence: null,
      source_model: null,
      source_timestamp: null,
      manual_override: false,
      review_state: ReviewState.Pending,
      syllables: null,
    };
    expect(word.text).toBe("test");
    expect(word.start).toBe(0.0);
  });

  it("Style type has all required fields", () => {
    const style: Style = {
      read_ahead_opacity: 0.9,
      pop_scale: 1.15,
      size_pct: 5.0,
      weight: 400,
      width: 100,
      italic: false,
      size_mode: "auto",
      weight_mode: "auto",
      width_mode: "auto",
      color_transition_point: null,
      color_transition_duration: null,
      pop_duration: null,
      pop_easing: "smooth",
      syllable_mode: false,
      box_opacity: 0.9,
      box_padding: 10,
      breakout_permission: false,
      minimum_pct: 3.0,
      maximum_pct: 12.0,
    };
    expect(style.size_pct).toBe(5.0);
    expect(style.box_padding).toBe(10);
  });

  it("CaptionEvent type has all required fields", () => {
    const event: CaptionEvent = {
      id: "evt_001",
      type: EventType.Dialogue,
      start: 0.0,
      end: 3.0,
      speaker_id: null,
      off_camera: false,
      text: "test",
      style: {
        read_ahead_opacity: 0.9,
        pop_scale: 1.15,
        size_pct: 5.0,
        weight: 400,
        width: 100,
        italic: false,
        size_mode: "auto",
        weight_mode: "auto",
        width_mode: "auto",
        color_transition_point: null,
        color_transition_duration: null,
        pop_duration: null,
        pop_easing: "smooth",
        syllable_mode: false,
        box_opacity: 0.9,
        box_padding: 10,
        breakout_permission: false,
        minimum_pct: 3.0,
        maximum_pct: 12.0,
      },
      words: [],
      confidence: null,
      source_model: null,
      source_timestamp: null,
      manual_override: false,
      review_state: ReviewState.Pending,
      exception_profile: null,
      notes: "",
    };
    expect(event.id).toBe("evt_001");
    expect(event.words).toHaveLength(0);
  });

  it("Speaker type has all required fields", () => {
    const speaker: Speaker = {
      id: "spk_001",
      name: "Test",
      category: SpeakerCategory.Main,
      role: null,
      color: "#E5E517",
      confidence: null,
      source_model: null,
      source_timestamp: null,
      manual_override: false,
      review_state: ReviewState.Pending,
      off_camera: false,
      active_speaker: false,
      notes: "",
    };
    expect(speaker.color).toBe("#E5E517");
  });

  it("Project type has all required fields", () => {
    const project: Project = {
      schema_version: "ci-project-1",
      design_system: "caption-with-intention-v1.0",
      project_name: "Test",
      video: {
        width: 1920,
        height: 1080,
        fps: 23.976,
        duration: 0.0,
        pixel_aspect_ratio: null,
        codec: null,
        audio_codec: null,
        audio_sample_rate: null,
        audio_channels: null,
        language: null,
        source_hash: null,
        proxy_path: null,
      },
      speakers: [],
      events: [],
      scenes: [],
      created_at: null,
      modified_at: null,
      profile_version: "v1.0",
      notes: "",
    };
    expect(project.events).toHaveLength(0);
  });
});
