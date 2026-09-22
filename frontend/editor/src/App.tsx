import { useState, useCallback, useEffect, useRef } from "react";
import { EditorApiClient } from "@/api/client";
import type { ApiResponse } from "@/types/project";
import { SpeakerPanel } from "@/components/SpeakerPanel";
import { EventList } from "@/components/EventList";
import { EventEditor } from "@/components/EventEditor";
import { InspectorPanel } from "@/components/InspectorPanel";
import { Timeline } from "@/components/Timeline";
import { Toolbar } from "@/components/Toolbar";
import { ProjectSummary } from "@/components/ProjectSummary";

function isApiResponse<T>(r: ApiResponse<T> | { success: boolean; data: any }): r is ApiResponse<T> {
  return "success" in r;
}

type ActivePanel = "events" | "speakers" | "inspector";

export function App() {
  const apiRef = useRef<EditorApiClient | null>(null);
  if (!apiRef.current) {
    apiRef.current = new EditorApiClient(async (action, params) => {
      const query = params ? `?${new URLSearchParams(params).toString()}` : "";
      const res = await fetch(`/api/${action}${query}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: params ? JSON.stringify(params) : undefined,
      });
      return res.json();
    });
  }
  const api = apiRef.current;

  const [activePanel, setActivePanel] = useState<ActivePanel>("events");
  const [selectedEventId, setSelectedEventId] = useState<string | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);
  const [loading, setLoading] = useState(true);

  const [projectSummary, setProjectSummary] = useState<{ success: boolean; data: Record<string, any> }>({ success: false, data: {} });

  const forceRefresh = useCallback(() => setRefreshKey((k) => k + 1), []);

  useEffect(() => {
    setLoading(false);
    api.getProjectSummary().then((r) => {
      if (r && typeof r === "object" && "success" in r && r.success) {
        setProjectSummary(r as { success: boolean; data: Record<string, any> });
      }
    });
  }, [api]);

  if (loading) {
    return <div className="loading">Loading CWI Editor...</div>;
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100vh", overflow: "hidden" }}>
      {/* Header */}
      <header
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "var(--sp-3) var(--sp-5)",
          background: "linear-gradient(180deg, var(--bg-2) 0%, var(--bg-1) 100%)",
          borderBottom: "1px solid var(--border)",
        }}
      >
        <h1 style={{ fontSize: "1.15rem", margin: 0, border: "none", padding: 0, letterSpacing: "-0.01em" }}>
          Caption With Intention
        </h1>
        <ProjectSummary summary={projectSummary.data} />
      </header>

      {/* Toolbar */}
      <Toolbar api={api} onAction={forceRefresh} />

      {/* Main Content */}
      <div style={{ display: "flex", flex: 1, overflow: "hidden" }}>
        {/* Left Sidebar */}
        <aside
          style={{
            width: "240px",
            minWidth: "240px",
            borderRight: "1px solid var(--border)",
            display: "flex",
            flexDirection: "column",
            background: "var(--bg-1)",
          }}
        >
          <div className="tab-bar">
            {[
              { key: "events", label: "Events" },
              { key: "speakers", label: "Speakers" },
              { key: "inspector", label: "Inspector" },
            ].map((tab) => (
              <button
                key={tab.key}
                className={`tab ${activePanel === tab.key ? "active" : ""}`}
                onClick={() => setActivePanel(tab.key as ActivePanel)}
              >
                {tab.label}
              </button>
            ))}
          </div>

          <div style={{ flex: 1, overflow: "auto", padding: "var(--sp-4)" }}>
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
              <div style={{ color: "var(--text-400)", padding: "var(--sp-6)", textAlign: "center" }}>
                Select an event to inspect its properties.
              </div>
            )}
          </div>
        </aside>

        {/* Center — Timeline + Editor */}
        <main style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>
          <div style={{ padding: "var(--sp-5)", overflow: "auto", flex: 1 }}>
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
