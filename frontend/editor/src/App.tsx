import { useState, useCallback, useMemo } from "react";
import { EditorApiClient, createInProcessTransport } from "@/api/client";
import type { EditorAPI } from "@/types";
import { SpeakerPanel } from "@/components/SpeakerPanel";
import { EventList } from "@/components/EventList";
import { EventEditor } from "@/components/EventEditor";
import { InspectorPanel } from "@/components/InspectorPanel";
import { Timeline } from "@/components/Timeline";
import { Toolbar } from "@/components/Toolbar";
import { ProjectSummary } from "@/components/ProjectSummary";

export interface AppProps {
  editorApi?: EditorAPI;
}

export type { EditorAPI } from "@/types";

type ActivePanel = "events" | "speakers" | "inspector";

export function App({ editorApi: propApi }: AppProps) {
  const [api] = useState<EditorAPI>(() => propApi ?? createMockApi());
  const [activePanel, setActivePanel] = useState<ActivePanel>("events");
  const [selectedEventId, setSelectedEventId] = useState<string | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);

  const forceRefresh = useCallback(() => setRefreshKey((k) => k + 1), []);

  const projectSummary = useMemo(
    () => api.getProjectSummary?.() ?? { success: false, data: {} },
    [api, refreshKey],
  );

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        height: "100vh",
        overflow: "hidden",
      }}
    >
      {/* Header */}
      <header
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "8px 16px",
          background: "var(--color-bg-secondary)",
          borderBottom: "1px solid var(--color-border)",
        }}
      >
        <h1
          style={{
            fontSize: "1.2rem",
            margin: 0,
            border: "none",
            padding: 0,
          }}
        >
          Caption With Intention
        </h1>
        <ProjectSummary summary={projectSummary.data} />
      </header>

      {/* Toolbar */}
      <Toolbar api={api} onAction={forceRefresh} />

      {/* Main Content — 3-panel layout */}
      <div
        style={{
          display: "flex",
          flex: 1,
          overflow: "hidden",
        }}
      >
        {/* Left Sidebar — Speakers & Navigation */}
        <aside
          style={{
            width: "240px",
            minWidth: "240px",
            borderRight: "1px solid var(--color-border)",
            display: "flex",
            flexDirection: "column",
          }}
        >
          <nav
            style={{
              display: "flex",
              borderBottom: "1px solid var(--color-border)",
            }}
          >
            {([
              { key: "events", label: "Events" },
              { key: "speakers", label: "Speakers" },
              { key: "inspector", label: "Inspector" },
            ] as { key: ActivePanel; label: string }[]).map((tab) => (
              <button
                key={tab.key}
                onClick={() => setActivePanel(tab.key)}
                style={{
                  flex: 1,
                  borderRadius: 0,
                  borderBottom:
                    activePanel === tab.key
                      ? "2px solid var(--color-accent)"
                      : "2px solid transparent",
                  background:
                    activePanel === tab.key
                      ? "var(--color-bg-tertiary)"
                      : "transparent",
                }}
              >
                {tab.label}
              </button>
            ))}
          </nav>

          <div style={{ flex: 1, overflow: "auto", padding: "var(--spacing-md)" }}>
            {activePanel === "speakers" && (
              <SpeakerPanel api={api} onAction={forceRefresh} key={refreshKey} />
            )}
            {activePanel === "events" && (
              <EventList
                api={api}
                selectedEventId={selectedEventId}
                onSelectEvent={setSelectedEventId}
                onAction={forceRefresh}
                key={refreshKey}
              />
            )}
            {activePanel === "inspector" && selectedEventId && (
              <InspectorPanel
                api={api}
                eventId={selectedEventId}
                onAction={forceRefresh}
                key={refreshKey}
              />
            )}
            {activePanel === "inspector" && !selectedEventId && (
              <div style={{ color: "var(--color-text-muted)", padding: "var(--spacing-xl)" }}>
                Select an event to inspect its properties.
              </div>
            )}
          </div>
        </aside>

        {/* Center — Timeline + Editor */}
        <main
          style={{
            flex: 1,
            display: "flex",
            flexDirection: "column",
            overflow: "hidden",
          }}
        >
          <div
            style={{
              padding: "var(--spacing-md)",
              overflow: "auto",
              flex: 1,
            }}
          >
            <Timeline api={api} onAction={forceRefresh} key={refreshKey} />

            {activePanel === "events" && (
              <EventEditor
                api={api}
                selectedEventId={selectedEventId}
                onSelectEvent={setSelectedEventId}
                onAction={forceRefresh}
                key={refreshKey}
              />
            )}
          </div>
        </main>
      </div>
    </div>
  );
}

/** Creates a mock API for standalone/demo use without Python backend. */
function createMockApi(): EditorAPI {
  return {
    getProjectSummary: () => ({
      success: true,
      data: {
        project_name: "Untitled",
        speaker_count: 0,
        event_count: 0,
        scene_count: 0,
        selected_items: [],
        modified_at: null,
      },
    }),
  } as unknown as EditorAPI;
}
