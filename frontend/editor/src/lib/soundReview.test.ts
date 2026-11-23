import {describe,it,expect} from 'vitest';
import {soundNeedsReview} from './soundReview';
import {createDemoProject} from './demoProject';
describe('sound suggestion review',()=>{
 it('flags only pending sourced sound events',()=>{
  const event=createDemoProject().events[0];
  event.type='sound_effect' as any;event.review_state='pending' as any;event.source_model='HeuristicClassifier';
  expect(soundNeedsReview(event)).toBe(true);
  event.review_state='accepted' as any;expect(soundNeedsReview(event)).toBe(false);
  event.review_state='corrected' as any;expect(soundNeedsReview(event)).toBe(false);
  event.review_state='pending' as any;event.type='dialogue' as any;expect(soundNeedsReview(event)).toBe(false);
  event.type='music' as any;event.source_model=null;expect(soundNeedsReview(event)).toBe(false);
 });
});
