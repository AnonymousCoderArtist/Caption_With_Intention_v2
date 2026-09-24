import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { gsap } from "gsap";
import { EditorApiClient } from "@/api/client";
import { DemoClient } from "@/lib/demoProject";
import type { Project, CaptionEvent, Word, Style } from "@/types/project";
import { WelcomeScreen } from "@/components/WelcomeScreen";
import { TopBar } from "@/components/TopBar";
import { Toolbar } from "@/components/Toolbar";
import { PreviewMonitor, Transport } from "@/components/PreviewMonitor";
import { Timeline } from "@/components/Timeline";
import { EventList } from "@/components/EventList";
import { SpeakerPanel } from "@/components/SpeakerPanel";
import { InspectorPanel } from "@/components/InspectorPanel";
import { Toast } from "@/components/Toast";

type ActivePanel = "events" | "speakers";

function withTimeout<T>(p: Promise<T>, ms: number): Promise<T> {
  return new Promise((res, rej) => {
    const t = setTimeout(() => rej(new Error("timeout")), ms);
    p.then(
      (v) => {
        clearTimeout(t);
        res(v);
      },
      (e) => {
        clearTimeout(t);
        rej(e);
      },
    );
  });
}

export function App() {
  /* ── client (live backend, else demo) ── */
  const clientRef = useRef<EditorApiClient | DemoClient | null>(null);
  const [source, setSource] = useState<"live" | "demo">("demo");

  const ensureClient = useCallback(async () => {
    if (clientRef.current) return clientRef.current;
    const live = new EditorApiClient(async (action, params) => {
      const res = await fetch(`/api/${action}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: params ? JSON.stringify(params) : "{}",
      });
      if (!res.ok) throw new Error("api " + res.status);
      return res.json();
    });
    try {
      const r: any = await withTimeout(live.getProject(), 2500);
      if (r?.success && r.data) {
        clientRef.current = live;
        setSource("live");
        return live;
      }
    } catch {
      /* fall through to demo */
    }
    clientRef.current = new DemoClient();
    setSource("demo");
    return clientRef.current;
  }, []);

  /* ── state ── */
  const [started, setStarted] = useState(false);
  const [project, setProject] = useState<Project | null>(null);
  const [projectName, setProjectName] = useState("Untitled Project");
  const [activePanel, setActivePanel] = useState<ActivePanel>("events");
  const [selectedEventId, setSelectedEventId] = useState<string | null>(null);
  const [time, setTime] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [toast, setToast] = useState<{ msg: string; kind: "success" | "error" } | null>(null);
  const toastTimer = useRef<number | undefined>(undefined);
  const clipboardRef = useRef<Style | null>(null);
  const shellRef = useRef<HTMLDivElement>(null);

  const duration = project?.video.duration ?? 0;
  const fps = project?.video.fps ?? 23.976;
  const stats = useMemo(
    () => ({ speakers: project?.speakers.length ?? 0, events: project?.events.length ?? 0 }),
    [project],
  );
  const selectedEvent = useMemo(
    () => project?.events.find((e) => e.id === selectedEventId) ?? null,
    [project, selectedEventId],
  );

  const showToast = useCallback((msg: string, kind: "success" | "error" = "success") => {
    setToast({ msg, kind });
    window.clearTimeout(toastTimer.current);
    toastTimer.current = window.setTimeout(() => setToast(null), 2600);
  }, []);

  /* ── data load / mutations ── */
  const reload = useCallback(async () => {
    const c = clientRef.current;
    if (!c) return;
    try {
      const r: any = await c.getProject();
      if (r?.success) setProject(r.data);
    } catch {
      /* ignore */
    }
  }, []);

  const act = useCallback(
    async (fn: () => Promise<any>, okMsg?: string, okKind: "success" | "error" = "success") => {
      try {
        const c = clientRef.current;
        if (!c) return;
        const r = await fn();
        if (r?.success) {
          if (okMsg) showToast(okMsg, okKind);
          await reload();
        }
      } catch {
        showToast("Something went wrong", "error");
      }
    },
    [reload, showToast],
  );

  const start = useCallback(
    async (isNew: boolean) => {
      const c = await ensureClient();
      setStarted(true);
      try {
        const r: any = await c.getProject();
        if (r?.success && r.data) {
          setProject(r.data);
          setProjectName(r.data.project_name || "Untitled Project");
        }
      } catch {
        /* ignore */
      }
      if (isNew && (clientRef.current as DemoClient)?.source === "demo") {
        showToast("New project created");
      }
    },
    [ensureClient, showToast],
  );

  /* mutations */
  const updateEvent = useCallback(
    (id: string, updates: Partial<CaptionEvent>) => act(() => clientRef.current!.updateEvent(id, updates)),
    [act],
  );
  const updateStyle = useCallback(
    (id: string, updates: Record<string, any>) => act(() => clientRef.current!.setTypography(id, updates as any)),
    [act],
  );
  const deleteEvent = useCallback(
    (id: string) => {
      act(() => clientRef.current!.removeEvent(id), "Event deleted");
      setSelectedEventId((cur) => (cur === id ? null : cur));
    },
    [act],
  );
  const deleteSpeaker = useCallback(
    (id: string) => act(() => clientRef.current!.removeSpeaker(id), "Speaker removed"),
    [act],
  );
  const speakerColor = useCallback(
    (id: string, color: string) => act(() => clientRef.current!.updateSpeaker(id, { color })),
    [act],
  );
  const speakerCategory = useCallback(
    (id: string, category: string) => act(() => clientRef.current!.updateSpeaker(id, { category: category as any })),
    [act],
  );

  const addEvent = useCallback(async () => {
    const c = clientRef.current;
    if (!c) return;
    const s = Math.round(time * 100) / 100;
    const e = Math.round((time + 2) * 100) / 100;
    const r: any = await c.addEvent({ text: "", start: s, end: e, event_type: "dialogue" });
    if (r?.success) {
      await reload();
      setSelectedEventId(r.data?.id);
      setActivePanel("events");
    }
  }, [time, reload]);

  const addSpeaker = useCallback(async () => {
    const c = clientRef.current;
    if (!c) return;
    const palette = ["#E5E517", "#17E5E5", "#E51717", "#E58017", "#17E517", "#E517E5"];
    const color = palette[stats.speakers % palette.length];
    const r: any = await c.addSpeaker({
      name: `Speaker ${stats.speakers + 1}`,
      category: "main",
      color,
    });
    if (r?.success) {
      await reload();
      setActivePanel("speakers");
      showToast("Speaker added");
    }
  }, [stats.speakers, reload, showToast]);

  const addWord = useCallback(
    async (id: string) => {
      const c = clientRef.current;
      const e = project?.events.find((x) => x.id === id);
      if (!c || !e) return;
      const lastEnd = e.words.length ? e.words[e.words.length - 1].end : e.end;
      const s = lastEnd;
      const en = Math.min(e.end, lastEnd + 0.4);
      await c.addWord(id, "word", s, Math.max(en, s + 0.2));
      await reload();
    },
    [project, reload],
  );
  const updateWord = useCallback(
    (id: string, idx: number, updates: Partial<Word>) => act(() => clientRef.current!.updateWord(id, idx, updates)),
    [act],
  );
  const removeWord = useCallback(
    (id: string, idx: number) => act(() => clientRef.current!.removeWord(id, idx)),
    [act],
  );

  const undo = useCallback(() => act(() => clientRef.current!.undo()), [act]);
  const redo = useCallback(() => act(() => clientRef.current!.redo()), [act]);

  const copyStyle = useCallback(() => {
    if (!selectedEvent) return showToast("Select an event to copy its style");
    clientRef.current?.copyStyle(selectedEvent.id).then((r: any) => {
      if (r?.success) {
        clipboardRef.current = r.data.copied_style;
        showToast("Style copied");
      }
    });
  }, [selectedEvent, showToast]);
  const pasteStyle = useCallback(() => {
    if (!selectedEvent || !clipboardRef.current) return showToast("Nothing to paste yet");
    act(() => clientRef.current!.setTypography(selectedEvent.id, clipboardRef.current as any), "Style pasted");
  }, [selectedEvent, act, showToast]);

  /* ── playback ── */
  const togglePlay = useCallback(() => {
    setPlaying((p) => {
      if (!p) setTime((t) => (t >= duration - 0.05 ? 0 : t));
      return !p;
    });
  }, [duration]);

  useEffect(() => {
    if (!playing) return;
    let raf = 0;
    let last = performance.now();
    const tick = (now: number) => {
      const dt = (now - last) / 1000;
      last = now;
      setTime((t) => {
        const nt = t + dt;
        if (nt >= duration) {
          setPlaying(false);
          return duration;
        }
        return nt;
      });
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [playing, duration]);

  const scrub = useCallback((t: number) => {
    setPlaying(false);
    setTime(Math.min(duration, Math.max(0, t)));
  }, [duration]);
  const step = useCallback(
    (dir: -1 | 1) => {
      setPlaying(false);
      setTime((t) => Math.min(duration, Math.max(0, t + dir / fps)));
    },
    [duration, fps],
  );
  const skip = useCallback(
    (dir: "start" | "end") => {
      setPlaying(false);
      setTime(dir === "start" ? 0 : duration);
    },
    [duration],
  );

  /* ── keyboard shortcuts ── */
  useEffect(() => {
    if (!started) return;
    const onKey = (e: KeyboardEvent) => {
      const el = e.target as HTMLElement;
      if (el.tagName === "INPUT" || el.tagName === "TEXTAREA" || el.tagName === "SELECT" || el.isContentEditable)
        return;
      if (e.code === "Space") {
        e.preventDefault();
        togglePlay();
      } else if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "z") {
        e.preventDefault();
        if (e.shiftKey) redo();
        else undo();
      } else if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "y") {
        e.preventDefault();
        redo();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [started, togglePlay, undo, redo]);

  /* ── entrance animation on entering the editor ── */
  useEffect(() => {
    if (!started) return;
    const el = shellRef.current;
    if (!el) return;
    const ctx = gsap.context(() => {
      gsap.fromTo(".topbar", { y: -18, opacity: 0 }, { y: 0, opacity: 1, duration: 0.5, ease: "power3.out" });
      gsap.fromTo(".toolbar", { y: -14, opacity: 0 }, { y: 0, opacity: 1, duration: 0.5, ease: "power3.out", delay: 0.06 });
      gsap.fromTo(
        [".sidebar", ".inspector"],
        { y: 22, opacity: 0 },
        { y: 0, opacity: 1, duration: 0.55, ease: "power3.out", stagger: 0.08, delay: 0.14 },
      );
      gsap.fromTo(".center", { opacity: 0, scale: 0.99 }, { opacity: 1, scale: 1, duration: 0.6, ease: "power3.out", delay: 0.1 });
    }, el);
    return () => ctx.revert();
  }, [started]);

  /* ── render ── */
  if (!started) {
    return <WelcomeScreen onNew={() => start(true)} onOpen={() => start(false)} />;
  }

  return (
    <div className="app-shell" ref={shellRef}>
      <TopBar
        projectName={projectName}
        onRename={setProjectName}
        source={source}
        stats={stats}
        video={project?.video ? { width: project.video.width, height: project.video.height, fps: project.video.fps } : undefined}
        onExit={() => setStarted(false)}
      />

      <Toolbar
        onUndo={undo}
        onRedo={redo}
        onAddEvent={addEvent}
        onAddSpeaker={addSpeaker}
        onSelectAll={() => act(() => clientRef.current!.selectAll())}
        onClearSelection={() => {
          act(() => clientRef.current!.clearSelection());
          setSelectedEventId(null);
        }}
        onCopyStyle={copyStyle}
        onPasteStyle={pasteStyle}
        onExport={() => showToast("Export pipeline coming soon")}
        onSettings={() => showToast("Settings coming soon")}
      />

      <div className="workspace">
        {/* left browser */}
        <aside className="sidebar">
          <div className="panel-tabs">
            <button className={`panel-tab ${activePanel === "events" ? "active" : ""}`} onClick={() => setActivePanel("events")}>
              Events
            </button>
            <button className={`panel-tab ${activePanel === "speakers" ? "active" : ""}`} onClick={() => setActivePanel("speakers")}>
              Speakers
            </button>
          </div>
          <div className="scroll">
            {activePanel === "events" ? (
              <EventList
                events={project?.events ?? []}
                speakers={project?.speakers ?? []}
                selectedEventId={selectedEventId}
                onSelect={setSelectedEventId}
                onDelete={deleteEvent}
                onNew={addEvent}
              />
            ) : (
              <SpeakerPanel
                speakers={project?.speakers ?? []}
                onAdd={async (p) => {
                  const c = clientRef.current;
                  if (!c) return;
                  const r: any = await c.addSpeaker(p);
                  if (r?.success) await reload();
                }}
                onDelete={deleteSpeaker}
                onColor={speakerColor}
                onCategory={speakerCategory}
              />
            )}
          </div>
        </aside>

        {/* center: preview + transport + timeline */}
        <main className="center">
          <PreviewMonitor project={project} time={time} fps={fps} />
          <Transport
            time={time}
            duration={duration}
            playing={playing}
            fps={fps}
            onToggle={togglePlay}
            onScrub={scrub}
            onStep={step}
            onSkip={skip}
          />
          <div style={{ flexShrink: 0, height: 250, padding: "0 16px 14px" }}>
            <Timeline
              project={project}
              selectedEventId={selectedEventId}
              time={time}
              onSelectEvent={setSelectedEventId}
              onScrub={scrub}
            />
          </div>
        </main>

        {/* right inspector */}
        <aside className="inspector">
          <InspectorPanel
            event={selectedEvent}
            speakers={project?.speakers ?? []}
            onUpdateEvent={updateEvent}
            onUpdateStyle={updateStyle}
            onAddWord={addWord}
            onUpdateWord={updateWord}
            onRemoveWord={removeWord}
          />
        </aside>
      </div>

      {toast && <Toast message={toast.msg} kind={toast.kind} />}
    </div>
  );
}
