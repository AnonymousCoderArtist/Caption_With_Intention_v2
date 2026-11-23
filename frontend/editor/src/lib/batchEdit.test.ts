import {describe,it,expect} from 'vitest';
import {batchEdit} from './batchEdit';
import {createDemoProject,DemoClient} from './demoProject';
const project=()=>{const p=createDemoProject(),template=p.events[0];p.events=Array.from({length:3},(_,i)=>({...structuredClone(template),id:String(i),start:i*2,end:i*2+1,words:[{...template.words[0],start:i*2,end:i*2+1}]}));return p;};
describe('atomic batch caption edits',()=>{
 it('moves selected and preserves unselected captions',()=>{const p=project(),next=batchEdit(p,['0','1'],'move',.5);expect(next.events.map(e=>e.start)).toEqual([.5,2.5,4]);expect(p.events[0].start).toBe(0);});
 it('ripples later captions and their words',()=>{const next=batchEdit(project(),['0'],'move',1,true);expect(next.events.map(e=>e.start)).toEqual([1,3,5]);expect(next.events[2].words[0].start).toBe(5);});
 it('closes only deleted occupied time, not gaps',()=>expect(batchEdit(project(),['0','1'],'delete',0,true).events[0].start).toBe(2));
 it('validates before one undo commit',async()=>{const p=project(),c=new DemoClient(p);expect((await c.batchEvents(['0'],'move',-1)).success).toBe(false);expect((await c.canUndo()).data!.can_undo).toBe(false);await c.batchEvents(['0','1'],'move',1);await c.undo();expect((await c.getProject()).data).toEqual(p);});
});
