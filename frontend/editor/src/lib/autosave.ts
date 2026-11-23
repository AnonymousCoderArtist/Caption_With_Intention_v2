import type {Project} from '@/types/project';
import {parseProject,STORAGE_KEY} from './projectFile';
export const RECOVERY_KEY=STORAGE_KEY+':previous';
export const AUTOSAVE_META_KEY=STORAGE_KEY+':meta';
export interface StoragePort{getItem(key:string):string|null;setItem(key:string,value:string):void;}
export const browserStorage:StoragePort={getItem:key=>window.localStorage.getItem(key),setItem:(key,value)=>window.localStorage.setItem(key,value)};
export interface LocalRecovery{project:Project|null;from:'current'|'previous'|null;corruptCurrent:boolean;}
export function readLocalRecovery(storage:StoragePort):LocalRecovery{
 let corruptCurrent=false;
 try{const raw=storage.getItem(STORAGE_KEY);if(raw){try{return {project:parseProject(raw),from:'current',corruptCurrent:false};}catch{corruptCurrent=true;}}}catch{return {project:null,from:null,corruptCurrent:false};}
 try{const raw=storage.getItem(RECOVERY_KEY);if(raw)return {project:parseProject(raw),from:'previous',corruptCurrent};}catch{/* Never replace unreadable saved data with a fabricated project. */}
 return {project:null,from:null,corruptCurrent};
}
export function previousRecovery(storage:StoragePort):Project|null{
 try{const raw=storage.getItem(RECOVERY_KEY);return raw?parseProject(raw):null;}catch{return null;}
}
export function writeLocalAutosave(storage:StoragePort,project:Project,now=Date.now()):number{
 const next=JSON.stringify(project);
 // Validate before touching either saved copy.
 parseProject(next);
 const current=storage.getItem(STORAGE_KEY);
 if(current!==next&&current){
  try{parseProject(current);storage.setItem(RECOVERY_KEY,current);}catch{/* Backup is best effort; never overwrite a valid backup with corrupt current data. */}
 }
 // setItem is atomic per key. If quota blocks it, the current saved copy survives.
 storage.setItem(STORAGE_KEY,next);
 try{storage.setItem(AUTOSAVE_META_KEY,JSON.stringify({savedAt:now,projectName:project.project_name}));}catch{/* Snapshot is saved even if optional timestamp metadata cannot be. */}
 return now;
}
export function savedAt(storage:StoragePort):number|null{
 try{const value=JSON.parse(storage.getItem(AUTOSAVE_META_KEY)||'null');return Number.isFinite(value?.savedAt)?value.savedAt:null;}catch{return null;}
}
