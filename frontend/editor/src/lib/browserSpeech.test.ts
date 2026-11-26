import {describe,expect,it} from 'vitest';
import {assembleTranscript} from './browserSpeech';

describe('assembleTranscript',()=>{
 it('builds ordered non-overlapping entries',()=>{
  const t=assembleTranscript([
   {text:'Hello there',at:2.0,confidence:0.9},
   {text:'a second much longer phrase to read',at:6.0},
  ]);
  expect(t).toHaveLength(2);
  expect(t[0].text).toBe('Hello there');
  expect(t[0].end).toBe(2);
  expect(t[0].start).toBeGreaterThanOrEqual(0);
  expect(t[0].start).toBeLessThan(t[0].end);
  expect(t[0].confidence).toBe(0.9);
  expect(t[1].start).toBeGreaterThanOrEqual(t[0].end);
  expect(t[1].confidence).toBeUndefined();
 });

 it('drops empty pieces and normalizes whitespace',()=>{
  const t=assembleTranscript([{text:'   ',at:1},{text:'  many   spaces\nhere ',at:2}]);
  expect(t).toHaveLength(1);
  expect(t[0].text).toBe('many spaces here');
 });

 it('estimates the start from word count',()=>{
  const t=assembleTranscript([{text:'one two three four',at:10}]);
  expect(t[0].start).toBeCloseTo(10-(0.34*4+0.25),3);
 });

 it('keeps entries monotonic when results arrive early',()=>{
  const t=assembleTranscript([{text:'first',at:1},{text:'second',at:1.1}]);
  expect(t[1].end).toBeGreaterThan(t[0].end);
  expect(t[1].start).toBeLessThan(t[1].end);
  expect(t[1].start).toBeGreaterThanOrEqual(0);
 });

 it('clamps the estimated duration for long utterances',()=>{
  const words=Array.from({length:80},()=>'word').join(' ');
  const t=assembleTranscript([{text:words,at:30}]);
  expect(t[0].end-t[0].start).toBeLessThanOrEqual(12);
 });

 it('rejects out-of-range confidence but keeps the text',()=>{
  const t=assembleTranscript([{text:'hi',at:1,confidence:2}]);
  expect(t[0].confidence).toBeUndefined();
 });
});
