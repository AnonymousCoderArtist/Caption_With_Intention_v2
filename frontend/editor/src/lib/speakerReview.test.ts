import {describe,it,expect} from 'vitest';
import {speakerReviewReasons} from './speakerReview';
import {createDemoProject} from './demoProject';
describe('speaker review queue',()=>{
 it('flags unassigned speech and clears after explicit review',()=>{const p=createDemoProject(),e={...p.events[0],speaker_id:null};expect(speakerReviewReasons(e,p.speakers).length).toBeGreaterThan(0);e.speaker_reviewed=true;expect(speakerReviewReasons(e,p.speakers)).toEqual([]);});
 it('does not use text confidence as speaker confidence',()=>{const p=createDemoProject(),e={...p.events[0],confidence:.01};expect(speakerReviewReasons(e,p.speakers)).toEqual([]);});
});

it('batch speaker correction is undoable and marks only chosen captions',async()=>{
 const {DemoClient}=await import('./demoProject');const c=new DemoClient(),p=(await c.getProject()).data!;
 const id=p.events[0].id;await c.assignSpeakerEvents([id],p.speakers[0].id,true);
 expect((await c.getEvents()).data![0].speaker_reviewed).toBe(true);
 await c.undo();expect((await c.getEvents()).data![0]).toEqual(p.events[0]);
});

it('reopens attribution review after deleting a checked caption speaker and undo restores it',async()=>{
 const {DemoClient}=await import('./demoProject');const c=new DemoClient(),p=(await c.getProject()).data!;
 const e=p.events.find(e=>e.speaker_id)!;await c.updateEvent(e.id,{speaker_reviewed:true});
 await c.removeSpeaker(e.speaker_id!);let current=(await c.getProject()).data!;
 expect(speakerReviewReasons(current.events.find(x=>x.id===e.id)!,current.speakers)).toContain('No speaker assigned.');
 await c.undo();current=(await c.getProject()).data!;expect(current.events.find(x=>x.id===e.id)!.speaker_reviewed).toBe(true);expect(current.events.find(x=>x.id===e.id)!.speaker_id).toBe(e.speaker_id);
});
