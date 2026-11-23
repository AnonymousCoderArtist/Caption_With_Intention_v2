import type {Project} from '@/types/project';
/** Caption-only structure edits preserve absolute word/syllable timings. */
export function structureEdit(project:Project,ids:string[],operation:'split'|'merge',at=0):Project {
 const result=structuredClone(project),selected=result.events.filter(e=>ids.includes(e.id)).sort((a,b)=>a.start-b.start||a.end-b.end);
 if(!selected.length||selected.length!==new Set(ids).size)throw new Error('Select existing captions.');
 if(operation==='split') {
  const event=selected[0];
  if(selected.length!==1||!Number.isFinite(at)||at<=event.start||at>=event.end||event.words.length<2)throw new Error('Split needs a playhead inside a caption with at least two timed words.');
  if(event.words.some(w=>w.start<at&&at<w.end))throw new Error('Place the playhead between words, not inside a spoken word.');
  const left=event.words.filter(w=>w.end<=at),right=event.words.filter(w=>w.start>=at);
  if(!left.length||!right.length||left.length+right.length!==event.words.length)throw new Error('Split needs timed words on both sides of the playhead.');
  let n=1;while(result.events.some(e=>e.id===`${event.id}_split_${n}`))n++;
  let leftText=left.map(w=>w.text).join(' '),rightText=right.map(w=>w.text).join(' '),cursor=0;
  const starts:number[]=[];
  for(const word of event.words){const index=event.text.indexOf(word.text,cursor);if(index<0)break;starts.push(index);cursor=index+word.text.length;}
  if(starts.length===event.words.length){leftText=event.text.slice(0,starts[left.length]).trimEnd();rightText=event.text.slice(starts[left.length]).trimStart();}
  const second={...structuredClone(event),id:`${event.id}_split_${n}`,start:at,words:right,text:rightText,manual_override:true};
  event.end=at;event.words=left;event.text=leftText;event.manual_override=true;
  result.events.splice(result.events.indexOf(event)+1,0,second);
 }else if(operation==='merge') {
  if(selected.length<2)throw new Error('Select at least two captions to merge.');
  const first=selected[0];
  if(selected.some(e=>e.speaker_id!==first.speaker_id||e.type!==first.type||JSON.stringify(e.style)!==JSON.stringify(first.style)||e.off_camera!==first.off_camera||e.exception_profile!==first.exception_profile))throw new Error('Merge needs the same speaker, type, style and off-camera settings.');
  if(selected.some((e,i)=>i>0&&e.start<selected[i-1].end))throw new Error('Overlapping captions cannot be merged. Their simultaneous timing is preserved.');
  if(selected.some(e=>!e.words.length))throw new Error('Merge needs timed words in every selected caption.');
  const text=selected.map(e=>e.text).join(' '),words=selected.flatMap(e=>e.words);
  const notes=selected.map(e=>e.notes).filter(Boolean).join('\n\n'),reviewed=selected.every(e=>e.speaker_reviewed);
  const reasons=[...new Set(selected.flatMap(e=>e.speaker_review_reasons??[]))],required=selected.some(e=>e.speaker_review_required);
  first.notes=notes;first.speaker_reviewed=reviewed;first.speaker_review_reasons=reasons;first.speaker_review_required=required;
  first.end=selected[selected.length-1].end;first.text=text;first.words=words;first.manual_override=true;
  result.events=result.events.filter(e=>!selected.slice(1).some(s=>s.id===e.id));
 }else throw new Error('Unknown caption structure operation.');
 return result;
}
