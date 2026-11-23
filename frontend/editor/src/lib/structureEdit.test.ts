import {describe,it,expect} from 'vitest';
import {structureEdit} from './structureEdit';
import {createDemoProject,DemoClient} from './demoProject';
function project(){const p=createDemoProject(),e=p.events[0];p.events=[{...e,id:'e',start:0,end:3,text:'One two',words:[{...e.words[0],text:'One',start:.1,end:1},{...e.words[0],text:'two',start:1.5,end:2.5}]}];return p;}
describe('caption structure edits',()=>{
 it('splits between words and merges without retiming',()=>{const p=project(),split=structureEdit(p,['e'],'split',1.2);expect(split.events.map(e=>e.text)).toEqual(['One','two']);expect(split.events[1].words[0].start).toBe(1.5);const merged=structureEdit(split,split.events.map(e=>e.id),'merge');expect(merged.events[0].words).toEqual(p.events[0].words);});
 it('rejects splitting inside a word',()=>expect(()=>structureEdit(project(),['e'],'split',.5)).toThrow('between words'));
 it('keeps each successful edit to one undo',async()=>{const p=project(),client=new DemoClient(p);await client.structureEvents(['e'],'split',1.2);await client.undo();expect((await client.getProject()).data).toEqual(p);});
 it('rejects incompatible styles and overlap',()=>{const p=structureEdit(project(),['e'],'split',1.2);p.events[1].style.italic=true;expect(()=>structureEdit(p,p.events.map(e=>e.id),'merge')).toThrow('same speaker');p.events[1].style.italic=false;p.events[1].start=.5;expect(()=>structureEdit(p,p.events.map(e=>e.id),'merge')).toThrow('Overlapping');});
});

it('keeps punctuation stored outside word tokens when splitting',()=>{const p=project();p.events[0].text='One,  two!';const result=structureEdit(p,['e'],'split',1.2);expect(result.events.map(e=>e.text)).toEqual(['One,','two!']);expect(p.events[0].text).toBe('One,  two!');});
