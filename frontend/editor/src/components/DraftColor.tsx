import {useEffect,useState} from 'react';
/** Keep native color-picker input local until the picker loses focus. */
export function DraftColor({value,onCommit,...props}:{value:string;onCommit:(color:string)=>void;'aria-label'?:string}){
 const [draft,setDraft]=useState(value);
 useEffect(()=>setDraft(value),[value]);
 return <input {...props} type="color" value={draft} onChange={e=>setDraft(e.target.value)} onBlur={e=>{if(e.target.value!==value)onCommit(e.target.value);}}/>;
}
