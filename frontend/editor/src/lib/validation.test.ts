import {wordsError} from './validation';
import {describe,it,expect} from 'vitest';
import {DemoClient,createDemoProject} from './demoProject';
import {parseProject} from './projectFile';
describe('atomic local validation',()=>{
 it('rejects invalid style without adding undo history',async()=>{
  const c=new DemoClient();const e=(await c.getEvents()).data![0];
  const before=structuredClone(e.style);
  expect((await c.setStyle(e.id,{box_opacity:2})).success).toBe(false);
  expect((await c.getEvents()).data![0].style).toEqual(before);
  expect((await c.canUndo()).data!.can_undo).toBe(false);
 });
 it('rejects invalid word opacity and pitch',async()=>{
  const c=new DemoClient();const e=(await c.getEvents()).data!.find(e=>e.words.length)!;
  for(const updates of [{opacity:2},{pitch_hz:-1},{weight:0}])expect((await c.updateWord(e.id,0,updates)).success).toBe(false);
  expect((await c.canUndo()).data!.can_undo).toBe(false);
 });
 it('rejects malformed imported word values and growth settings',()=>{
  const p=createDemoProject();p.events[0].words[0].opacity=2;
  expect(()=>parseProject(JSON.stringify(p))).toThrow();
  p.events[0].words[0].opacity=1;p.events[0].style.escalation_rate=-1;
  expect(()=>parseProject(JSON.stringify(p))).toThrow();
 });
});

describe('speaker identity protection',()=>{
 it('keeps IDs stable and rejects malformed speaker fields without history',async()=>{
  const c=new DemoClient();const s=(await c.getSpeakers()).data![0];
  await c.updateSpeaker(s.id,{id:'changed',name:'Renamed'});
  expect((await c.getSpeakers()).data![0].id).toBe(s.id);
  const before=(await c.getSpeakers()).data;
  expect((await c.updateSpeaker(s.id,{color:'invalid'})).success).toBe(false);
  expect((await c.getSpeakers()).data).toEqual(before);
 });
});

describe('nested word timing edits',()=>{
 it('retimes syllables with a word and restores them on undo',async()=>{
  const p=createDemoProject();p.events=[{...p.events[0],id:'e',start:0,end:5,text:'hello',words:[{...p.events[0].words[0],text:'hello',start:1,end:2,syllables:[{text:'hel',start:1,end:1.5},{text:'lo',start:1.5,end:2}]}]}];
  const c=new DemoClient(p);await c.updateWord('e',0,{start:2,end:4});
  expect((await c.getEvents()).data![0].words[0].syllables).toEqual([{text:'hel',start:2,end:3},{text:'lo',start:3,end:4}]);
  await c.undo();expect((await c.getProject()).data).toEqual(p);
 });
 it('rejects invalid timing deltas without undo history',async()=>{
  const c=new DemoClient();const e=(await c.getEvents()).data![0];
  expect((await c.adjustWordTiming(e.id,0,100,0)).success).toBe(false);
  expect((await c.canUndo()).data!.can_undo).toBe(false);
 });
});

it('rejects malformed syllable pitches',()=>{const word=createDemoProject().events[0].words[0];expect(wordsError([{...word,syllables:[{text:'a',start:word.start,end:word.end,pitch_hz:-1}]}])).toContain('Syllable pitch');});

it('rejects syllables outside their word on import and edit without history',async()=>{
 const p=createDemoProject(),w=p.events[0].words[0];
 const syllables=[{text:w.text,start:w.start,end:w.end+1}];
 p.events[0].words[0].syllables=syllables;
 expect(()=>parseProject(JSON.stringify(p))).toThrow('inside their word');
 const c=new DemoClient();const e=(await c.getEvents()).data![0];
 expect((await c.updateWord(e.id,0,{syllables})).success).toBe(false);
 expect((await c.canUndo()).data!.can_undo).toBe(false);
});

it('keeps event-only punctuation when editing word typography and timing',async()=>{
 const p=createDemoProject();const e=p.events[0];e.text='"'+e.words.map(w=>w.text).join(' ')+'."';
 const c=new DemoClient(p);await c.updateWord(e.id,0,{weight:800});
 expect((await c.getEvents()).data![0].text).toBe(e.text);
 await c.updateWord(e.id,0,{start:e.words[0].start+.001});
 expect((await c.getEvents()).data![0].text).toBe(e.text);
});

it('replaces only the selected repeated word and keeps mapped punctuation',async()=>{
 const p=createDemoProject();const template=p.events[0].words[0];
 p.events=[{...p.events[0],id:'e',start:0,end:3,text:'"go, go!"',words:[{...template,text:'go',start:0,end:1},{...template,text:'go',start:1,end:2}]}];
 const c=new DemoClient(p);await c.updateWord('e',1,{text:'stay'});
 expect((await c.getEvents()).data![0].text).toBe('"go, stay!"');
 await c.undo();expect((await c.getEvents()).data![0].text).toBe('"go, go!"');
});

it('roundtrips character colors and rejects malformed overrides atomically',async()=>{
 const p=createDemoProject();p.events[0].words[0].character_colors=[null,'#FF0000'];
 expect(parseProject(JSON.stringify(p)).events[0].words[0].character_colors).toEqual([null,'#FF0000']);
 const c=new DemoClient(p);expect((await c.updateWord(p.events[0].id,0,{character_colors:['bad']})).success).toBe(false);expect((await c.canUndo()).data!.can_undo).toBe(false);
});
it('validates video grades before recording history',async()=>{
 const c=new DemoClient();expect((await c.updateProject({video:{brightness:2}})).success).toBe(false);expect((await c.canUndo()).data!.can_undo).toBe(false);
});
it('clears stale character overrides when edited word text changes',async()=>{
 const p=createDemoProject();const e=p.events[0];e.words[0].character_colors=['#ff0000'];const c=new DemoClient(p);
 await c.updateWord(e.id,0,{text:'changed'});expect((await c.getEvents()).data![0].words[0].character_colors).toBeNull();
 await c.undo();expect((await c.getEvents()).data![0].words[0].character_colors).toEqual(['#ff0000']);
});
