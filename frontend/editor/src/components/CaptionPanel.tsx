import {useEffect,useMemo,useRef,useState} from 'react';
import {BrowserSpeechCancelled,detectSupport,installOnDevice,onDeviceStatus,transcribeFile} from '@/lib/browserSpeech';
interface Job {id:string;state:string;progress:number;stage?:string;error?:string}
const MODELS:{id:string;label:string}[]=[
 {id:'base.en',label:'Speech model: fast (base.en, about 150 MB, lower accuracy)'},
 {id:'small.en',label:'Speech model: better words (small.en, about 500 MB, slower)'},
];
const BROWSER_ID='browser';
/** Local automatic captions: recognition runs on this computer, never in a cloud account. */
export function CaptionPanel({source,hasEvents,onClose,onDone,onActiveChange}:{source:File|null;hasEvents:boolean;onClose:()=>void;onDone:(project:unknown)=>void;onActiveChange?:(active:boolean)=>void}) {
 const support=useMemo(detectSupport,[]);
 const [job,setJob]=useState<Job|null>(null),[error,setError]=useState(''),[busy,setBusy]=useState(false),[upload,setUpload]=useState(0),[engine,setEngine]=useState(support.ok?BROWSER_ID:'base.en');
 const [localOnly,setLocalOnly]=useState(true),[installing,setInstalling]=useState(false);
 const mounted=useRef(true),transfer=useRef<XMLHttpRequest|null>(null),finished=useRef(false),cancelled=useRef(false);
 useEffect(()=>{mounted.current=true;return()=>{mounted.current=false;transfer.current?.abort();cancelled.current=true;};},[]);
 const browserMode=engine===BROWSER_ID;
 const running=!!job&&['uploading','transferring','analyzing'].includes(job.state);
 const active=busy||running;
 useEffect(()=>{onActiveChange?.(active);return()=>onActiveChange?.(false);},[active,onActiveChange]);
 useEffect(()=>{
  if(!job||!running||busy||browserMode)return;
  let stop=false;
  const timer=setTimeout(async()=>{
   try{const r=await fetch(`/api/captions/${job.id}/status`);const next=await r.json();if(stop)return;if(!r.ok)throw new Error(next.error||'Status unavailable.');setJob(next);}
   catch(e){if(!stop)setError(e instanceof Error?e.message:'Status unavailable.');}
  },800);
  return()=>{stop=true;clearTimeout(timer);};
 },[job,running,busy,browserMode]);
 useEffect(()=>{
  if(job?.state!=='complete'||finished.current)return;finished.current=true;
  if(browserMode)return; // browser mode already has the project when it completes
  fetch(`/api/captions/${job.id}/result`).then(async r=>{const data=await r.json();if(!r.ok)throw new Error(data.error||'Could not read the captions.');if(mounted.current)onDone(data);}).catch(e=>{if(mounted.current)setError(e instanceof Error?e.message:'Could not read the captions.');});
 },[job,onDone,browserMode]);
 const startBrowser=async()=>{
  cancelled.current=false;
  setJob({id:BROWSER_ID,state:'analyzing',progress:0,stage:'Preparing browser speech'});
  if(localOnly){
   const status=await onDeviceStatus('en-US');
   if(status==='downloadable'){
    setInstalling(true);setJob({id:BROWSER_ID,state:'analyzing',progress:0,stage:'Downloading the browser language pack (one time)'});
    const ok=await installOnDevice('en-US');setInstalling(false);
    if(!ok)throw new Error('The on-device language pack could not be installed. Turn off "on this device", or pick a speech model below.');
   }else if(status==='unavailable')throw new Error('This browser cannot recognize speech on-device. Turn off "on this device" (audio goes to the browser speech service), or pick a speech model below.');
  }
  const made=await transcribeFile({
   file:source as File,lang:'en-US',processLocally:localOnly,
   onStage:stage=>{if(mounted.current)setJob(j=>j?{...j,stage}:j);},
   onProgress:progress=>{if(mounted.current)setJob(j=>j?{...j,progress}:j);},
   isCancelled:()=>cancelled.current,
  });
  if(mounted.current)setJob(j=>j?{...j,stage:'Building editable captions',progress:99}:j);
  const built=await fetch('/api/captions/build',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(made)});
  const data=await built.json();if(!built.ok)throw new Error(data.error||'Could not build the captions.');
  if(!mounted.current)return;
  finished.current=true;setJob({id:BROWSER_ID,state:'complete',progress:100,stage:'Done'});onDone(data);
 };
 const start=async()=>{
  if(!source||active)return;
  if(hasEvents&&!window.confirm('Automatic captions replace the current captions and speakers. Save your project JSON first if you want to keep them. Continue?'))return;
  setError('');setBusy(true);setUpload(0);finished.current=false;
  try{
   if(browserMode){await startBrowser();return;}
   const created=await fetch('/api/captions/create',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({model:engine})});
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
  }catch(e){
   if(!mounted.current)return;
   if(e instanceof BrowserSpeechCancelled)setJob({id:BROWSER_ID,state:'cancelled',progress:0,stage:'Cancelled'});
   else setError(e instanceof Error?e.message:'Captioning failed.');
  }
  finally{transfer.current=null;if(mounted.current)setBusy(false);}
 };
 const cancel=async()=>{
  if(browserMode){cancelled.current=true;return;}
  transfer.current?.abort();if(!job)return;try{const r=await fetch(`/api/captions/${job.id}/cancel`,{method:'POST'});const next=await r.json();if(r.ok&&mounted.current)setJob(next);}catch{setError('Could not cancel. Close the editor to stop.');}
 };
 const browserLabel=job?.state==='complete'?'Captions ready':job?.state==='cancelled'?'Cancelled':job?`${job.stage||'Working'} · ${job.progress}%`:'';
 const label=browserMode?browserLabel:busy&&upload<100?`Copying video to the local engine · ${upload}%`:job?.state==='complete'?'Captions ready':job?.state==='failed'?'Captioning failed':job?.state==='cancelled'?'Cancelled':job?`${job.stage||'Working'} · ${job.progress}%`:'';
 return <section className="render-panel" aria-label="Auto captions">
  <div><h3>Auto captions</h3><button className="subtle" onClick={onClose} disabled={active}>Close</button></div>
  <p>Makes editable captions from the speech in your video, on this computer. Free, no account. English speech only. Speakers are not separated automatically: assign colors yourself afterwards.</p>
  <p className="mono">{source?source.name:'Import your video first (top bar, Import video).'}</p>
  <label>Engine <select value={engine} disabled={active} onChange={e=>setEngine(e.target.value)} aria-label="Recognition engine">
   <option value={BROWSER_ID} disabled={!support.ok}>Browser speech (default: nothing to install, plays the video in real time){support.ok?'':' — not available in this browser'}</option>
   {MODELS.map(m=><option key={m.id} value={m.id}>{m.label}</option>)}
  </select></label>
  {browserMode&&support.reason&&<p role="note" className="render-error">{support.reason} A speech model is selected instead where possible.</p>}
  {browserMode&&support.ok&&<>
   <label><input type="checkbox" checked={localOnly} disabled={active||installing} onChange={e=>setLocalOnly(e.target.checked)}/> Recognize on this device (downloads a small language pack once, then works offline)</label>
   {!localOnly&&<p role="note" className="render-error">With this off, the audio goes to your browser's speech service (for example Google in Chrome) and needs internet.</p>}
   <small>Plays the video at normal speed: a 10 minute video takes 10 minutes. Timing is phrase-level: words are spread evenly inside each phrase, so check the timing before rendering.</small>
  </>}
  {job&&<><label>{label}</label><progress max={100} value={browserMode?job.progress:busy&&upload<100?upload:job.progress}/></>}
  {(error||job?.error)&&<p role="alert" className="render-error">{error||job?.error}</p>}
  <div>{running&&<button className="ghost" onClick={cancel}>Cancel</button>}
  <button className="primary" disabled={!source||active} onClick={start}>{active?'Working...':job?.state==='complete'?'Run again':'Generate captions'}</button></div>
  <small>{browserMode
   ?'Browser speech needs Chrome, Edge 135+ or Firefox 160+. Output is a draft: words, timing and sound cues need review. Keep this tab open and audible playback is not needed (the video stays muted).'
   :'First run downloads the speech model once (internet needed, then it works offline). Needs FFmpeg on PATH and the speech add-on (uv sync --extra dev --extra asr). Output is a draft: words, timing and sound cues need review. Keep this tab open while it runs.'}</small>
 </section>;
}
