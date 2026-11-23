import type {CaptionEvent} from '@/types/project';
export function soundNeedsReview(event:CaptionEvent):boolean{
 return ['music','sound_effect'].includes(event.type)&&event.review_state==='pending'&&!!event.source_model;
}
