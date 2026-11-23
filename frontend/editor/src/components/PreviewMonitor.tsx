/** Reactive composition monitor. Browser preview, not a substitute for final FFmpeg QA. */
import { useEffect, useRef, useState } from 'react';
import type { CaptionEvent, Project } from '@/types/project';
import {displayWords} from '@/lib/captionText';
import { ASS_EM_SCALE, activeCaptionEvents, letterLift, letterSpoken, sizeAt } from '@/lib/captionMotion';
import {captionLines,captionLineGap,nominalWidth} from '@/lib/captionLayout';
import { fmtTimecode } from '@/lib/theme';
import { Icon } from '@/lib/icons';

function useSize(ref: React.RefObject<HTMLElement | null>) {
  const [size, setSize] = useState({ w: 0, h: 0 });
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const observer = new ResizeObserver(([entry]) => setSize({ w: entry.contentRect.width, h: entry.contentRect.height }));
    observer.observe(el);
    return () => observer.disconnect();
  }, [ref]);
  return size;
}
function Caption({ event, project, time, height, onSelect, selected }: {
  event: CaptionEvent; project: Project; time: number; height: number;
  onSelect?: (id: string) => void; selected: boolean;
}) {
  const speaker = project.speakers.find(s => s.id === event.speaker_id);
  const words=displayWords(event);
  const timed=event.type!=='music'&&event.words.length>0;

  const base = height * .05;
  let wordOffset=0;
  const lines = (event.type==='dialogue'||event.type==='speaker_overlap'||event.type==='custom') && event.words.length
    ? captionLines(event,project.video.width,project.video.height).map(line=>{const displayed=words.slice(wordOffset,wordOffset+line.length);wordOffset+=line.length;return displayed;}) : [words];
  const breakout = words.some(w => (event.style.size_mode==='manual'?event.style.size_pct:w.size_pct) >= (event.type==='sound_effect'?6:10));
  return <div className="composition-group" style={{display:'flex',flexDirection:'column',alignItems:'center',gap:captionLineGap(event,lines,height,project.video.height)}}>{lines.map((line,lineIndex)=><div key={lineIndex} className={`composition-event ${selected ? 'selected' : ''}`} role="button" tabIndex={0}
    aria-label={`Select caption: ${event.text}`} onClick={() => onSelect?.(event.id)}
    onKeyDown={e => { if (e.key === 'Enter') onSelect?.(event.id); }}
    style={{ background: breakout ? 'transparent' : `rgba(0,0,0,${event.style.box_opacity})`,
      padding: `${event.style.box_padding * height / project.video.height}px`,
      fontSize: base * ASS_EM_SCALE, whiteSpace:'nowrap', lineHeight: 0 }}>
    {line.map((word, wi) => {
      const chars = Array.from(word.text.trim());
      const size = event.type === 'music' ? base : sizeAt(word, event, time, base);
      const targetWidth = event.style.width_mode === 'manual' ? event.style.width : word.source_model && !word.manual_override && Math.abs(word.width - 100) < 15 ? 100 : word.width;
      const weight = event.style.weight_mode === 'manual' ? event.style.weight : word.weight;
      const spoken = time >= word.start;
      const width = spoken && time < word.end ? targetWidth : 100;
      return <span className="composition-word" key={wi} style={{ fontSize: size * ASS_EM_SCALE, height: base, lineHeight: `${base}px`, position: 'relative', top: event.style.box_padding * height / project.video.height,
        fontWeight: spoken && time < word.end && weight >= 700 ? 700 : 400,
        fontStyle: spoken && (word.italic || event.off_camera || speaker?.off_camera || event.style.italic) ? 'italic' : 'normal',
        fontOpticalSizing: 'none',
        fontVariationSettings: '"wdth" 100, "opsz" 14, "wght" 400',
        textAlign:'left',
        width: width===100 ? undefined : nominalWidth(word.text.trim(),size*ASS_EM_SCALE,width),
        opacity: word.opacity }}>
        <span style={{display:'inline-block',transform:width===100?undefined:`scaleX(${width/100})`,transformOrigin:'left center'}}>{chars.map((char, j) => {
          const colored = event.type !== 'music' && (!timed || letterSpoken(word, j, chars.length, time));
          const color = event.type==='music' ? 'rgba(255,255,255,.9)' : colored ? (speaker?.color ?? (event.speaker_id ? word.color : '#fff')) : `rgba(255,255,255,${event.style.read_ahead_opacity})`;
          const lift = !timed ? 0 : letterLift(word, j, chars.length, time, base, event.style.pop_scale);
          return <span key={j} className="composition-letter" style={{ color, transform: `translateY(${-lift}px)` }}>{char}</span>;
        })}</span>
      </span>;
    })}
  </div>)}</div>;
}
export function PreviewMonitor({ project, time, fps, mediaUrl, playing = false,
  onMediaTime, onMediaDuration, onEnded, selectedEventId, onSelectEvent }: {
  project: Project | null; time: number; fps: number; mediaUrl?: string | null; playing?: boolean;
  onMediaTime?: (time: number) => void; onMediaDuration?: (duration: number) => void;
  onEnded?: () => void; selectedEventId?: string | null; onSelectEvent?: (id: string) => void;
}) {
  const wrapRef = useRef<HTMLDivElement>(null);
  const available = useSize(wrapRef);
  const ratio = project ? project.video.width/project.video.height : 16/9;
  const monitorWidth = Math.max(0,Math.min(available.w,(available.h-50)*ratio));
  const frameRef = useRef<HTMLDivElement>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const { h } = useSize(frameRef);
  const active = project ? activeCaptionEvents(project.events, time) : [];
  const [mediaError, setMediaError] = useState('');
  useEffect(() => {setMediaError('');}, [mediaUrl]);
  useEffect(() => {
    const video = videoRef.current;
    if (!video || !mediaUrl) return;
    if (!playing || Math.abs(video.currentTime - time) > .2) video.currentTime = time;
  }, [time, playing, mediaUrl]);
  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;
    let current=true;
    if (playing) video.play().catch(() => {if(current){setMediaError('Playback could not start. Press play again.');onEnded?.();}});
    else video.pause();
    return()=>{current=false;};
  }, [playing, mediaUrl]);
  useEffect(() => {
    if (!playing || !mediaUrl) return;
    let raf = 0;
    const tick = () => { if (videoRef.current) onMediaTime?.(videoRef.current.currentTime); raf = requestAnimationFrame(tick); };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [playing, mediaUrl, onMediaTime]);
  return <div className="monitor-wrap" ref={wrapRef}>
    <div className="program-monitor-title"><span>Program monitor</span><span>{mediaUrl ? 'Local video + captions' : 'Caption study · no source video'}</span></div>
    <div className="monitor" style={{ aspectRatio:ratio,width:monitorWidth||'100%',height:monitorWidth?monitorWidth/ratio:undefined,flexShrink:0 }}>
      <div className="monitor-frame" ref={frameRef}>
        {mediaUrl ? <video ref={videoRef} src={mediaUrl} className="source-video" playsInline disableRemotePlayback disablePictureInPicture
          onLoadedMetadata={e => {setMediaError(''); onMediaDuration?.(e.currentTarget.duration);}}
          onError={() => {setMediaError('This video could not be decoded by your browser.');onEnded?.();}}
          onEnded={onEnded} /> : <div className="scene" />}
        <div className="composition-layer" style={{paddingBottom: h * .05}}>
          {project && active.map(event => <Caption key={event.id} event={event} project={project} time={time}
            height={h} selected={event.id === selectedEventId} onSelect={onSelectEvent} />)}
        </div>
        <div className="monitor-meta"><span className="monitor-rec"><span className="dot" />{mediaError || 'Browser preview'}</span><span className="monitor-tc">{fmtTimecode(time, fps)}</span></div>
      </div>
    </div>
    <p className="preview-note">Local composition preview. Final FFmpeg render remains the fidelity check.</p>
  </div>;
}

/** Transport control bar under the monitor. */
export function Transport({
  time,
  duration,
  playing,
  fps,
  onToggle,
  onScrub,
  onStep,
  onSkip,
}: {
  time: number;
  duration: number;
  playing: boolean;
  fps: number;
  onToggle: () => void;
  onScrub: (t: number) => void;
  onStep: (dir: -1 | 1) => void;
  onSkip: (dir: "start" | "end") => void;
}) {
  const barRef = useRef<HTMLDivElement>(null);
  const stopScrub=useRef<(()=>void)|null>(null);
  useEffect(()=>()=>{stopScrub.current?.();},[]);
  const pct = duration > 0 ? Math.min(100, (time / duration) * 100) : 0;

  const scrubTo = (clientX: number) => {
    const el = barRef.current;
    if (!el) return;
    const r = el.getBoundingClientRect();
    const ratio = Math.min(1, Math.max(0, (clientX - r.left) / r.width));
    onScrub(ratio * duration);
  };

  return (
    <div className="transport">
      <button className="t-btn" onClick={() => onSkip("start")} title="Skip to start">
        <Icon name="skip-back" size={15} />
      </button>
      <button className="t-btn" onClick={() => onStep(-1)} title="Previous frame">
        <Icon name="step-back" size={15} />
      </button>

      <button className="t-btn t-play" onClick={onToggle} title={playing ? "Pause" : "Play"}>
        <Icon name={playing ? "pause" : "play"} size={18} />
      </button>

      <button className="t-btn" onClick={() => onStep(1)} title="Next frame">
        <Icon name="step-fwd" size={15} />
      </button>
      <button className="t-btn" onClick={() => onSkip("end")} title="Skip to end">
        <Icon name="skip-fwd" size={15} />
      </button>

      <div className="scrub">
        <div
          className="scrub-track" role="slider" aria-label="Playback position" tabIndex={0}
          aria-valuemin={0} aria-valuemax={duration} aria-valuenow={time}
          onKeyDown={e => {if(['ArrowLeft','ArrowRight','Home','End'].includes(e.key)){e.preventDefault();e.stopPropagation();onScrub(e.key==='Home'?0:e.key==='End'?duration:Math.max(0,Math.min(duration,time+(e.key==='ArrowRight'?1:-1)/fps)));}}}
          ref={barRef}
          onPointerDown={(e) => {
            stopScrub.current?.();
            (e.target as HTMLElement).setPointerCapture?.(e.pointerId);
            scrubTo(e.clientX);
            const move = (ev: PointerEvent) => scrubTo(ev.clientX);
            const up = () => {
              window.removeEventListener("pointermove", move);
              window.removeEventListener("pointerup", up);
              window.removeEventListener("pointercancel", up);
              stopScrub.current=null;
            };
            stopScrub.current=up;
            window.addEventListener("pointermove", move);
            window.addEventListener("pointerup", up);
            window.addEventListener("pointercancel", up);
          }}
        >
          <div className="scrub-fill" style={{ width: `${pct}%` }} />
          <div className="scrub-knob" style={{ left: `${pct}%` }} />
        </div>
      </div>

      <div className="tc">
        {fmtTimecode(time, fps)}
        <span className="dim"> / {fmtTimecode(duration, fps)}</span>
      </div>
    </div>
  );
}
