import {describe,it,expect} from 'vitest';
import {emptyProject,parseProject} from './projectFile';
import {createDemoProject} from './demoProject';
describe('local project files',()=>{
 it('roundtrips a full project',()=>{const p=createDemoProject();expect(parseProject(JSON.stringify(p))).toEqual(p)});
 it('makes a genuinely empty project',()=>{const p=emptyProject();expect(p.events).toEqual([]);expect(p.speakers).toEqual([])});
 it('rejects malformed formats, duplicate IDs and invalid timing',()=>{
  expect(()=>parseProject('{}')).toThrow();
  const p=createDemoProject();p.events[0].end=-1;expect(()=>parseProject(JSON.stringify(p))).toThrow();
  const duplicate=createDemoProject();duplicate.events.push(duplicate.events[0]);expect(()=>parseProject(JSON.stringify(duplicate))).toThrow();
 });
 it('restores defaults missing from older project styles',()=>{const p=createDemoProject();delete (p.events[0].style as any).box_padding;expect(parseProject(JSON.stringify(p)).events[0].style.box_padding).toBe(10)});
});

it('rejects malformed review metadata before it reaches the review queue',()=>{
 const p=createDemoProject();
 for(const value of ['reason',[1],{}]){
  (p.events[0] as any).speaker_review_reasons=value;
  expect(()=>parseProject(JSON.stringify(p))).toThrow('Speaker review reasons');
 }
});

it('rejects malformed metadata that would reach text controls and provenance labels',()=>{
 const cases=[(p:any)=>p.project_name={},(p:any)=>p.scenes='bad',(p:any)=>p.speakers[0].notes={},(p:any)=>p.events[0].source_model={},(p:any)=>p.events[0].words[0].review_state='unknown',(p:any)=>p.events[0].words[0].confidence=2];
 for(const change of cases){const p=createDemoProject();change(p);expect(()=>parseProject(JSON.stringify(p))).toThrow();}
});
