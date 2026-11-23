import { describe, expect, it } from 'vitest';
import { DemoClient, createDemoProject } from './demoProject';
import { ASS_EM_SCALE, activeCaptionEvents, effectiveSize, envelope, letterLift, letterSpoken, MOTION, sizeAt } from './captionMotion';
import { EventType } from '@/types/project';
const event = () => createDemoProject().events.find(e => e.words.length)!;
describe('stable caption motion', () => {
  it('maps bundled Roboto Flex em sizes to libass REAL_DIM', () => {
    expect(ASS_EM_SCALE).toBeCloseTo(2048 / 3061);
  });
  it('returns exactly to baseline and never goes below it', () => {
    expect(envelope(-1)).toBe(0); expect(envelope(60)).toBe(1); expect(envelope(200)).toBe(0);
    for(let t=0;t<400;t++) expect(envelope(t)).toBeGreaterThanOrEqual(0);
  });
  it('bounds the pitch lift and leaves no held tail', () => {
    const w = {...event().words[0],start:1,end:1.5,pitch_hz:400};
    expect(letterLift(w,0,5,1.06,100,1.25)).toBeCloseTo(14);
    expect(letterLift(w,0,5,2,100,1.25)).toBe(0);
    expect(letterLift(w,0,5,1.06,100,1)).toBe(0);
  });
  it('stabilizes ordinary machine sizes, keeps deliberate manual edits', () => {
    const e = event(), w = {...e.words[0],source_model:'asr',size_pct:7};
    e.style.size_mode = 'auto'; expect(effectiveSize(w,e)).toBe(5);
    e.style.size_mode = 'manual';e.style.size_pct=9;expect(effectiveSize(w,e)).toBe(9);
  });
  it('uses syllable pitch when no per-letter pitch is provided', () => {
    const w={...event().words[0],text:'hello',start:1,end:2,pitch_hz:180,
      syllables:[{text:'hel',start:1,end:1.6,pitch_hz:250},{text:'lo',start:1.6,end:2,pitch_hz:110}]};
    expect(letterLift(w,0,5,1.06,100,1.25)).toBeCloseTo(14);
    expect(letterLift(w,3,5,1.66,100,1.25)).toBeCloseTo(10);
    w.letter_pitches=[180];expect(letterLift(w,0,5,1.06,100,1.25)).toBeCloseTo(12);
  });
  it('gates loud growth and resets after the spoken window', () => {
    const e = event(), w = {...e.words[0],start:1,end:3,size_pct:10,source_model:null};
    e.style.size_mode='auto';e.style.maximum_pct=30;
    expect(sizeAt(w,e,.9,100)).toBe(100);
    expect(sizeAt(w,e,1.3,100)).toBeCloseTo(200);
    expect(sizeAt(w,e,2,100)).toBeGreaterThan(200);
    expect(sizeAt(w,e,3+MOTION.sizeSettleMs/1000,100)).toBe(100);
  });
  it('sweeps letters from their own absolute onset', () => {
    const w={...event().words[0],start:1,end:2};
    expect(letterSpoken(w,3,5,1.5)).toBe(false);expect(letterSpoken(w,3,5,1.61)).toBe(true);
  });
  it('composites all active events with SFX first and later speech above earlier', () => {
    const a={...event(),id:'a',start:0,end:4},b={...event(),id:'b',start:1,end:3};
    const sfx={...event(),id:'sfx',type:EventType.SoundEffect,start:0,end:4};
    expect(activeCaptionEvents([a,b,sfx],2).map(e=>e.id)).toEqual(['sfx','b','a']);
    expect(activeCaptionEvents([a,b,sfx],4)).toEqual([]);
  });
});
describe('editable demo data invariants', () => {
  it('synchronizes text and words in one undo step',async()=>{
    const c=new DemoClient();const e=(await c.getProject()).data!.events.find(e=>e.words.length)!;
    await c.updateEvent(e.id,{text:'New text'});
    let now=(await c.getEvents()).data!.find(x=>x.id===e.id)!;
    expect(now.words.map(w=>w.text).join(' ')).toBe('New text');
    expect(now.words[0].start).toBe(e.start);expect(now.words[1].end).toBe(e.end);
    await c.undo();now=(await c.getEvents()).data!.find(x=>x.id===e.id)!;expect(now).toEqual(e);
  });
  it('retimes words proportionally when moving and trimming a caption',async()=>{
    const c=new DemoClient();const e=(await c.getProject()).data!.events.find(e=>e.words.length)!;
    await c.updateEvent(e.id,{start:e.start+1,end:e.end+1});
    const now=(await c.getEvents()).data!.find(x=>x.id===e.id)!;
    expect(now.words[0].start).toBeCloseTo(e.words[0].start+1);
  });
  it('rejects invalid word timings without changing data or undo history',async()=>{
    const c=new DemoClient();const e=(await c.getProject()).data!.events.find(e=>e.words.length)!;
    const r=await c.updateWord(e.id,0,{end:e.end+20});expect(r.success).toBe(false);
    expect((await c.getEvents()).data!.find(x=>x.id===e.id)).toEqual(e);
    expect((await c.canUndo()).data!.can_undo).toBe(false);
  });
  it('does not reuse an existing ID after deletion',async()=>{
    const c=new DemoClient();const events=(await c.getEvents()).data!;await c.removeEvent(events[0].id);
    await c.addEvent({text:'new',start:0,end:1});const ids=(await c.getEvents()).data!.map(x=>x.id);
    expect(new Set(ids).size).toBe(ids.length);
  });
});
