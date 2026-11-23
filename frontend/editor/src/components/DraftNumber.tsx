import {useEffect,useRef,useState} from 'react';
/** Let a number be temporarily empty while typing. Commit on blur or Enter. */
export function DraftNumber({value,onCommit,...props}: {
 value:number;onCommit:(v:number)=>void;min?:number;max?:number;step?:number;
 'aria-label'?:string;className?:string;style?:React.CSSProperties;title?:string;
}) {
 const [draft,setDraft]=useState(String(value));const focused=useRef(false);
 useEffect(()=>{if(!focused.current)setDraft(String(value));},[value]);
 const flush=()=>{
  const n=Number(draft);
  if(!draft.trim()||!Number.isFinite(n)||(props.min!==undefined&&n<props.min)||(props.max!==undefined&&n>props.max))setDraft(String(value));
  else if(n!==value)onCommit(n);
 };
 return <input {...props} type="number" value={draft} onFocus={()=>{focused.current=true;}}
  onChange={e=>setDraft(e.target.value)} onBlur={()=>{focused.current=false;flush();}}
  onKeyDown={e=>{if(e.key==='Enter'){e.preventDefault();e.currentTarget.blur();}else if(e.key==='Escape'){setDraft(String(value));}}}/>;
}
