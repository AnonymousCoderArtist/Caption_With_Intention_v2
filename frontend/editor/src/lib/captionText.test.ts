import {describe,it,expect} from 'vitest';
import {displayWords} from './captionText';
import {createDemoProject} from './demoProject';
import {EventType} from '@/types/project';
describe('caption display punctuation',()=>{
 const event=createDemoProject().events[0];
 it('preserves music symbols already present',()=>{
  expect(displayWords({...event,type:EventType.Music,text:'♪ quiet strings ♪'})[0].text).toBe('♪ quiet strings ♪');
  expect(displayWords({...event,type:EventType.Music,text:'[quiet strings]'})[0].text).toBe('♪ quiet strings ♪');
 });
 it('brackets SFX without changing saved words',()=>{
  const source={...event,type:EventType.SoundEffect,text:'GASP',words:[{...event.words[0],text:'GASP'}]};
  expect(displayWords(source)[0].text).toBe('[GASP]');expect(source.words[0].text).toBe('GASP');
 });
 it('preserves spaces in untimed captions and supplies baseline typography',()=>{
  const word=displayWords({...event,words:[],text:'soft strings'})[0];
  expect(word.text).toBe('soft strings');expect(word.size_pct).toBe(5);
 });
});

it('keeps event-only punctuation without mutating timed word tokens',()=>{
 const event=createDemoProject().events[0],words=[{...event.words[0],text:'One'},{...event.words[0],text:'two'}];
 expect(displayWords({...event,text:'One, two!',words}).map(w=>w.text)).toEqual(['One,','two!']);
 expect(words.map(w=>w.text)).toEqual(['One','two']);
 expect(displayWords({...event,text:'different transcript',words}).map(w=>w.text)).toEqual(['One','two']);
});
