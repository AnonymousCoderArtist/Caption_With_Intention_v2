import { useState, useEffect, useRef, useCallback } from "react";
import { EditorApiClient } from "@/api/client";
import { SpeakerPanel } from "@/components/SpeakerPanel";
import { EventList } from "@/components/EventList";
import { EventEditor } from "@/components/EventEditor";
import { InspectorPanel } from "@/components/InspectorPanel";
import { Timeline } from "@/components/Timeline";
import { Toolbar } from "@/components/Toolbar";

type ActivePanel = "events" | "speakers" | "inspector";

/* ────────────────────────────────────────────────
   WELCOME SCREEN — Cinematic, Awwwards-grade
   ──────────────────────────────────────────────── */
function WelcomeScreen({ onNewProject, onOpen }: { onNewProject: () => void; onOpen: () => void }) {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    const t = requestAnimationFrame(() => setMounted(true));
    return () => cancelAnimationFrame(t);
  }, []);

  const anim = (delay: number, i: number) => ({
    opacity: mounted ? 1 : 0,
    transform: mounted ? "translateY(0)" : "translateY(24px)",
    transition: `all 0.7s cubic-bezier(0.16, 1, 0.3, 1) ${i + delay}s`,
  });

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        height: "100vh",
        background: "var(--void)",
        position: "relative",
        overflow: "hidden",
      }}
    >
      {/* Ambient radial glow */}
      <div
        style={{
          position: "absolute",
          width: "600px",
          height: "600px",
          borderRadius: "50%",
          background: "radial-gradient(circle, var(--cwi-soft) 0%, transparent 65%)",
          top: "50%",
          left: "50%",
          transform: "translate(-50%, -50%)",
          opacity: mounted ? 1 : 0,
          transition: "opacity 1.5s var(--ease-out)",
          pointerEvents: "none",
        }}
      />

      {/* Subtle grid texture */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          backgroundImage: `
            linear-gradient(rgba(255,255,255,0.02) 1px, transparent 1px),
            linear-gradient(90deg, rgba(255,255,255,0.02) 1px, transparent 1px)
          `,
          backgroundSize: "40px 40px",
          opacity: 0.3,
          pointerEvents: "none",
        }}
      />

      {/* Content */}
      <div style={{ textAlign: "center", zIndex: 1, maxWidth: "480px", padding: "var(--s7)" }}>
        {/* CWI Logo */}
        <div
          style={{
            ...anim(0, 0),
            fontSize: "80px",
            fontWeight: 800,
            color: "var(--cwi)",
            letterSpacing: "-0.04em",
            lineHeight: 1,
            marginBottom: "var(--s4)",
            textShadow: "0 0 60px var(--cwi-glow)",
          }}
        >
          CWI
        </div>

        {/* Title */}
        <div
          style={{
            ...anim(0.1, 1),
            fontSize: "16px",
            color: "var(--ink)",
            fontWeight: 500,
            letterSpacing: "0.04em",
            marginBottom: "var(--s3)",
          }}
        >
          Caption With Intention
        </div>

        {/* Subtitle */}
        <p
          style={{
            ...anim(0.2, 2),
            fontSize: "13px",
            color: "var(--muted)",
            lineHeight: 1.7,
            maxWidth: "380px",
            margin: "0 auto var(--s7)",
          }}
        >
          Transform closed captions into an expressive, accessible experience.
          <br />
          <span style={{ color: "var(--ghost)", fontSize: "12px" }}>
            Built for the Deaf and hard-of-hearing community.
          </span>
        </p>

        {/* CTA Buttons */}
        <div
          style={{
            ...anim(0.3, 3),
            display: "flex",
            flexDirection: "column",
            gap: "var(--s3)",
            alignItems: "center",
          }}
        >
          <button
            className="primary"
            onClick={onNewProject}
            style={{
              padding: "var(--s3) var(--s7)",
              fontSize: "13px",
              letterSpacing: "0.04em",
              animation: mounted ? "glowPulse 3s ease-in-out 1.5s infinite" : "none",
            }}
          >
            New Project
          </button>
          <button
            className="ghost"
            onClick={onOpen}
            style={{ padding: "var(--s2) var(--s5)", fontSize: "12px" }}
          >
            Open Project
          </button>
        </div>

        {/* Footer */}
        <div
          style={{
            ...anim(0.5, 4),
            marginTop: "var(--s8)",
            fontSize: "10px",
            color: "var(--ghost)",
            letterSpacing: "0.1em",
            textTransform: "uppercase",
          }}
        >
          v2.0 — Open Source
        </div>
      </div>
    </div>
  );
}

/* ────────────────────────────────────────────────
   MAIN APP — Professional NLE Layout
   ──────────────────────────────────────────────── */
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

  const [showWelcome, setShowWelcome] = useState(false);
  const [activePanel, setActivePanel] = useState<ActivePanel>("events");
  const [selectedEventId, setSelectedEventId] = useState<string | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);
  const [loading, setLoading] = useState(true);
  const [projectName, setProjectName] = useState("Untitled Project");
  const [saved, setSaved] = useState(true);
  const [projectSummary, setProjectSummary] = useState<{ success: boolean; data: Record<string, any> }>({ success: false, data: {} });
  const [toast, setToast] = useState<string | null>(null);

  const forceRefresh = useCallback(() => setRefreshKey((k) => k + 1), []);

  const showToast = useCallback((msg: string) => {
    setToast(msg);
    setTimeout(() => setToast(null), 2400);
  }, []);

  useEffect(() => {
    const visited = localStorage.getItem("cwi-welcome-dismissed");
    if (!visited) setShowWelcome(true);
    setLoading(false);

    api.getProjectSummary().then((r: any) => {
      if (r?.success) {
        setProjectSummary(r);
        if (r.data?.project_name) setProjectName(r.data.project_name);
      }
    }).catch(() => setLoading(false));
  }, [api]);

  const handleNewProject = () => {
    setShowWelcome(false);
    localStorage.setItem("cwi-welcome-dismissed", "1");
    setProjectName("Untitled Project");
    setSaved(false);
    showToast("New project created");
  };

  const handleOpen = () => {
    setShowWelcome(false);
    localStorage.setItem("cwi-welcome-dismissed", "1");
    showToast("Opening project...");
  };

  if (loading) {
    return (
      <div className="loading" style={{ height: "100vh", background: "var(--void)" }}>
        <span style={{ letterSpacing: "0.2em" }}>LOADING</span>
      </div>
    );
  }

  if (showWelcome) {
    return <WelcomeScreen onNewProject={handleNewProject} onOpen={handleOpen} />;
  }

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        height: "100vh",
        overflow: "hidden",
        background: "var(--deep)",
      }}
    >
      {/* ── Header ── */}
      <header
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "var(--s2) var(--s5)",
          background: "var(--glass-bg)",
          backdropFilter: "blur(16px)",
          WebkitBackdropFilter: "blur(16px)",
          borderBottom: "1px solid var(--border)",
          height: "48px",
          flexShrink: 0,
          zIndex: 10,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "var(--s3)" }}>
          <span
            style={{
              fontSize: "14px",
              fontWeight: 800,
              color: "var(--cwi)",
              letterSpacing: "-0.03em",
              lineHeight: 1,
              textShadow: "0 0 12px var(--cwi-soft)",
            }}
          >
            CWI
          </span>

          <div style={{ width: "1px", height: "16px", background: "var(--border-2)" }} />

          <input
            value={projectName}
            onChange={(e) => { setProjectName(e.target.value); setSaved(false); }}
            style={{
              background: "transparent",
              border: "1px solid transparent",
              color: "var(--ink)",
              fontSize: "13px",
              fontWeight: 500,
              width: "180px",
              padding: "2px 6px",
              borderRadius: "var(--r1)",
              transition: "all var(--t-fast)",
            }}
            onFocus={(e) => { e.target.style.background = "var(--input)"; e.target.style.borderColor = "var(--border-2)"; }}
            onBlur={(e) => { e.target.style.background = "transparent"; e.target.style.borderColor = "transparent"; }}
            title="Project name"
          />

          {projectSummary.data?.video_info?.duration > 0 && (
            <span
              className="font-mono"
              style={{ fontSize: "10px", color: "var(--muted)", padding: "2px 6px", background: "var(--input)", borderRadius: "var(--r1)" }}
            >
              {formatDuration(projectSummary.data.video_info.duration)}
            </span>
          )}
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "var(--s4)", fontSize: "11px" }}>
          <span style={{ color: saved ? "var(--muted)" : "var(--warn)", display: "flex", alignItems: "center", gap: "var(--s2)" }}>
            <span
              style={{
                width: "5px",
                height: "5px",
                borderRadius: "50%",
                background: saved ? "var(--ok)" : "var(--warn)",
                display: "inline-block",
                animation: saved ? "none" : "pulse 1.5s infinite",
              }}
            />
            {saved ? "Saved" : "Unsaved"}
          </span>

          <span
            style={{
              color: "var(--muted)",
              fontSize: "11px",
              display: "flex",
              alignItems: "center",
              gap: "var(--s2)",
            }}
          >
            <span className="font-mono" style={{ background: "var(--input)", padding: "2px 6px", borderRadius: "var(--r1)", fontSize: "10px" }}>
              {projectSummary.data?.speaker_count ?? 0} speakers
            </span>
            <span className="font-mono" style={{ background: "var(--input)", padding: "2px 6px", borderRadius: "var(--r1)", fontSize: "10px" }}>
              {projectSummary.data?.event_count ?? 0} events
            </span>
          </span>
        </div>
      </header>

      {/* ── Toolbar ── */}
      <Toolbar api={api} onAction={forceRefresh} showToast={showToast} />

      {/* ── Main ── */}
      <div style={{ display: "flex", flex: 1, overflow: "hidden" }}>
        {/* Sidebar */}
        <aside
          style={{
            width: "250px",
            minWidth: "250px",
            borderRight: "1px solid var(--border)",
            display: "flex",
            flexDirection: "column",
            background: "var(--base)",
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

          <div style={{ flex: 1, overflow: "auto", padding: "var(--s4)" }}>
            {activePanel === "speakers" && (
              <SpeakerPanel api={api} onAction={forceRefresh} key={refreshKey} />
            )}
            {activePanel === "events" && (
              <EventList
                api={api}
                selectedEventId={selectedEventId}
                onSelectEvent={(id) => { setSelectedEventId(id); }}
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
              <div className="empty-state">
                <span className="empty-state-icon">∅</span>
                <span>Select an event<br />to inspect properties</span>
              </div>
            )}
          </div>
        </aside>

        {/* Center */}
        <main style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>
          <div style={{ padding: "var(--s4)", overflow: "auto", flex: 1 }}>
            <Timeline api={api} onAction={forceRefresh} key={refreshKey} />

            {activePanel === "events" && (
              <EventEditor
                api={api}
                selectedEventId={selectedEventId}
                onSelectEvent={(id) => { setSelectedEventId(id); }}
                onAction={forceRefresh}
                key={refreshKey}
              />
            )}
          </div>
        </main>
      </div>

      {/* Toast */}
      {toast && (
        <div className="toast">{toast}</div>
      )}
    </div>
  );
}

function formatDuration(s: number): string {
  const m = Math.floor(s / 60);
  const sec = Math.floor(s % 60);
  const ms = Math.floor((s % 1) * 100);
  return `${m}:${String(sec).padStart(2, "0")}:${String(ms).padStart(2, "0")}`;
}
