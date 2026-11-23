import {useEffect,useRef,useState} from 'react';
import type {Project} from '@/types/project';
import {inspectMedia,renderWarnings} from '@/lib/renderPreflight';
function RenderedVideo({id}:{id:string}) {
 const video=useRef<HTMLVideoElement>(null);
 const [time,setTime]=useState(0),[duration,setDuration]=useState(0),[playing,setPlaying]=useState(false),[playError,setPlayError]=useState('');
 return <div className="render-result-wrap"><video ref={video} className="render-result" src={`/api/render/${id}/download`} playsInline disableRemotePlayback disablePictureInPicture preload="auto" aria-label="Final rendered video"
 onError={()=>setPlayError('This local render is unavailable or could not be decoded. It may have expired. Render again to create a new MP4.')} onLoadedMetadata={e=>{setDuration(e.currentTarget.duration);setPlayError('');}} onTimeUpdate={e=>setTime(e.currentTarget.currentTime)} onPlay={()=>setPlaying(true)} onPause={()=>setPlaying(false)}/>
 <div className="render-playback"><button className="ghost" onClick={()=>{const v=video.current;if(v){if(v.paused)void v.play().catch(()=>setPlayError('Playback could not start. Download the MP4 to inspect it.'));else v.pause();}}}>{playing?'Pause final':'Play final'}</button>
 <input type="range" aria-label="Final video position" min={0} max={duration||0} step={.01} value={time} onChange={e=>{if(video.current)video.current.currentTime=Number(e.target.value);setTime(Number(e.target.value));}}/>
 <span className="mono">{time.toFixed(1)} / {duration.toFixed(1)}s</span></div>
 <button className="subtle" onClick={()=>{void video.current?.requestFullscreen().catch(()=>setPlayError('Full screen is unavailable. Download the MP4 for a larger view.'));}}>Full screen</button>
 {playError&&<p role="alert">{playError}</p>}</div>;
}
interface Job {id:string;state:string;progress:number;error?:string}
export function RenderPanel({source,getProject,onClose,onActiveChange}:{source:File|null;getProject:()=>Promise<Project>;onClose:()=>void;onActiveChange?:(active:boolean)=>void}) {
 const [job,setJob]=useState<Job|null>(null),[error,setError]=useState(''),[busy,setBusy]=useState(false),[upload,setUpload]=useState(0);
 const mounted=useRef(true),transfer=useRef<XMLHttpRequest|null>(null);
 const [retry,setRetry]=useState(0),[renderSourceName,setRenderSourceName]=useState('');
 const cancel=async()=>{if(!job)return;setError('');try{const r=await fetch(`/api/render/${job.id}/cancel`,{method:'POST'});const next=await r.json();if(!r.ok)throw new Error(next.error||'Could not cancel render.');transfer.current?.abort();setJob(next);setBusy(false);}catch(e){setError(e instanceof Error?e.message:'Could not cancel render.');}};
 useEffect(()=>{mounted.current=true;return()=>{mounted.current=false;};},[]);

 useEffect(()=>{
  if(!job||!['rendering','uploading','transferring'].includes(job.state)||busy)return;
  let cancelled=false;let timer:ReturnType<typeof setTimeout>;
  const check=async()=>{
   try{const response=await fetch(`/api/render/${job.id}/status`);const next=await response.json();if(response.status===404){if(!cancelled){setJob(current=>current?{...current,state:'failed'}:null);setError(next.error||'This render expired. Start another render.');}return;}if(!response.ok)throw new Error(next.error||'Could not check render status.');if(!cancelled){setJob(next);setError('');if(['rendering','uploading','transferring'].includes(next.state))timer=setTimeout(check,1000);}}
   catch(e){if(!cancelled)setError(e instanceof Error?e.message:'Render status unavailable.');}
  };timer=setTimeout(check,500);return()=>{cancelled=true;clearTimeout(timer);};
 },[job?.id,job?.state,busy,retry]);
 const start=async()=>{
  if(!source)return;if(source.size>2*1024**3){setError('Choose a source video smaller than 2 GB.');return;}setBusy(true);setError('');setUpload(0);
  try{
   setRenderSourceName(source.name);
   const project=await getProject();
   let warnings:string[];
   try{warnings=renderWarnings(project,await inspectMedia(source));}
   catch{warnings=['The browser could not inspect this video. Source dimensions and caption coverage could not be checked. FFmpeg will try to decode it locally.'];}
   if(warnings.length&&!window.confirm(warnings.join('\n\n')+'\n\nRender this source anyway?'))return;
   const requestKey=crypto.randomUUID();
   const create=async()=>{const response=await fetch('/api/render/create',{method:'POST',headers:{'Content-Type':'application/json','X-CWI-Request-Key':requestKey},body:JSON.stringify(project)});return {response,result:await response.json() as Job};};
   // If the response is lost, retry the same key rather than reserving a second job.
   let created:Awaited<ReturnType<typeof create>>;
   try{created=await create();}catch{created=await create();}
   const {response,result}=created;
   if(!response.ok)throw new Error(result.error||'Could not start local render.');setJob(result);
   const uploaded=await new Promise<Job>((resolve,reject)=>{
    const request=new XMLHttpRequest();transfer.current=request;request.open('POST',`/api/render/${result.id}/source`);request.timeout=30*60*1000;
    request.setRequestHeader('Content-Type','application/octet-stream');
    request.upload.onprogress=e=>{if(mounted.current&&e.lengthComputable)setUpload(Math.round(e.loaded/e.total*100));};
    request.onabort=()=>resolve({...result,state:'cancelled'});
    request.onerror=()=>reject(new Error('Local renderer could not be reached.'));
    request.ontimeout=()=>reject(new Error('Local source transfer timed out.'));
    request.onload=()=>{try{const data=JSON.parse(request.responseText);if(request.status>=400)reject(new Error(data.error||'Source transfer failed.'));else resolve(data);}catch{reject(new Error('Invalid local renderer response.'));}};
    request.send(source);
   });if(mounted.current)setJob(uploaded);
  }catch(e){if(mounted.current){setError(e instanceof Error?e.message:'Render failed.');// A lost upload response does not prove the server stopped encoding.
    setRetry(n=>n+1);}}
  finally{transfer.current=null;if(mounted.current)setBusy(false);}
 };
 const active=busy||!!job&&['rendering','transferring','uploading'].includes(job.state);
 useEffect(()=>{onActiveChange?.(active);return()=>onActiveChange?.(false);},[active,onActiveChange]);
 useEffect(()=>{if(!active)return;const warn=(event:BeforeUnloadEvent)=>{event.preventDefault();event.returnValue='';};window.addEventListener('beforeunload',warn);return()=>window.removeEventListener('beforeunload',warn);},[active]);
 return <section className="render-panel" aria-label="Render video">
  <div><h3>Render video</h3><button className="subtle" onClick={onClose} disabled={!!active}>Close</button></div>
  <p>Final FFmpeg captions, rendered on this computer. Your selected video is copied to the local Python service, never to a cloud service.</p>
  <p className="mono">{job&&renderSourceName?renderSourceName:source?source.name:'Import the matching local video first.'}</p>
  {job&&<><label>{busy?`Copying source · ${upload}%`:job.state==='complete'?'Render complete':job.state==='failed'?'Render failed':job.state==='cancelled'?'Render cancelled':job.state==='uploading'?'Waiting for source':job.state==='transferring'?'Copying source to renderer':`Encoding · ${job.progress}%`}</label><progress max={100} value={busy?upload:job.progress}/></>}
  {(error||job?.error)&&<p role="alert" className="render-error">{error||job?.error}</p>}
  {job?.state==='complete'&&<RenderedVideo key={job.id} id={job.id}/>}
  <div>{job?.state==='complete'&&<a className="render-download" href={`/api/render/${job.id}/download`} download="captioned.mp4">Download MP4</a>}
  {active&&job&&['uploading','transferring','rendering'].includes(job.state)&&<button className="ghost" onClick={cancel}>Cancel render</button>}
  {error&&job&&['rendering','uploading','transferring'].includes(job.state)&&<button className="ghost" onClick={()=>{setError('');setRetry(n=>n+1);}}>Retry status</button>}
  <button className="primary" disabled={!source||!!active} onClick={start}>{active?'Rendering...':job?'Render again':'Start local render'}</button></div>
  <small>Uses a snapshot of the latest edits. Later changes need another render. Keep this tab open during transfer. Download is retained locally for one hour. Maximum source size: 2 GB. Odd dimensions get up to one pixel of right/bottom padding for MP4 compatibility.</small>
 </section>;
}
