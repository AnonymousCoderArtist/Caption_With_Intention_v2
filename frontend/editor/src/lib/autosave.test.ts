import {describe,it,expect} from 'vitest';
import {createDemoProject} from './demoProject';
import {STORAGE_KEY} from './projectFile';
import {readLocalRecovery,writeLocalAutosave,RECOVERY_KEY,AUTOSAVE_META_KEY} from './autosave';
class MemoryStorage{
 data=new Map<string,string>();fail=false;
 getItem(key:string){return this.data.get(key)??null;}
 setItem(key:string,value:string){if(this.fail)throw new Error('quota');this.data.set(key,value);}
}
describe('local autosave recovery',()=>{
 it('retains the previous valid project and does not rotate an identical save',()=>{
  const store=new MemoryStorage();const project=createDemoProject();writeLocalAutosave(store,project,10);
  const first=store.getItem(STORAGE_KEY);project.project_name='New title';writeLocalAutosave(store,project,20);
  expect(store.getItem(RECOVERY_KEY)).toBe(first);writeLocalAutosave(store,project,30);expect(store.getItem(RECOVERY_KEY)).toBe(first);
  expect(JSON.parse(store.getItem(AUTOSAVE_META_KEY)!).savedAt).toBe(30);
 });
 it('recovers the previous snapshot if current is corrupt without overwriting the backup',()=>{
  const store=new MemoryStorage();const project=createDemoProject();store.setItem(RECOVERY_KEY,JSON.stringify(project));store.setItem(STORAGE_KEY,'broken');
  expect(readLocalRecovery(store)).toMatchObject({from:'previous',corruptCurrent:true});
  writeLocalAutosave(store,project);expect(JSON.parse(store.getItem(RECOVERY_KEY)!).project_name).toBe(project.project_name);
 });
 it('keeps saved bytes intact on quota failure and reports the failure',()=>{
  const store=new MemoryStorage();const project=createDemoProject();writeLocalAutosave(store,project);const saved=store.getItem(STORAGE_KEY);store.fail=true;
  project.project_name='Not saved';expect(()=>writeLocalAutosave(store,project)).toThrow();expect(store.getItem(STORAGE_KEY)).toBe(saved);
 });
 it('rejects invalid snapshots before touching stored data',()=>{
  const store=new MemoryStorage();const project=createDemoProject();writeLocalAutosave(store,project);const saved=store.getItem(STORAGE_KEY);
  project.video.width=-1;expect(()=>writeLocalAutosave(store,project)).toThrow();expect(store.getItem(STORAGE_KEY)).toBe(saved);
 });
 it('tolerates unavailable storage on read',()=>{
  expect(readLocalRecovery({getItem(){throw new Error('blocked');},setItem(){}}).project).toBeNull();
 });
});
