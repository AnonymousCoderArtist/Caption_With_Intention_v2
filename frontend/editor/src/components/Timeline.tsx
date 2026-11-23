/** Editable timeline. Ruler seeks, caption bodies move, edge handles trim. */
import { useEffect, useMemo, useRef, useState } from 'react';
import type { CaptionEvent, Project } from '@/types/project';
import { fmtTime, EVENT_TYPES, readableOn } from '@/lib/theme';
import { Icon } from '@/lib/icons';
import { speakerLanes,timelineTicks } from '@/lib/timelineLayout';
const HEAD_W = 100;
interface Props {
  project: Project | null; selectedEventId: string | null; selectedIds?:string[]; time: number;
  duration?: number; mediaName?: string;
  onSelectEvent: (id: string,additive?:boolean) => void; onScrub: (t: number) => void;
  onUpdateEvent: (id: string, updates: Partial<CaptionEvent>) => void;
  onMoveSelection?:(ids:string[],delta:number)=>void;
  ripple?:boolean;
}
export function Timeline({project, selectedEventId, time, onSelectEvent, onScrub,
  selectedIds, onMoveSelection,ripple, onUpdateEvent, duration: durationProp, mediaName}: Props) {
  const duration = durationProp ?? project?.video.duration ?? 0;
  const [ppx, setPpx] = useState(60);
  const [draft, setDraft] = useState<{id: string; start: number; end: number; mode?:string;ids?:string[]} | null>(null);
  const bodyRef = useRef<HTMLDivElement>(null);
  const stopPointer=useRef<(()=>void)|null>(null);
  useEffect(()=>()=>{stopPointer.current?.();},[]);
  const contentW = Math.max(400, duration * ppx) + HEAD_W;
  const selected = project?.events.find(e => e.id === selectedEventId);
  const ticks=useMemo(()=>timelineTicks(duration,ppx),[duration,ppx]);
  const lanes=useMemo(()=>speakerLanes(project?.events??[],project?.speakers??[]),[project]);
  useEffect(()=>{
    const body=bodyRef.current;if(!body)return;
    const x=HEAD_W+time*ppx,padding=30;
    if(x<body.scrollLeft+HEAD_W||x>body.scrollLeft+body.clientWidth-padding)
      body.scrollLeft=Math.max(0,x-HEAD_W-padding);
  },[time,ppx]);
  const seek = (clientX: number) => {
    const body = bodyRef.current; if (!body) return;
    const x = clientX - body.getBoundingClientRect().left + body.scrollLeft - HEAD_W;
    onScrub(Math.max(0, Math.min(duration, x / ppx)));
  };
  const drag = (ev: React.PointerEvent, event: CaptionEvent, mode: 'move' | 'start' | 'end') => {
    stopPointer.current?.();
    ev.stopPropagation(); ev.preventDefault(); if(ev.shiftKey||ev.ctrlKey||ev.metaKey){onSelectEvent(event.id,true);return;}
    const group = mode==='move' && selectedIds?.includes(event.id) ? selectedIds : [event.id];
    if(group.length===1)onSelectEvent(event.id);
    const minimum=Math.min(...(project?.events.filter(e=>group.includes(e.id)).map(e=>e.start)??[event.start]));
    const origin = ev.clientX; let next = {id: event.id, start: event.start, end: event.end,mode,ids:group};
    const move = (p: PointerEvent) => {
      const delta = (p.clientX - origin) / ppx;
      const span = event.end - event.start;
      if (mode === 'move') {
        const start = Math.max(event.start-minimum, event.start + delta);
        next = {...next, start, end: start + span};
      } else if (mode === 'start') next = {...next, start: Math.max(0, Math.min(event.end - .05, event.start + delta)), end: event.end};
      else next = {...next, start: event.start, end: Math.max(event.start + .05, Math.min(duration, event.end + delta))};
      setDraft(next);
    };
    const end = () => {
      window.removeEventListener('pointermove', move); window.removeEventListener('pointerup', end);
      window.removeEventListener('pointercancel', cancel); stopPointer.current=null;setDraft(null);
      if (Math.abs(next.start - event.start) > .001 || Math.abs(next.end - event.end) > .001)
        if(mode==='move'&&onMoveSelection)onMoveSelection(group,+(next.start-event.start).toFixed(3));
        else onUpdateEvent(event.id, {start: +next.start.toFixed(3), end: +next.end.toFixed(3)});
    };
    const cancel = () => { window.removeEventListener('pointermove', move); window.removeEventListener('pointerup', end); window.removeEventListener('pointercancel', cancel); stopPointer.current=null;setDraft(null); };
    stopPointer.current=cancel;
    window.addEventListener('pointermove', move); window.addEventListener('pointerup', end); window.addEventListener('pointercancel', cancel);
  };
  const trackRows=useMemo(()=>lanes.map(lane => <div key={lane.key} className="tl-track" style={{height: 38}}>
        <div className="tl-track-head" title={lane.label} style={{width:HEAD_W,color:lane.color}}>{lane.label}</div>
        <div className="tl-lane" style={{width:contentW - HEAD_W, position:'relative'}}>
          {lane.events.map(e => {
            const dragged=project?.events.find(item=>item.id===draft?.id);
            const linked=draft?.mode==='move'&&dragged&&(e.id===draft.id||(draft.ids?.includes(e.id))||(ripple&&e.start>=Math.max(...(project?.events.filter(item=>draft.ids?.includes(item.id)).map(item=>item.end)??[dragged.end]))));
            const offset=linked&&draft&&dragged?draft.start-dragged.start:0;
            const current = draft?.id === e.id ? draft : linked?{...e,start:e.start+offset,end:e.end+offset}:e;
            const color = project?.speakers.find(s => s.id === e.speaker_id)?.color || EVENT_TYPES[e.type]?.color || '#aaa';
            return <div key={e.id} role="button" tabIndex={0} aria-label={`Caption ${e.text}`} className={`tl-clip ${(selectedIds?.includes(e.id)??selectedEventId === e.id) ? 'selected' : ''}`}
              style={{left:current.start * ppx,width: Math.max(8,(current.end - current.start) * ppx),background:color,color:readableOn(color)}}
              title={`${e.text}: ${current.start.toFixed(2)} to ${current.end.toFixed(2)} seconds`}
              onPointerDown={p => drag(p,e,'move')}
              aria-pressed={selectedIds?.includes(e.id)??selectedEventId===e.id}
              onKeyDown={p => { if (p.key === 'Enter'||p.code==='Space') {p.preventDefault();p.stopPropagation();onSelectEvent(e.id,p.shiftKey||p.ctrlKey||p.metaKey);if(!p.shiftKey&&!p.ctrlKey&&!p.metaKey)onScrub(e.start);} }}>
              <span className="trim-handle left" onPointerDown={p => drag(p,e,'start')} title="Trim start"/>
              <span className="clip-label">{e.text || 'Empty caption'}</span>
              <span className="trim-handle right" onPointerDown={p => drag(p,e,'end')} title="Trim end"/>
            </div>;
          })}
        </div>
      </div>),[lanes,project,selectedIds,selectedEventId,draft,ripple,ppx,contentW,onSelectEvent,onMoveSelection,onUpdateEvent,onScrub]);
  return <div className="timeline">
    <div className="tl-head"><div className="tl-title"><Icon name="timeline" size={16}/> Timeline <span className="dim">{fmtTime(duration)}</span></div>
      <div className="timeline-actions"><span className="tl-help">Drag to move · edges to trim</span>
        <button className="subtle" title="Zoom out" onClick={() => setPpx(p => Math.max(10, p / 1.25))}><Icon name="zoom-out" size={15}/></button>
        <button className="subtle" title="Zoom in" onClick={() => setPpx(p => Math.min(400, p * 1.25))}><Icon name="zoom-in" size={15}/></button>
      </div>
    </div>
    <div className="tl-body" ref={bodyRef}><div style={{width: contentW, position: 'relative'}}>
      <div className="tl-ruler" role="slider" aria-label="Timeline playhead" aria-valuemin={0} aria-valuemax={duration} aria-valuenow={time} tabIndex={0}
        onKeyDown={e => { if (['ArrowLeft','ArrowRight','Home','End'].includes(e.key)) {e.preventDefault(); e.stopPropagation(); onScrub(e.key === 'Home' ? 0 : e.key === 'End' ? duration : time + (e.key === 'ArrowRight' ? 1 : -1) / (project?.video.fps || 24));} }}
        onPointerDown={e => { stopPointer.current?.();seek(e.clientX); const move = (p: PointerEvent) => seek(p.clientX); const end = () => { window.removeEventListener('pointermove',move);window.removeEventListener('pointerup',end);window.removeEventListener('pointercancel',end);stopPointer.current=null; };stopPointer.current=end; window.addEventListener('pointermove',move);window.addEventListener('pointerup',end);window.addEventListener('pointercancel',end); }}>
        <div className="tl-track-head" style={{width: HEAD_W}}>TIME</div>
        {ticks.map(t => <div key={t} className="tl-tick major" style={{left: HEAD_W + t * ppx}}><span>{fmtTime(t)}</span></div>)}
      </div>
      <div className="tl-track" style={{height: 38}}><div className="tl-track-head" style={{width: HEAD_W}}>Video</div><div className="tl-lane source-lane" style={{width:contentW - HEAD_W}}>{mediaName || 'No video loaded. Import a local video to composite.'}</div></div>
      {trackRows}
      <div className="tl-track" style={{height: 30}}><div className="tl-track-head" style={{width:HEAD_W}}>Words</div><div className="tl-lane" style={{width:contentW - HEAD_W,position:'relative'}}>
        {selected?.words.map((w,i) => <button key={i} aria-label={`Seek to word ${w.text}`} className="tl-wordbar" title={`${w.text}: ${w.start.toFixed(2)}s`} onClick={() => onScrub(w.start)} style={{left:w.start * ppx,width:Math.max(3,(w.end-w.start)*ppx),background:w.color}}/>)}
      </div></div>
      <div className="tl-playhead" style={{left:HEAD_W + time * ppx,pointerEvents:'none'}}/>
    </div></div>
  </div>;
}
