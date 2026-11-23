import type {CaptionEvent,Word} from '@/types/project';
import advances from './fontAdvances.json';
import {effectiveSize} from './captionMotion';
const metrics=advances as Record<string,number>;
export function nominalWidth(text:string,size:number,width=100) {
 return Array.from(text).reduce((sum,c)=>sum+(metrics[c]??.5),0)*size*width/100;
}
/** Mirror renderer: landscape two-line split; portrait source-time pages. */
export function captionLines(event:CaptionEvent,width:number,height:number,time?:number):Word[][] {
 const words=event.words;
 if(words.length<2||!event.text)return [words];
 // Renderer work-area side margins are 2.5% each.
 const available=width*.95;
 const widths=words.map(w=>nominalWidth(w.text+' ',Math.max(1,Math.round(height*effectiveSize(w,event)/100)),event.style.width_mode==='manual'?event.style.width:w.source_model&&!w.manual_override&&Math.abs(w.width-100)<15?100:w.width));
 if(height>width){
  const pages:Word[][]=[];let group:Word[]=[],used=0;
  for(let i=0;i<words.length;i++){if(group.length&&used+widths[i]>available){pages.push(group);group=[];used=0;}group.push(words[i]);used+=widths[i];}if(group.length)pages.push(group);
  if(time===undefined)return pages;
  let selected=0;for(let i=1;i<pages.length;i++)if(time>=pages[i][0].start)selected=i;
  return [pages[selected]??words];
 }
 if(widths.reduce((a,b)=>a+b,0)<=available)return [words];
 let used=0,split=1;
 for(let i=0;i<widths.length;i++){if(used+widths[i]>available&&i>0){split=i;break;}used+=widths[i];split=words.length-1;}
 return [words.slice(0,split),words.slice(split)];
}

export function captionLineGap(event:CaptionEvent,lines:Word[][],height:number,sourceHeight:number) {
 if(lines.length<2)return 0;
 const base=Math.max(1,Math.round(sourceHeight*.05));
 const maxSecond=Math.max(...lines[1].map(w=>Math.max(1,Math.round(sourceHeight*effectiveSize(w,event)/100))));
 const offset=Math.round(maxSecond*1.5)+2*Math.max(6,Math.round(base*.3))+Math.max(2,Math.round(base*.12));
 return Math.max(0,(offset-base-2*event.style.box_padding)*height/sourceHeight);
}
