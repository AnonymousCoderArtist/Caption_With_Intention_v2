import {useEffect,useRef,useState} from 'react';
export type GuideWorkspace='edit'|'text'|'color'|'speakers'|'export';
export const guideSteps:[string,string,GuideWorkspace|null,string[]][]=[
 ['Start with a project','Choose your starting point',null,[
  'Open project JSON loads an existing CWI project. Open editor resumes the browser copy when one is available, otherwise it tries the local service or a sample.',
  'New project starts empty. Import video selects the matching local source for preview and rendering. It does not transcribe the video.',
  'Automatic speech analysis currently runs separately through the local command line, not an editor button. Import its project JSON here. Review the transcript and speaker assignments before export.'
 ]],
 ['Find your way','Edit workspace','edit',[
  'Caption cards are on the left, source preview and timeline in the center, selected-caption controls on the right. Click a card or timeline caption to select it.',
  'Play and scrub the source clock. Space plays/pauses outside inputs; Left/Right step one frame. Timeline ruler Home/End goes to either end.',
  'Lightweight preview lowers preview updates to 15 fps. It does not change source frame rate or final export quality.'
 ]],
 ['Fix words and timing','Text workspace','text',[
  'Edit caption text, then leave the field to accept it. Replacing full text redistributes word timing across the caption. Inspect the result and undo if needed.',
  'Open word properties for word timing, typography, syllables and pitch data. Numbers apply on Enter or leaving the field; unfinished drafts are not saved.',
  'Drag caption edges to trim, or the body to move. Split at the playhead between words. Merge compatible non-overlapping captions. Undo/Redo reverses accepted edits.'
 ]],
 ['Review who and what','Speakers workspace','speakers',[
  'Name speakers and set their colors. Use Speaker review, Listen to turn and Next unchecked turn, then assign the correct speaker and mark it checked.',
  'Timing coverage is not identity certainty. Short replies, overlapping voices and automatic speaker links need listening, even when a model supplied a name.',
  'Sound review finds pending sound/music proposals if present. Correct, remove or accept them. Automatic sound suggestions are optional and unverified.'
 ]],
 ['Refine the look','Color and type','color',[
  'Text controls set caption and word typography. Color workspace adjusts the source-video grade. Character color overrides apply to spoken characters; replacing a word clears its character colors.',
  'Shift/Ctrl/Cmd-click to select captions together. Group move and ripple affect captions only, never cut the source video. Copy/Paste style works on a selected caption.',
  'Browser preview and source grade are approximate. Some legacy controls are saved metadata only. Inspect an actual final MP4 for font, motion, overlap and color fidelity.'
 ]],
 ['Keep your work','Browser and disk saves',null,[
  'The tiny check beside the project badge is browser autosave. Click it for saved time, recovery, Save now and JSON download. An exclamation mark means a save needs attention.',
  'Choose disk autosave file adds an optional JSON copy in supported secure-context browsers. You explicitly choose the file and allow access. It can overwrite that chosen file. Reconnect after reload or project change.',
  'Browser storage can be cleared. Disk writes can fail or be interrupted on close. Use one editing tab; download JSON backups. Source video, undo history and unfinished drafts are not included.'
 ]],
 ['Render and inspect','Export workspace','export',[
  'Import the matching source video, then choose Render video and Start local render. This needs the local Python/FFmpeg service, not just the frontend.',
  'The service copies the selected source locally. Maximum source size is 2 GB. Check source/caption warnings, monitor progress or cancel, and keep the tab open during transfer.',
  'For portrait video, long dialogue captions page in source time. Inspect the result: long unbroken words, oversized type and simultaneous speakers can still exceed the safe area.',
  'Play the completed render and download MP4. Local results are retained for one hour. Changes made after a render starts need another render. JSON is the editable project, not a video.'
 ]],
 ['When something looks wrong','Troubleshooting and limits',null,[
  'Missing video after reload: select the same source again. Missing edits: click the save icon and inspect recovery before starting another project.',
  'Failed disk save: browser save remains separate. Reconnect the file explicitly or download JSON. Unsupported file picker: use JSON download.',
  'Render service unavailable: start the editor from the repository root with uv run python engine/editor/start.py after installing its dependencies. Exact official-film parity and automatic recognition accuracy are not certified. This is local development software, not a finished offline installer.'
 ]]
];
export function EditorGuide({onClose,onWorkspace}:{onClose:()=>void;onWorkspace?:(workspace:GuideWorkspace)=>void}){
 const [step,setStep]=useState(0);const close=useRef<HTMLButtonElement>(null);
 useEffect(()=>{const prior=document.activeElement as HTMLElement|null;close.current?.focus();return()=>{if(prior?.isConnected)prior.focus();};},[]);
 const [title,subtitle,workspace,paragraphs]=guideSteps[step];
 return <aside className="editor-guide" role="region" aria-label="Editor guide" onKeyDown={e=>{e.stopPropagation();if(e.key==='Escape')onClose();}}>
  <header><div><span className="guide-eyebrow">AUTOMATED CWI · HOW TO</span><h2>Editor guide</h2></div><button ref={close} onClick={onClose} aria-label="Close editor guide">Close</button></header>
  <p className="guide-intro">A practical walkthrough. Nothing opens automatically, and reading this guide never changes your project.</p>
  <nav aria-label="Guide topics">{guideSteps.map(([name],i)=><button key={name} aria-current={i===step?'step':undefined} onClick={()=>setStep(i)}>{i+1}. {name}</button>)}</nav>
  <article key={step}><span className="guide-eyebrow">STEP {step+1} OF {guideSteps.length}</span><h3>{title}</h3><h4>{subtitle}</h4>{paragraphs.map(p=><p key={p}>{p}</p>)}{workspace&&onWorkspace&&<button className="ghost" onClick={()=>onWorkspace(workspace)}>Show {workspace} workspace</button>}</article>
  <footer><button disabled={step===0} onClick={()=>setStep(s=>s-1)}>Previous</button><span>{step+1} / {guideSteps.length}</span><button onClick={()=>step===guideSteps.length-1?onClose():setStep(s=>s+1)}>{step===guideSteps.length-1?'Done':'Next'}</button></footer>
 </aside>;
}
