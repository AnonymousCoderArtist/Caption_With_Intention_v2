import {describe,it,expect} from 'vitest';
import {captionLines,nominalWidth} from './captionLayout';
import {createDemoProject} from './demoProject';
describe('renderer nominal layout',()=>{
 it('uses bundled default-instance advances',()=>expect(nominalWidth('Quiet emphasis settles.',36)).toBeCloseTo(372.5859375,3));
 it('keeps a short caption intact and splits a long caption at word boundaries',()=>{
  const e=createDemoProject().events[0];expect(captionLines(e,1920,1080)).toHaveLength(1);
  const words=Array.from({length:15},()=>({...e.words[0],text:'emphasis'}));const long={...e,words,text:words.map(w=>w.text).join(' ')};
  const lines=captionLines(long,1280,720);expect(lines).toHaveLength(2);expect(lines.flat()).toEqual(words);expect(lines[0].length).toBeGreaterThan(0);expect(lines[1].length).toBeGreaterThan(0);
 });
});
