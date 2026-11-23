import {useEffect,useRef,useState} from 'react';
/** Keep typing local while slow transports catch up. Blur flushes immediately. */
export function DraftText({value,onCommit,multiline=false,...props}: {
 value:string;onCommit:(v:string)=>void;multiline?:boolean;
 className?:string;style?:React.CSSProperties;rows?:number;'aria-label'?:string;
}) {
 const [draft,setDraft]=useState(value);const focused=useRef(false);
 const timer=useRef<ReturnType<typeof setTimeout>>();const pending=useRef<string|null>(null);
 const commit=useRef(onCommit);commit.current=onCommit;
 const flush=()=>{clearTimeout(timer.current);if(pending.current!==null){commit.current(pending.current);pending.current=null;}};
 useEffect(()=>{if(!focused.current&&pending.current===null)setDraft(value);},[value]);
 useEffect(()=>()=>{clearTimeout(timer.current);},[]);
 const shared={...props,value:draft,onFocus:()=>{focused.current=true;},onChange:(e:React.ChangeEvent<HTMLInputElement|HTMLTextAreaElement>)=>{const v=e.target.value;setDraft(v);pending.current=v;clearTimeout(timer.current);timer.current=setTimeout(flush,160);},onBlur:()=>{focused.current=false;flush();}};
 return multiline?<textarea {...shared}/>:<input {...shared}/>;
}
