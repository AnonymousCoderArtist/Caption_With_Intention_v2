import type { CaptionEvent, Speaker } from '@/types/project';
/** Greedy interval packing keeps overlapping captions separately reachable. */
export function packIntervals(events: CaptionEvent[]): CaptionEvent[][] {
 const rows:CaptionEvent[][]=[];
 for(const event of [...events].sort((a,b)=>a.start-b.start||a.end-b.end)){
  let row=rows.find(row=>row[row.length-1].end<=event.start);
  if(!row){row=[];rows.push(row)}row.push(event);
 }
 return rows;
}
/** Keep long-video rulers bounded while retaining useful spacing at each zoom. */
export function timelineTicks(duration:number,pixelsPerSecond:number):number[]{
 if(!Number.isFinite(duration)||duration<0||!Number.isFinite(pixelsPerSecond)||pixelsPerSecond<=0)return [];
 const minimum=Math.max(1,60/pixelsPerSecond,duration/500);
 const magnitude=10**Math.floor(Math.log10(minimum));
 const step=[1,2,5,10].map(n=>n*magnitude).find(n=>n>=minimum)??10*magnitude;
 return Array.from({length:Math.floor(duration/step)+1},(_,i)=>i*step);
}

export interface CaptionLane {key:string;label:string;color?:string;events:CaptionEvent[]}
/** Keep each dialogue identity on its own track, including empty named speakers. */
export function speakerLanes(events:CaptionEvent[],speakers:Speaker[]):CaptionLane[]{
 const lanes:CaptionLane[]=[];
 const speech=events.filter(e=>['dialogue','speaker_overlap'].includes(e.type));
 const groups=[...speakers.map(s=>({id:s.id,label:s.name,color:s.color})),{id:null,label:'Unassigned',color:undefined}];
 for(const group of groups){
  const matching=speech.filter(e=>group.id===null?!e.speaker_id||!speakers.some(s=>s.id===e.speaker_id):e.speaker_id===group.id);
  if(!matching.length&&group.id===null&&speakers.length)continue;
  const rows=packIntervals(matching);
  (rows.length?rows:[[]]).forEach((row,i)=>lanes.push({key:`speaker:${group.id??'none'}:${i}`,label:group.label+(i?` · ${i+1}`:''),color:group.color,events:row}));
 }
 for(const [type,label] of [['sound_effect','SFX'],['music','Music'],['custom','Other']] as const){
  const rows=packIntervals(events.filter(e=>e.type===type));
  (rows.length?rows:[[]]).forEach((row,i)=>lanes.push({key:`${type}:${i}`,label:label+(i?` · ${i+1}`:''),events:row}));
 }
 return lanes;
}
