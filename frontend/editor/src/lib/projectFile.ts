/** Local project files are data. Parse, validate, and supply schema defaults. */
import type { Project, CaptionEvent, Word } from '@/types/project';
import { EventType, ReviewState, SpeakerCategory } from '@/types/project';
import {styleError,wordsError} from './validation';
import { createDemoProject } from './demoProject';
export const STORAGE_KEY = 'cwi-editor-local-v1';
const finite = (v: unknown): v is number => typeof v === 'number' && Number.isFinite(v);
export function emptyProject(): Project {
  const defaults=createDemoProject();
  return {...defaults, project_name:'Untitled Project',video:{...defaults.video,duration:0},events:[],speakers:[],scenes:[],created_at:new Date().toISOString(),modified_at:null};
}
export function parseProject(text: string): Project {
  const data = JSON.parse(text);
  if (!data || typeof data !== 'object' || data.schema_version !== 'ci-project-1' || !Array.isArray(data.events) || !Array.isArray(data.speakers) || !data.video)
    throw new Error('Choose a CWI project JSON file with video, speakers and events.');
  for(const key of ['project_name','design_system','profile_version','notes'])
    if(data[key]!==undefined&&typeof data[key]!=='string')throw new Error('Project names and metadata must be text.');
  if(data.scenes!==undefined&&(!Array.isArray(data.scenes)||data.scenes.some((scene:unknown)=>!scene||typeof scene!=='object'||Array.isArray(scene))))throw new Error('Project scenes must be a list of objects.');
  if (data.events.length > 50000) throw new Error('This project is too large for the browser editor.');
  const defaults = createDemoProject(); const style = defaults.events[0].style;
  const wordDefaults: Word = {text:'',start:0,end:1,size_pct:5,weight:400,width:100,color:'#FFFFFF',opacity:1,italic:false,confidence:null,source_model:null,source_timestamp:null,manual_override:false,review_state:ReviewState.Pending,syllables:null};
  const validateMetadata=(value:any)=>{
    for(const key of ['source_model','exception_profile'])if(value[key]!=null&&typeof value[key]!=='string')throw new Error('Source labels must be text or null.');
    if(value.review_state!==undefined&&!Object.values(ReviewState).includes(value.review_state))throw new Error('Unknown review status.');
    if(value.confidence!=null&&(!finite(value.confidence)||value.confidence<0||value.confidence>1))throw new Error('Confidence must be between 0 and 1.');
  };
  const events: CaptionEvent[] = data.events.map((e: any) => {
    if (!e || typeof e.id !== 'string' || typeof e.text !== 'string' || !Object.values(EventType).includes(e.type) || !finite(e.start) || !finite(e.end) || e.start < 0 || e.end <= e.start || !Array.isArray(e.words))
      throw new Error('A caption has invalid text, type or timing.');
    validateMetadata(e);
    if(e.speaker_review_reasons!==undefined&&(!Array.isArray(e.speaker_review_reasons)||e.speaker_review_reasons.some((r:unknown)=>typeof r!=='string')))
      throw new Error('Speaker review reasons must be a list of text values.');
    if(e.speaker_id!==null&&e.speaker_id!==undefined&&typeof e.speaker_id!=='string')throw new Error('Speaker assignment must be a speaker ID or null.');
    for(const key of ['speaker_review_required','speaker_reviewed','off_camera','manual_override'])if(e[key]!==undefined&&typeof e[key]!=='boolean')throw new Error('Caption flags must be true or false.');
    if(e.notes!==undefined&&typeof e.notes!=='string')throw new Error('Caption notes must be text.');
    const words = e.words.map((w: any) => {
      if (!w || typeof w.text !== 'string' || !finite(w.start) || !finite(w.end) || w.start < e.start || w.end > e.end + .001 || w.end <= w.start)
        throw new Error('A word has invalid timing outside its caption.');
      validateMetadata(w);
      for(const key of ['italic','manual_override'])if(w[key]!==undefined&&typeof w[key]!=='boolean')throw new Error('Word flags must be true or false.');
      if(w.color!==undefined&&!/^#[0-9a-f]{6}$/i.test(w.color))throw new Error('Word colors must be six-digit hex values.');
      return {...wordDefaults,...w};
    });
    const mergedStyle={...style,...e.style};
    for (const key of ['size_pct','weight','width','read_ahead_opacity','pop_scale','box_opacity','box_padding','minimum_pct','maximum_pct'] as const)
      if (!finite(mergedStyle[key]) || mergedStyle[key]<0) throw new Error('A caption has an invalid style value.');
    if (mergedStyle.read_ahead_opacity>1||mergedStyle.box_opacity>1||mergedStyle.minimum_pct>mergedStyle.maximum_pct||mergedStyle.size_pct<=0)
      throw new Error('A caption has an invalid size or opacity.');
    for(const key of ['size_mode','weight_mode','width_mode'] as const)
      if(!['auto','manual'].includes(mergedStyle[key]))throw new Error('A typography mode must be auto or manual.');
    for(const word of words) {
      for(const key of ['size_pct','weight','width','opacity'] as const)
        if(!finite(word[key])||word[key]<0)throw new Error('A word has invalid typography.');
      if(word.syllables!==null&&(!Array.isArray(word.syllables)||word.syllables.some((sy:any)=>!sy||typeof sy.text!=='string'||!finite(sy.start)||!finite(sy.end)||sy.end<=sy.start)))throw new Error('A word has malformed syllable data.');
      if(word.letter_pitches!=null&&(!Array.isArray(word.letter_pitches)||word.letter_pitches.some((v:any)=>v!==null&&(!finite(v)||v<0))))throw new Error('A word has malformed letter pitches.');
    }
    const validation=styleError(mergedStyle)||wordsError(words);
    if(validation)throw new Error(validation);
    return {...defaults.events[0],...e,words,style:mergedStyle};
  });
  const ids = events.map(e => e.id);
  if (new Set(ids).size !== ids.length) throw new Error('Caption IDs must be unique.');
  const speakers = data.speakers.map((s: any) => {
    if (!s || typeof s.id !== 'string' || typeof s.name !== 'string' || !/^#[0-9a-f]{6}$/i.test(s.color) || !Object.values(SpeakerCategory).includes(s.category))
      throw new Error('A speaker has an invalid name, color or category.');
    validateMetadata(s);
    for(const key of ['off_camera','active_speaker','manual_override'])if(s[key]!==undefined&&typeof s[key]!=='boolean')throw new Error('Speaker flags must be true or false.');
    if(s.notes!==undefined&&typeof s.notes!=='string')throw new Error('Speaker notes must be text.');
    if(s.role!=null&&typeof s.role!=='string')throw new Error('Speaker role must be text or null.');
    return {...defaults.speakers[0],...s};
  });
  if (new Set(speakers.map((s: any)=>s.id)).size !== speakers.length) throw new Error('Speaker IDs must be unique.');
  if (![data.video.width,data.video.height,data.video.fps].every(v=>finite(v)&&v>0) || !finite(data.video.duration) || data.video.duration<0)
    throw new Error('Video dimensions, frame rate and duration must be valid.');
  for(const [key,min,max,fallback] of [['brightness',-.5,.5,0],['contrast',.5,2,1],['saturation',0,2,1]] as const){const v=data.video[key]??fallback;if(!finite(v)||v<min||v>max)throw new Error('Video grade is outside the supported range.');}
  const count=data.video.portrait_words_per_page??0;if(!Number.isInteger(count)||count<0||count>50)throw new Error('Portrait words per page must be an integer from 0 to 50.');
  return {...emptyProject(),...data,events,speakers,video:{...defaults.video,...data.video}};
}
