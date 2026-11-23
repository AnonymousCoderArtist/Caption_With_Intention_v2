import {describe,it,expect} from 'vitest';
import {packIntervals} from './timelineLayout';
import {createDemoProject} from './demoProject';
describe('timeline overlap packing',()=>{
 it('puts overlapping captions on separate lanes without mutating input',()=>{
  const e=createDemoProject().events[0];const input=[{...e,id:'b',start:1,end:3},{...e,id:'a',start:0,end:2},{...e,id:'c',start:2,end:4}];
  const rows=packIntervals(input);expect(rows.map(r=>r.map(e=>e.id))).toEqual([['a','c'],['b']]);expect(input[0].id).toBe('b');
 });
 it('packs touching intervals together',()=>{const e=createDemoProject().events[0];expect(packIntervals([{...e,start:0,end:1},{...e,start:1,end:2}])).toHaveLength(1)});
 it('handles empty input',()=>expect(packIntervals([])).toEqual([]));
});

import {timelineTicks} from './timelineLayout';
describe('bounded long-video rulers',()=>{
 it('keeps a two-hour ruler below501ticks',()=>expect(timelineTicks(7200,60).length).toBeLessThanOrEqual(501));
 it('retains one-second ticks for short projects',()=>expect(timelineTicks(3,60)).toEqual([0,1,2,3]));
 it('rejects invalid ranges',()=>{expect(timelineTicks(Infinity,60)).toEqual([]);expect(timelineTicks(-1,60)).toEqual([])});
});

import {speakerLanes} from './timelineLayout';
it('separates named speakers and keeps same-speaker overlaps editable',()=>{
 const p=createDemoProject(),e=p.events[0],a=p.speakers[0],b=p.speakers[1];
 const lanes=speakerLanes([{...e,id:'a',speaker_id:a.id,start:0,end:3},{...e,id:'b',speaker_id:b.id,start:0,end:3},{...e,id:'c',speaker_id:a.id,start:1,end:2}], [a,b]);
 expect(lanes.filter(l=>l.key.startsWith('speaker:')).map(l=>l.events.map(e=>e.id))).toEqual([['a'],['c'],['b']]);
 expect(lanes[0].label).toBe(a.name);expect(lanes[0].color).toBe(a.color);
});
