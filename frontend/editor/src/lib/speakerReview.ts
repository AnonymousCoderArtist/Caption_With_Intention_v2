import type {CaptionEvent,Speaker} from '@/types/project';
export function speakerReviewReasons(event:CaptionEvent,speakers:Speaker[]):string[]{
 if(event.speaker_reviewed||!['dialogue','speaker_overlap'].includes(event.type))return [];
 const reasons=[...(event.speaker_review_reasons??[])];
 if(!event.speaker_id||!speakers.some(s=>s.id===event.speaker_id))reasons.push('No speaker assigned.');
 if(event.speaker_coverage!=null&&event.speaker_coverage<.7)reasons.push('Limited diarization timing coverage.');
 if(event.end-event.start<.4)reasons.push('Very short turn.');
 if(event.speaker_review_required&&!reasons.length)reasons.push('Attribution needs review.');
 return [...new Set(reasons)];
}

/** Review cues, never calibrated identity confidence or a face-model request. */
export function speakerReviewWindows(events:CaptionEvent[],speakers:Speaker[],duration:number,padding=1.5){
 const windows:{start:number;end:number;eventIds:string[]}[]=[];
 for(const event of [...events].sort((a,b)=>a.start-b.start)){
  if(!speakerReviewReasons(event,speakers).length)continue;
  const start=Math.max(0,event.start-padding),end=Math.min(duration>0?duration:Infinity,event.end+padding);
  if(end<=start)continue;
  const last=windows[windows.length-1];
  if(last&&start<=last.end){last.end=Math.max(last.end,end);last.eventIds.push(event.id);}
  else windows.push({start,end,eventIds:[event.id]});
 }
 return windows;
}
