import {useEffect,useRef,useState} from 'react';
interface Job {id:string;state:string;progress:number;stage?:string;error?:string}
const MODELS:{id:string;label:string}[]=[
 {id:'base.en',label:'Fast (base.en, about 150 MB, lower accuracy)'},
 {id:'small.en',label:'Better words (small.en, about 500 MB, slower)'},
];
/** Local automatic captions: the video is copied to the local Python service, never to a cloud service. */
export function CaptionPanel({source,hasEvents,onClose,onDone,onActiveChange}:{source:File|null;hasEvents:boolean;onClose:()=>void;onDone:(project:unknown)=>void;onActiveChange?:(active:boolean)=>void}) {
 const [job,setJob]=useState<Job|null>(null),[error,setError]=useState(''),[busy,setBusy]=useState(false),[upload,setUpload]=useState(0),[model,setModel]=useState('base.en');
 const mounted=useRef(true),transfer=useRef<XMLHttpRequest|null>(null),finished=useRef(false);
 useEffect(()=>{mounted.current=true;return()=>{mounted.current=false;transfer.current?.abort();};},[]);
 const running=!!job&&['uploading','transferring','analyzing'].includes(job.state);
 const active=busy||running;
 useEffect(()=>{onActiveChange?.(active);return()=>onActiveChange?.(false);},[active,onActiveChange]);
 useEffect(()=>{
  if(!job||!running||busy)return;
  let stop=false;
  const timer=setTimeout(async()=>{
   try{const r=await fetch(`/api/captions/${job.id}/status`);const next=await r.json();if(stop)return;if(!r.ok)throw new Error(next.error||'Status unavailable.');setJob(next);}
   catch(e){if(!stop)setError(e instanceof Error?e.message:'Status unavailable.');}
  },800);
  return()=>{stop=true;clearTimeout(timer);};
 },[job,running,busy]);
 useEffect(()=>{
  if(job?.state!=='complete'||finished.current)return;finished.current=true;
  fetch(`/api/captions/${job.id}/result`).then(async r=>{const data=await r.json();if(!r.ok)throw new Error(data.error||'Could not read the captions.');if(mounted.current)onDone(data);}).catch(e=>{if(mounted.current)setError(e instanceof Error?e.message:'Could not read the captions.');});
 },[job,onDone]);
 const start=async()=>{
  if(!source||active)return;
  if(hasEvents&&!window.confirm('Automatic captions replace the current captions and speakers. Save your project JSON first if you want to keep them. Continue?'))return;
  setError('');setBusy(true);setUpload(0);finished.current=false;
  try{
   const created=await fetch('/api/captions/create',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({model})});
   const made=await created.json();if(!created.ok)throw new Error(made.error||'Could not start captioning.');
   setJob(made);
   const uploaded:Job=await new Promise((resolve,reject)=>{
    const request=new XMLHttpRequest();transfer.current=request;request.open('POST',`/api/captions/${made.id}/source`);request.timeout=30*60*1000;
    request.upload.onprogress=e=>{if(e.lengthComputable&&mounted.current)setUpload(Math.round(e.loaded/e.total*100));};
    request.onload=()=>{try{const body=JSON.parse(request.responseText);request.status>=200&&request.status<300?resolve(body):reject(new Error(body.error||'Upload failed.'));}catch{reject(new Error('Upload failed.'));}};
    request.onerror=()=>reject(new Error('The local service could not be reached. Is the editor running?'));request.ontimeout=()=>reject(new Error('The video copy took too long.'));request.onabort=()=>reject(new Error('Cancelled.'));
    request.send(source);
   });
   if(mounted.current)setJob(uploaded);
  }catch(e){if(mounted.current)setError(e instanceof Error?e.message:'Captioning failed.');}
  finally{transfer.current=null;if(mounted.current)setBusy(false);}
 };
 const cancel=async()=>{transfer.current?.abort();if(!job)return;try{const r=await fetch(`/api/captions/${job.id}/cancel`,{method:'POST'});const next=await r.json();if(r.ok&&mounted.current)setJob(next);}catch{setError('Could not cancel. Close the editor to stop.');}};
 const label=busy&&upload<100?`Copying video to the local engine · ${upload}%`:job?.state==='complete'?'Captions ready':job?.state==='failed'?'Captioning failed':job?.state==='cancelled'?'Cancelled':job?`${job.stage||'Working'} · ${job.progress}%`:'';
 return <section className="render-panel" aria-label="Auto captions">
  <div><h3>Auto captions</h3><button className="subtle" onClick={onClose} disabled={active}>Close</button></div>
  <p>Makes editable captions from the speech in your video, on this computer. Free, no account. English speech only. Speakers are not separated automatically: assign colors yourself afterwards.</p>
  <p className="mono">{source?source.name:'Import your video first (top bar, Import video).'}</p>
  <label>Model <select value={model} disabled={active} onChange={e=>setModel(e.target.value)} aria-label="Speech model">{MODELS.map(m=><option key={m.id} value={m.id}>{m.label}</option>)}</select></label>
  {job&&<><label>{label}</label><progress max={100} value={busy&&upload<100?upload:job.progress}/></>}
  {(error||job?.error)&&<p role="alert" className="render-error">{error||job?.error}</p>}
  <div>{running&&<button className="ghost" onClick={cancel}>Cancel</button>}
  <button className="primary" disabled={!source||active} onClick={start}>{active?'Working...':job?.state==='complete'?'Run again':'Generate captions'}</button></div>
  <small>First run downloads the speech model once (internet needed, then it works offline). Needs FFmpeg on PATH and the speech add-on (uv sync --extra dev --extra asr). Output is a draft: words, timing and sound cues need review. Keep this tab open while it runs.</small>
 </section>;
}
