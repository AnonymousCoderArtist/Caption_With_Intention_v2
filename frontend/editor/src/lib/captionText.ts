import type {CaptionEvent,Word} from '@/types/project';
import {ReviewState} from '@/types/project';
function fallback(event:CaptionEvent,text=event.text):Word {
 return {text,start:event.start,end:event.end,size_pct:5,weight:400,width:100,color:'#fff',opacity:1,italic:false,
 confidence:null,source_model:null,source_timestamp:null,manual_override:false,review_state:ReviewState.Pending,syllables:null};
}
/** Preserve renderer punctuation conventions without changing saved transcript words. */
export function displayWords(event:CaptionEvent):Word[] {
 if(event.type==='music') {
  let text=event.text.trim();
  if(text&&!text.includes('♪'))text=`♪ ${text.replace(/^[\[\] ]+|[\[\] ]+$/g,'')} ♪`;
  return [fallback(event,text)];
 }
 let words=event.words.length?event.words:[fallback(event)];
 if(event.words.length&&event.text){
  let cursor=0;const positions:{start:number;end:number}[]=[];
  for(const word of event.words){const start=event.text.indexOf(word.text,cursor);if(start<0)break;cursor=start+word.text.length;positions.push({start,end:cursor});}
  if(positions.length===event.words.length)words=event.words.map((word,i)=>({...word,character_colors:word.character_colors?[...Array(Array.from(i===0?event.text.slice(0,positions[0].start):'').filter(c=>! /\s/.test(c)).length).fill(null),...word.character_colors]:undefined,text:
   (i===0?event.text.slice(0,positions[0].start):'')+word.text+
   event.text.slice(positions[i].end,i+1<positions.length?positions[i+1].start:event.text.length).trimEnd()}));
 }

 if(event.type==='sound_effect'&&!event.text.trimStart().startsWith('['))
  return words.map((w,i)=>({...w,text:(i===0?'[':'')+w.text+(i===words.length-1?']':'')}));
 return words;
}
