import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { EditorApiClient } from "@/api/client";
import { DemoClient } from "@/lib/demoProject";
import { emptyProject, parseProject, STORAGE_KEY } from "@/lib/projectFile";
import type { Project, CaptionEvent, Word, Style } from "@/types/project";
import { WelcomeScreen } from "@/components/WelcomeScreen";
import { TopBar } from "@/components/TopBar";
import { Toolbar } from "@/components/Toolbar";
import { PreviewMonitor, Transport } from "@/components/PreviewMonitor";
import { Timeline } from "@/components/Timeline";
import { EventList } from "@/components/EventList";
import { SpeakerPanel } from "@/components/SpeakerPanel";
import { InspectorPanel } from "@/components/InspectorPanel";
import {speakerReviewReasons} from "@/lib/speakerReview";
import { RenderPanel } from "@/components/RenderPanel";
import { DraftNumber } from "@/components/DraftNumber";
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
  const editQueue = useRef<Promise<any>>(Promise.resolve());
  const sessionVersion = useRef(0);
  const reloadVersion = useRef(0);
  const [source, setSource] = useState<"live" | "demo">("demo");

  const ensureClient = useCallback(async () => {
    if (clientRef.current) return clientRef.current;
    // A local editing session must not disappear just because the API is up.
    try {
      const saved=localStorage.getItem(STORAGE_KEY);
      if(saved){clientRef.current=new DemoClient(parseProject(saved));setSource('demo');return clientRef.current;}
    } catch { /* unavailable or malformed local data can fall back to the API */ }
    const openingVersion=sessionVersion.current;
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
      if(openingVersion!==sessionVersion.current&&clientRef.current)return clientRef.current;
      if (r?.success && r.data) {
        clientRef.current = live;
        setSource("live");
        return live;
      }
    } catch {
      /* fall through to demo */
    }
    if(openingVersion!==sessionVersion.current&&clientRef.current)return clientRef.current;
    let local: Project | undefined;
    try { const saved = localStorage.getItem(STORAGE_KEY); if (saved) local = parseProject(saved); } catch { /* old or unavailable local storage */ }
    clientRef.current = new DemoClient(local);
    setSource("demo");
    return clientRef.current;
  }, []);

  /* ── state ── */
  const [started, setStarted] = useState(false);
  const [project, setProject] = useState<Project | null>(null);
  const [projectName, setProjectName] = useState("Untitled Project");
  const [mobilePanel, setMobilePanel] = useState<'events'|'preview'|'properties'>('preview');
  const [workspace,setWorkspace]=useState('Edit');
  const [lightPreview,setLightPreview]=useState(false);
  const [activePanel, setActivePanel] = useState<ActivePanel>("events");
  const [selectedEventId, setSelectedEventId] = useState<string | null>(null);
  const [selectedIds,setSelectedIds]=useState<string[]>([]);
  const [batchDelta,setBatchDelta]=useState(1);
  const [selectionExpanded,setSelectionExpanded]=useState(()=>window.innerWidth>1000);
  useEffect(()=>{const media=window.matchMedia('(min-width:1001px)');const changed=()=>setSelectionExpanded(media.matches);media.addEventListener('change',changed);return()=>media.removeEventListener('change',changed);},[]);
  const [batchSpeaker,setBatchSpeaker]=useState('');
  const auditionEnd=useRef<number|null>(null);
  const [ripple,setRipple]=useState(false);
  const [time, setTime] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [toast, setToast] = useState<{ msg: string; kind: "success" | "error" } | null>(null);
  const toastTimer = useRef<number | undefined>(undefined);
  const clipboardRef = useRef<Style | null>(null);
  const shellRef = useRef<HTMLDivElement>(null);
  const mediaInputRef = useRef<HTMLInputElement>(null);
  const projectInputRef = useRef<HTMLInputElement>(null);
  const [saveError, setSaveError] = useState(false);
  const [showProjectSettings, setShowProjectSettings] = useState(false);
  const [mediaUrl, setMediaUrl] = useState<string | null>(null);
  const [mediaName, setMediaName] = useState('');
  const [sourceFile,setSourceFile]=useState<File|null>(null);
  const [showRender,setShowRender]=useState(false);
  const renderActive=useRef(false);
  const onRenderActive=useCallback((active:boolean)=>{renderActive.current=active;},[]);
  const [mediaDuration, setMediaDuration] = useState<number | null>(null);
  useEffect(() => () => { if (mediaUrl) URL.revokeObjectURL(mediaUrl); }, [mediaUrl]);

  const duration = Math.max(mediaDuration ?? 0, project?.video.duration ?? 0, ...((project?.events ?? []).map(e=>e.end)));
  const fps = project?.video.fps ?? 23.976;
  const stats = useMemo(
    () => ({ speakers: project?.speakers.length ?? 0, events: project?.events.length ?? 0 }),
    [project],
  );
  useEffect(()=>{setSelectedIds(current=>current.filter(id=>project?.events.some(e=>e.id===id)));},[project]);
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
    const version = sessionVersion.current;
    const requestVersion = ++reloadVersion.current;
    try {
      const r: any = await c.getProject();
      if (version !== sessionVersion.current || requestVersion !== reloadVersion.current) return;
      if (r?.success) { setProject(r.data); setProjectName(r.data.project_name || "Untitled Project"); }
    } catch {
      /* ignore */
    }
  }, []);

  const act = useCallback(
    async (fn: () => Promise<any>, okMsg?: string, okKind: "success" | "error" = "success") => {
      try {
        const c = clientRef.current;
        if (!c) return;
        const version = sessionVersion.current;
        const guarded = () => version === sessionVersion.current ? fn() : Promise.resolve({success:false,error:'Project changed before the edit could apply.'});
        const operation = editQueue.current.then(guarded, guarded);
        editQueue.current = operation.catch(() => undefined);
        const r = await operation;
        if (version !== sessionVersion.current) return;
        if (r?.success) {
          if (okMsg) showToast(okMsg, okKind);
          await reload();
          return r;
        } else {
          showToast(r?.error || "Edit was not applied", "error");
        }
      } catch {
        showToast("Edit failed. Check the connection and try again.", "error");
      }
    },
    [reload, showToast],
  );

  const start = useCallback(
    async (isNew: boolean) => {
      if(renderActive.current){showToast('Finish or cancel the active render before changing projects.', 'error');return;}
      if (isNew && project && (project.events.length || project.speakers.length) && !window.confirm('Start a new local project? Save the current project JSON first if you want to keep it.')) return;
      if (isNew) {
        sessionVersion.current++; clientRef.current = new DemoClient(emptyProject()); setSource('demo');
        setSelectedEventId(null); setSelectedIds([]); setTime(0); setPlaying(false);
        setMediaUrl(null); setSourceFile(null); setMediaName(''); setMediaDuration(null);
        setWorkspace('Edit');setShowProjectSettings(false);setShowRender(false); clipboardRef.current = null; auditionEnd.current=null;
      }
      const c = await ensureClient();
      const version=sessionVersion.current;
      setStarted(true);
      try {
        const r: any = await c.getProject();
        if(version!==sessionVersion.current)return;
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
    [ensureClient, showToast, project],
  );

  useEffect(() => {
    if (!project || source !== 'demo') return;
    const timer = setTimeout(() => {
      try { localStorage.setItem(STORAGE_KEY, JSON.stringify({...project,project_name:projectName})); setSaveError(false); }
      catch { setSaveError(true); }
    }, 300);
    return () => clearTimeout(timer);
  }, [project, projectName, source]);

  const importProject = async (file: File) => {
    try {
      if (file.size > 20 * 1024 * 1024) throw new Error('Choose a project smaller than 20 MB.');
      const data = parseProject(await file.text());
      if(renderActive.current){showToast('Finish or cancel the active render before changing projects.', 'error');return;}
      if (project && (project.events.length || project.speakers.length) && !window.confirm('Replace the current editing session? Save its project JSON first if you want to keep it.')) return;
      sessionVersion.current++;
      clientRef.current = new DemoClient(data); setSource('demo'); setProject(data);
      setProjectName(data.project_name); setSelectedEventId(null); setSelectedIds([]); setTime(0); setPlaying(false); setStarted(true);
      setMediaUrl(null); setSourceFile(null); setMediaName(''); setMediaDuration(null);
      setWorkspace('Edit');setShowProjectSettings(false);setShowRender(false);clipboardRef.current=null;auditionEnd.current=null;
      showToast('Project opened locally. Import its video separately.');
    } catch (error) { showToast(error instanceof Error ? error.message : 'Could not open project.', 'error'); }
  };

  /* mutations */
  const updateEvent = useCallback(
    (id: string, updates: Partial<CaptionEvent>) => act(() => clientRef.current!.updateEvent(id, updates)),
    [act],
  );
  const updateStyle = useCallback(
    (id: string, updates: Record<string, any>) => act(() => clientRef.current!.setStyle(id, updates)),
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
    const r: any = await act(() => c.addEvent({ text: "", start: s, end: e, event_type: "dialogue" }));
    if (r?.success) {
      await reload();
      setSelectedEventId(r.data?.id);
      setActivePanel("events");
    }
  }, [time, reload, act]);

  const addSpeaker = useCallback(async () => {
    const c = clientRef.current;
    if (!c) return;
    const palette = ["#E5E517", "#17E5E5", "#E51717", "#E58017", "#17E517", "#E517E5"];
    const color = palette[stats.speakers % palette.length];
    const r: any = await act(() => c.addSpeaker({
      name: `Speaker ${stats.speakers + 1}`,
      category: "main",
      color,
    }));
    if (r?.success) {
      await reload();
      setActivePanel("speakers");
      showToast("Speaker added");
    }
  }, [stats.speakers, reload, showToast, act]);

  const addWord = useCallback(
    async (id: string) => {
      const c = clientRef.current;
      const e = project?.events.find((x) => x.id === id);
      if (!c || !e) return;
      const lastEnd = e.words.length ? e.words[e.words.length - 1].end : e.start;
      if (e.end - lastEnd < .05) return showToast('No room after the last word. Extend the event first.', 'error');
      await act(() => c.addWord(id, "word", lastEnd, Math.min(e.end, lastEnd + .4)));
    },
    [project, act, showToast],
  );
  const updateWord = useCallback(
    (id: string, idx: number, updates: Partial<Word>) => act(() => clientRef.current!.updateWord(id, idx, {manual_override:true,...updates})),
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
    updateStyle(selectedEvent.id, clipboardRef.current as any);
  }, [selectedEvent, updateStyle, showToast]);

  /* ── playback ── */
  const togglePlay = useCallback(() => {
    setPlaying((p) => {
      if (!p) setTime((t) => (t >= duration - 0.05 ? 0 : t));
      return !p;
    });
  }, [duration]);

  useEffect(() => {
    if (!playing || mediaUrl) return;
    let raf = 0;
    let last = performance.now();
    const tick = (now: number) => {
      if(now-last<(lightPreview?1000/15:1000/30)){raf=requestAnimationFrame(tick);return;}
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
  }, [playing, duration, mediaUrl,lightPreview]);

  const scrub = useCallback((t: number) => {
    auditionEnd.current=null;
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

  const selectEvent = useCallback((id: string,additive=false) => {
    setSelectedIds(current=>additive?current.includes(id)?current.filter(x=>x!==id):[...current,id]:[id]);
    setSelectedEventId(id);
    const event = project?.events.find(e=>e.id===id);
    if (event && (time < event.start || time >= event.end)) {
      setPlaying(false); setTime(event.start + Math.min(.06,(event.end-event.start)/2));
    }
  }, [project,time]);

  useEffect(()=>{if(auditionEnd.current!==null&&time>=auditionEnd.current){setPlaying(false);auditionEnd.current=null;}},[time]);

  /* ── keyboard shortcuts ── */
  useEffect(() => {
    if (!started) return;
    const onKey = (e: KeyboardEvent) => {
      const el = e.target as HTMLElement;
      if(el.closest('.render-panel'))return;
      if(e.code==='Space'&&el.closest('button,a,[role="button"]'))return;
      if (el.tagName === "INPUT" || el.tagName === "TEXTAREA" || el.tagName === "SELECT" || el.isContentEditable)
        return;
      if (e.code === "Space") {
        e.preventDefault();
        togglePlay();
      } else if (e.key === 'ArrowLeft' || e.key === 'ArrowRight') {
        e.preventDefault(); step(e.key === 'ArrowLeft' ? -1 : 1);
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
  }, [started, togglePlay, undo, redo, step]);

  const snapshotProject = useCallback(async () => {
    const version = sessionVersion.current;
    const client = clientRef.current;
    await editQueue.current;
    if (version !== sessionVersion.current) throw new Error('Project changed. Try again from the current project.');
    const response = await client?.getProject();
    if (version !== sessionVersion.current) throw new Error('Project changed. Try again from the current project.');
    if (!response?.success || !response.data) throw new Error('Could not read the latest project. Check the connection and try again.');
    return {...response.data, project_name: projectName};
  }, [projectName]);

  const exportProject = useCallback(async () => {
    try {
      const data = await snapshotProject();
      const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' }));
      const link = document.createElement('a'); link.href = url;
      link.download = `${data.project_name.replace(/[^a-z0-9_-]/gi, '_') || 'captions'}.cwi.json`;
      link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
      showToast('Project JSON downloaded. Use Render video to create an MP4.');
    } catch (error) {
      showToast(error instanceof Error ? error.message : 'Project could not be saved. Try again.', 'error');
    }
  }, [snapshotProject, showToast]);

  /* ── render ── */
  if (!started) {
    return <><WelcomeScreen onNew={() => start(true)} onOpen={() => start(false)} onImport={() => projectInputRef.current?.click()} />
      <input ref={projectInputRef} type="file" accept=".json" hidden aria-label="Open project JSON" onChange={e => {const f=e.target.files?.[0];if(f)void importProject(f);e.target.value='';}} />
      {toast && <Toast message={toast.msg} kind={toast.kind}/>}</>;
  }

  return (
    <div className="app-shell" ref={shellRef} data-mobile-panel={mobilePanel} data-workspace={workspace}>
      <input ref={projectInputRef} type="file" accept=".json" hidden aria-label="Open project JSON" onChange={e => {const f=e.target.files?.[0];if(f)void importProject(f);e.target.value='';}} />
      {saveError && <div className="save-warning" role="alert">Browser storage is full or unavailable. Save project JSON to keep your changes.</div>}
      <TopBar
        projectName={projectName}
        onRename={setProjectName}
        onRenameCommit={() => act(() => clientRef.current!.updateProject({project_name:projectName}))}
        source={source}
        localLabel={'Local project'}
        onOpenProject={() => projectInputRef.current?.click()}
        stats={stats}
        video={project?.video ? { width: project.video.width, height: project.video.height, fps: project.video.fps } : undefined}
        onExport={exportProject}
        onImportMedia={() => mediaInputRef.current?.click()}
        onExit={() => {if(renderActive.current){showToast('Finish or cancel the active render before leaving the editor.', 'error');return;} setPlaying(false); setStarted(false); }}
      />

      <nav className="workspace-tabs" aria-label="Editor workspaces">{['Edit','Text','Color','Speakers','Export'].map(tab=><button key={tab} aria-pressed={workspace===tab} onClick={()=>{setWorkspace(tab);if(tab==='Speakers')setActivePanel('speakers');if(tab==='Text'||tab==='Edit')setActivePanel('events');if(tab==='Export')setShowRender(true);else if(!renderActive.current)setShowRender(false);}}>{tab}</button>)}<label><input type="checkbox" checked={lightPreview} onChange={e=>setLightPreview(e.target.checked)}/> Lightweight preview (15 fps)</label></nav>
      {workspace==='Color'&&<section className="grade-panel" aria-label="Video color grading"><b>Video color</b>{(['brightness','contrast','saturation'] as const).map(key=><label key={key}>{key}<DraftNumber aria-label={`Video ${key}`} value={project?.video[key]??(key==='brightness'?0:1)} min={key==='brightness'?-.5:key==='contrast'?.5:0} max={key==='brightness'?.5:2} step={.05} onCommit={value=>act(()=>clientRef.current!.updateProject({video:{[key]:value}}))}/></label>)}<button onClick={()=>act(()=>clientRef.current!.updateProject({video:{brightness:0,contrast:1,saturation:1}}))}>Reset grade</button><small>Source video only. Captions stay unchanged. Browser grade is approximate; final MP4 uses FFmpeg.</small></section>}
      <Toolbar
        onUndo={undo}
        onRedo={redo}
        onAddEvent={addEvent}
        onAddSpeaker={addSpeaker}
        onSelectAll={() => act(() => clientRef.current!.selectAll())}
        onClearSelection={() => {
          act(() => clientRef.current!.clearSelection());
          setSelectedEventId(null);setSelectedIds([]);
        }}
        onCopyStyle={copyStyle}
        onPasteStyle={pasteStyle}
        onExport={exportProject}
        onSettings={() => setShowProjectSettings(v=>!v)}
        onRender={() => setShowRender(true)}
      />

      {showRender&&<RenderPanel onActiveChange={onRenderActive} source={sourceFile} onClose={()=>setShowRender(false)} getProject={snapshotProject}/>}
      <details className="batch-controls" open={selectionExpanded} onToggle={e=>setSelectionExpanded(e.currentTarget.open)}><summary>Caption selection · {selectedIds.length} selected</summary><div className="batch-bar" aria-label="Caption selection">
        <button className="subtle" onClick={()=>setSelectedIds(project?.events.map(e=>e.id)??[])}>Select all captions</button>
        <span>{selectedIds.length} selected · Shift/Ctrl-click to add</span><span className="batch-caveat">Caption timing only, source video stays fixed.</span>
        <label>Shift <DraftNumber aria-label="Selection shift seconds" value={batchDelta} min={-3600} max={3600} step={.1} onCommit={setBatchDelta}/> s</label>
        <label><input type="checkbox" checked={ripple} onChange={e=>setRipple(e.target.checked)}/> Ripple later captions</label>
        <label>Speaker <select aria-label="Selected captions speaker" value={batchSpeaker} onChange={e=>setBatchSpeaker(e.target.value)}><option value="">No speaker</option>{project?.speakers.map(s=><option key={s.id} value={s.id}>{s.name}</option>)}</select></label>
        <button className="ghost" disabled={!selectedIds.length} onClick={()=>act(()=>clientRef.current!.assignSpeakerEvents(selectedIds,batchSpeaker||null,true))}>Assign and check</button>
        <button className="ghost" disabled={selectedIds.length!==1} title="Place the playhead between timed words" onClick={()=>act(()=>clientRef.current!.structureEvents(selectedIds,'split',time),'Caption split at playhead')}>Split at playhead</button>
        <button className="ghost" disabled={selectedIds.length<2} title="Same speaker, style and type; no overlap" onClick={async()=>{const r=await act(()=>clientRef.current!.structureEvents(selectedIds,'merge'),'Captions merged');if(r){const first=project?.events.filter(e=>selectedIds.includes(e.id)).sort((a,b)=>a.start-b.start||a.end-b.end)[0]?.id;if(first){setSelectedIds([first]);setSelectedEventId(first);}}}}>Merge selected</button>
        <button className="ghost" disabled={!selectedIds.length} onClick={()=>act(()=>clientRef.current!.batchEvents(selectedIds,'move',batchDelta,ripple))}>Move selected</button>
        <button className="ghost" disabled={!selectedIds.length} onClick={async()=>{if(ripple&&!window.confirm('Delete selected captions and close their occupied time? Source video is unchanged.'))return;const result=await act(()=>clientRef.current!.batchEvents(selectedIds,'delete',0,ripple));if(result){setSelectedIds([]);setSelectedEventId(null);}}}>Delete selected</button>
      </div></details>
      <nav className="mobile-panels" aria-label="Editor panels">{(['events','preview','properties'] as const).map(panel=><button key={panel} aria-pressed={mobilePanel===panel} onClick={()=>setMobilePanel(panel)}>{panel}</button>)}</nav>
      {showProjectSettings && project && <section className="project-settings" aria-label="Project settings">
        <b>Sequence</b>
        {(['width','height','fps','duration'] as const).map(key=><label key={key}>{key}<DraftNumber aria-label={`Sequence ${key}`} min={key==='duration'?0:1} step={key==='fps'?.001:key==='duration'?.1:1} value={project.video[key]} onCommit={value=>{act(()=>clientRef.current!.updateProject({video:{[key]:value}}));}}/></label>)}
        <span>Space: play · arrows: frame · Ctrl/Cmd Z: undo</span>
        <button className="subtle" onClick={()=>setShowProjectSettings(false)}>Close</button>
      </section>}
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
              <EventList key={sessionVersion.current}
                events={project?.events ?? []}
                speakers={project?.speakers ?? []}
                selectedEventId={selectedEventId}
                selectedIds={selectedIds}
                onSelect={selectEvent}
                onDelete={deleteEvent}
                onNew={addEvent}
              />
            ) : (
              <SpeakerPanel key={sessionVersion.current}
                speakers={project?.speakers ?? []}
                onAdd={async (p) => {
                  const c = clientRef.current;
                  if (!c) return;
                  const r: any = await act(() => c.addSpeaker(p));
                  if (r?.success) await reload();
                }}
                onDelete={deleteSpeaker}
                onColor={speakerColor}
                onCategory={speakerCategory}
                onUpdate={(id,updates) => act(() => clientRef.current!.updateSpeaker(id,updates))}
              />
            )}
          </div>
        </aside>

        {/* center: preview + transport + timeline */}
        <main className="center">
          <input ref={mediaInputRef} type="file" accept="video/*" hidden aria-label="Import local video"
            onChange={e => { const file = e.target.files?.[0]; if (!file) return;
              setPlaying(false); setTime(0); setMediaDuration(null);
              setSourceFile(file); setMediaName(file.name); setMediaUrl(URL.createObjectURL(file)); e.target.value = '';
            }} />
          {mediaName && <div className="media-label">{mediaName} · local preview only <button className="subtle" onClick={() => { setMediaUrl(null); setSourceFile(null); setMediaName(''); setMediaDuration(null); setPlaying(false); }}>Remove video</button></div>}
          <PreviewMonitor lightweight={lightPreview} project={project} time={time} fps={fps} mediaUrl={mediaUrl} playing={playing}
            onMediaTime={setTime} onMediaDuration={setMediaDuration} onEnded={() => setPlaying(false)}
            selectedEventId={selectedEventId} onSelectEvent={selectEvent} />
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
          <div className="timeline-area" style={{ flexShrink: 0, height: 300, padding: "0 16px 14px" }}>
            <Timeline key={sessionVersion.current}
              project={project}
              selectedEventId={selectedEventId}
              selectedIds={selectedIds}
              time={time}
              onSelectEvent={selectEvent}
              onScrub={scrub}
              duration={duration}
              mediaName={mediaName}
              onUpdateEvent={updateEvent}
              ripple={ripple}
              onMoveSelection={(ids,delta)=>act(()=>clientRef.current!.batchEvents(ids,'move',delta,ripple))}
            />
          </div>
        </main>

        {/* right inspector */}
        <aside className="inspector">
          <InspectorPanel
            event={selectedEvent}
            speakers={project?.speakers ?? []}
            onUpdateEvent={updateEvent}
            onAudition={()=>{if(selectedEvent){setTime(Math.max(0,selectedEvent.start-.15));auditionEnd.current=selectedEvent.end+.15;setPlaying(true);}}}
            onNextSpeakerReview={()=>{const candidates=project?.events.filter(e=>speakerReviewReasons(e,project.speakers).length).sort((a,b)=>a.start-b.start)??[];const next=candidates.find(e=>e.start>(selectedEvent?.start??-1))??candidates[0];if(next)selectEvent(next.id);else showToast('No unchecked speaker turns remain.');}}
            hasMedia={!!mediaUrl}
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
