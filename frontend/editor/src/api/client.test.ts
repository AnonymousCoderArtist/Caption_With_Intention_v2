import { test, describe, expect, vi } from "vitest";
import { EditorApiClient, createInProcessTransport } from "@/api/client";
import type { Project, CaptionEvent, Speaker } from "@/types/project";

// ─── Test API mock ──────────────────────────────

function createTestApi(overrides: Partial<Record<string, any>> = {}) {
  const defaults = {
    getProjectSummary: () => ({
      success: true,
      data: {
        project_name: "Test Project",
        speaker_count: 2,
        event_count: 5,
        scene_count: 1,
        selected_items: [],
        modified_at: "2026-01-01T00:00:00Z",
      },
    }),
    getProject: () => ({
      success: true,
      data: {
        schema_version: "ci-project-1",
        design_system: "caption-with-intention-v1.0",
        project_name: "Test Project",
        video: {
          width: 1920,
          height: 1080,
          fps: 23.976,
          duration: 60.0,
          codec: "h264",
          audio_codec: "aac",
          audio_sample_rate: 48000,
          audio_channels: 2,
          language: "en",
          source_hash: null,
          proxy_path: null,
          pixel_aspect_ratio: null,
        },
        speakers: [
          {
            id: "spk_001",
            name: "Alice",
            category: "main",
            role: null,
            color: "#E5E517",
            confidence: null,
            source_model: null,
            source_timestamp: null,
            manual_override: false,
            review_state: "pending",
            off_camera: false,
            active_speaker: false,
            notes: "",
          },
          {
            id: "spk_002",
            name: "Bob",
            category: "supporting",
            role: null,
            color: "#FF6B6B",
            confidence: null,
            source_model: null,
            source_timestamp: null,
            manual_override: false,
            review_state: "pending",
            off_camera: false,
            active_speaker: false,
            notes: "",
          },
        ],
        events: [
          {
            id: "evt_001",
            type: "dialogue",
            start: 0.0,
            end: 3.0,
            speaker_id: "spk_001",
            off_camera: false,
            text: "Hello there",
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
            words: [
              {
                text: "Hello",
                start: 0.0,
                end: 1.5,
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
                review_state: "pending",
                syllables: null,
              },
              {
                text: "there",
                start: 1.5,
                end: 3.0,
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
                review_state: "pending",
                syllables: null,
              },
            ],
            confidence: null,
            source_model: null,
            source_timestamp: null,
            manual_override: false,
            review_state: "pending",
            exception_profile: null,
            notes: "",
          },
        ],
        scenes: [],
        created_at: "2026-01-01T00:00:00Z",
        modified_at: "2026-01-01T00:00:00Z",
        profile_version: "v1.0",
        notes: "",
      },
    }),
  };
  return { ...defaults, ...overrides };
}

// ─── Tests ──────────────────────────────────────

describe("EditorApiClient", () => {
  test("createInProcessTransport returns a transport function", () => {
    const mockApi = createTestApi();
    const transport = createInProcessTransport(mockApi);
    expect(typeof transport).toBe("function");
  });

  test("transport calls the correct method with params", async () => {
    const mockApi = createTestApi({
      add_speaker: (params: any) => ({
        success: true,
        data: { id: "spk_003", ...params },
      }),
    });
    const transport = createInProcessTransport(mockApi);
    const result = await transport("add_speaker", { name: "Charlie" });
    expect(result.success).toBe(true);
    expect(result.data.name).toBe("Charlie");
  });

  test("transport returns error for unknown action", async () => {
    const mockApi = createTestApi();
    const transport = createInProcessTransport(mockApi);
    const result = await transport("nonexistent_action");
    expect(result.error).toContain("Unknown action");
  });

  test("transport propagates exceptions from the API", async () => {
    const mockApi = createTestApi({
      get_project: () => {
        throw new Error("Connection lost");
      },
    });
    const transport = createInProcessTransport(mockApi);
    const result = await transport("get_project");
    expect(result.error).toContain("Connection lost");
  });
});

describe("Type validation", () => {
  test("CaptionEvent shape matches schema", () => {
    const api = createTestApi();
    const projectResult = api.getProject();
    const project = projectResult.data as Project;

    expect(project.schema_version).toBe("ci-project-1");
    expect(project.project_name).toBe("Test Project");
    expect(project.speakers).toHaveLength(2);
    expect(project.events).toHaveLength(1);
  });

  test("CaptionEvent has required fields", () => {
    const api = createTestApi();
    const project = api.getProject().data as Project;
    const event = project.events[0] as CaptionEvent;

    expect(event.id).toBe("evt_001");
    expect(event.type).toBe("dialogue");
    expect(event.start).toBe(0.0);
    expect(event.end).toBe(3.0);
    expect(event.words).toHaveLength(2);
    expect(event.style).toBeDefined();
  });

  test("Word fields are properly typed", () => {
    const api = createTestApi();
    const project = api.getProject().data as Project;
    const word = project.events[0].words[0];

    expect(word.text).toBe("Hello");
    expect(word.start).toBe(0.0);
    expect(word.end).toBe(1.5);
    expect(word.size_pct).toBe(5.0);
    expect(word.weight).toBe(400);
    expect(word.width).toBe(100);
    expect(word.italic).toBe(false);
  });

  test("Speaker fields are properly typed", () => {
    const api = createTestApi();
    const project = api.getProject().data as Project;
    const speaker = project.speakers[0];

    expect(speaker.id).toBe("spk_001");
    expect(speaker.name).toBe("Alice");
    expect(speaker.category).toBe("main");
    expect(speaker.color).toBe("#E5E517");
    expect(speaker.off_camera).toBe(false);
  });

  test("Style fields are properly typed", () => {
    const api = createTestApi();
    const project = api.getProject().data as Project;
    const style = project.events[0].style;

    expect(style.size_pct).toBe(5.0);
    expect(style.weight).toBe(400);
    expect(style.width).toBe(100);
    expect(style.italic).toBe(false);
    expect(style.pop_scale).toBe(1.15);
    expect(style.box_opacity).toBe(0.9);
    expect(style.box_padding).toBe(10);
    expect(style.breakout_permission).toBe(false);
    expect(style.syllable_mode).toBe(false);
  });
});

describe("API response shape", () => {
  test("success responses have success:true", () => {
    const api = createTestApi();
    expect(api.getProject().success).toBe(true);
    expect(api.getProjectSummary().success).toBe(true);
  });

  test("error responses have error string", () => {
    const transport = vi.fn().mockResolvedValue({ error: "Not found" });
    const client = new EditorApiClient(transport);
    client.getProject().then((r) => {
      expect(r.error).toBe("Not found");
    });
  });
});
