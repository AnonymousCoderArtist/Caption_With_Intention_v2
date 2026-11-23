import type {CaptionEvent,Speaker} from '@/types/project';
export function speakerReviewReasons(event:CaptionEvent,speakers:Speaker[]):string[]{
 if(event.speaker_reviewed||!['dialogue','speaker_overlap'].includes(event.type))return [];
 const reasons=[...(event.speaker_review_reasons??[])];
 if(!event.speaker_id||!speakers.some(s=>s.id===event.speaker_id))reasons.push('No speaker assigned.');
 if(event.end-event.start<.4)reasons.push('Very short turn.');
 if(event.speaker_review_required&&!reasons.length)reasons.push('Attribution needs review.');
 return [...new Set(reasons)];
}
