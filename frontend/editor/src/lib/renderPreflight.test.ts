import {describe,it,expect} from 'vitest';
import {renderWarnings} from './renderPreflight';
import {createDemoProject} from './demoProject';
describe('render preflight',()=>{
 const p=createDemoProject();
 it('accepts matching source geometry and sufficient duration',()=>expect(renderWarnings(p,{width:p.video.width,height:p.video.height,duration:p.video.duration})).toEqual([]));
 it('warns when source dimensions change final layout',()=>expect(renderWarnings(p,{width:640,height:480,duration:p.video.duration}).join(' ')).toContain('wrapping and placement'));
 it('warns about captions beyond the source',()=>expect(renderWarnings(p,{width:p.video.width,height:p.video.height,duration:.1}).join(' ')).toContain('will not appear'));
 it('warns on empty caption projects',()=>expect(renderWarnings({...p,events:[]},{width:p.video.width,height:p.video.height,duration:p.video.duration})).toHaveLength(1));
});

it('warns about a materially different source duration but allows frame-rounding differences',()=>{
 const p=createDemoProject();p.video.duration=45;
 expect(renderWarnings(p,{width:p.video.width,height:p.video.height,duration:60}).join(' ')).toContain('matching video');
 expect(renderWarnings({...p,events:[]},{width:p.video.width,height:p.video.height,duration:45.04}).join(' ')).not.toContain('matching video');
});

it('warns about portrait paging and safe-area limits',()=>{const p=createDemoProject();expect(renderWarnings(p,{width:540,height:960,duration:p.video.duration}).join(' ')).toContain('Portrait layout pages');});
