import type {Project,CaptionEvent} from '@/types/project';
function shift(e:CaptionEvent,delta:number){e.start+=delta;e.end+=delta;e.words.forEach(w=>{w.start+=delta;w.end+=delta;w.syllables?.forEach(s=>{s.start+=delta;s.end+=delta;});});}
export function batchEdit(project:Project,ids:string[],operation:'move'|'delete',delta=0,ripple=false):Project {
 const p=structuredClone(project),selected=p.events.filter(e=>ids.includes(e.id));
 if(!selected.length||selected.length!==new Set(ids).size)throw new Error('Select existing caption events.');
 if(!['move','delete'].includes(operation)||!Number.isFinite(delta))throw new Error('Invalid operation or shift.');
 if(operation==='move'){
  const boundary=Math.max(...selected.map(e=>e.end));const targets=p.events.filter(e=>ids.includes(e.id)||(ripple&&e.start>=boundary));
  if(Math.min(...targets.map(e=>e.start))+delta<0)throw new Error('This shift would move a caption before zero.');targets.forEach(e=>shift(e,delta));
 }else{
  const ranges:number[][]=[];
  for(const e of selected.sort((a,b)=>a.start-b.start)){const last=ranges[ranges.length-1];if(last&&e.start<=last[1])last[1]=Math.max(last[1],e.end);else ranges.push([e.start,e.end]);}
  p.events=p.events.filter(e=>!ids.includes(e.id));
  if(ripple)p.events.forEach(e=>shift(e,-ranges.filter(r=>r[1]<=e.start).reduce((n,r)=>n+r[1]-r[0],0)));
 }
 return p;
}
