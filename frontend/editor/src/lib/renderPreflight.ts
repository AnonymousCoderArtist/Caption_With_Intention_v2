import type {Project} from '@/types/project';
export interface MediaInfo {width:number;height:number;duration:number}
export function renderWarnings(project:Project,media:MediaInfo):string[] {
 const messages:string[]=[];
 if(media.width!==project.video.width||media.height!==project.video.height)
  messages.push(`Source is ${media.width}×${media.height}, sequence is ${project.video.width}×${project.video.height}. Final captions use source dimensions, so wrapping and placement may differ from the editor.`);
 if(Number.isFinite(media.duration)&&project.video.duration>0&&Math.abs(media.duration-project.video.duration)>Math.max(.5,project.video.duration*.01))
  messages.push(`Source duration is ${media.duration.toFixed(2)}s, sequence is ${project.video.duration.toFixed(2)}s. Confirm that you selected the matching video; export uses the full source duration.`);
 const last=Math.max(0,...project.events.map(e=>e.end));
 if(Number.isFinite(media.duration)&&last>media.duration+.1)
  messages.push(`Captions end at ${last.toFixed(2)}s but the source ends at ${media.duration.toFixed(2)}s. Captions beyond the source will not appear.`);
 if(!project.events.length)messages.push('This project has no captions. The export will contain only the source video.');
 return messages;
}
export async function inspectMedia(file:File):Promise<MediaInfo> {
 const url=URL.createObjectURL(file),video=document.createElement('video');
 try{return await new Promise((resolve,reject)=>{const timer=setTimeout(()=>{video.src='';reject(new Error('Video metadata timed out. Check that this is the matching source video.'));},10000);
 video.preload='metadata';video.onloadedmetadata=()=>{clearTimeout(timer);resolve({width:video.videoWidth,height:video.videoHeight,duration:video.duration});};
 video.onerror=()=>{clearTimeout(timer);reject(new Error('Your browser cannot inspect this source video. Use the renderer command line for formats the browser cannot decode.'));};video.src=url;});}
 finally{video.removeAttribute('src');video.load();URL.revokeObjectURL(url);}
}
