import assert from 'node:assert/strict';
import fs from 'node:fs';
import {fileURLToPath} from 'node:url';
import {validate,compose} from './build.mjs';
const fixture=JSON.parse(fs.readFileSync(fileURLToPath(new URL('../assets/project.example.json',import.meta.url)),'utf8'));
let passed=0;
const test=(name,f)=>{f();passed++;console.log('PASS '+name);};
const copy=()=>structuredClone(fixture);
test('derived timeline has exact sequential scene boundaries',()=>{
  const r=validate(fixture,'.',false);
  assert.equal(r.timeline[1].duration,6.04);
  assert.equal(r.timeline[2].start,8.04);
  assert.equal(r.timeline[2].duration,2.6);
  for(let i=1;i<r.timeline.length;i++)assert.ok(Math.abs(r.timeline[i].start-r.timeline[i-1].start-r.timeline[i-1].duration)<1e-6);
});
test('duration override shifts all dependent scenes',()=>{
  const c=copy();c.design={motion:{expand:2}};
  const before=validate(fixture,'.',false),after=validate(c,'.',false);
  assert.equal(after.timeline[3].start,before.timeline[3].start+1);
  assert.equal(after.duration,before.duration+2);
});
test('reject duplicated Q chapter',()=>{
  const c=copy();c.scenes[4].chapter='chapter-one';assert.throws(()=>validate(c,'.',false),/One Q/);
});
test('reject overlapping or overflowing captions',()=>{
  const c=copy();c.scenes[3].captions[1].start=1;assert.throws(()=>validate(c,'.',false),/Captions/);
  c.scenes[3].captions[1].start=2;c.scenes[3].captions[1].end=5;assert.throws(()=>validate(c,'.',false),/Captions/);
});
test('reject absent evidence source',()=>{
  const c=copy();c.scenes[3].evidence[0].media='missing';assert.throws(()=>validate(c,'.',false),/media/);
});
test('reject missing file before build',()=>assert.throws(()=>validate(fixture,'.',true),/Missing media/));
test('reject unsafe style and unsupported frame',()=>{
  let c=copy();c.design={colors:{gradient:['red','#000000','#ffffff']}};assert.throws(()=>validate(c,'.',false),/Colors/);
  c=copy();c.design={frame:{height:1920}};assert.throws(()=>validate(c,'.',false),/1080x1440/);
});
test('reject source trim backwards',()=>{
  const c=copy();c.media.hook.in=3;assert.throws(()=>validate(c,'.',false),/source out/);
});
test('markup escaping and all content comes from config',()=>{
  const c=copy();c.scenes[1].name='<测试&>';
  const r=compose(c,Object.fromEntries(Object.keys(c.media).map(k=>[k,'media/'+k+'.mp4'])));
  assert.ok(r.html.includes('&lt;测试&amp;&gt;'));assert.ok(!r.html.includes('齐钧泽'));
  assert.ok(!r.html.includes('{{BODY}}'));assert.equal(r.cues.length,3);
  assert.equal(r.cues[0].start,10.64);
});
test('one palette updates text and SVG, no old default remains in applied overrides',()=>{
  const c=copy();c.design={colors:{gradient:['#FFC480','#FF9270','#F5D1A0']}};
  const r=compose(c,Object.fromEntries(Object.keys(c.media).map(k=>[k,'media/'+k])));
  assert.ok(r.html.includes('stop-color="#FFC480"'));assert.ok(r.html.includes('--brand-gradient:linear-gradient(96deg,#FFC480'));
});
test('reject invalid bubble origin',()=>{
  const c=copy();c.scenes[4].fromTopic=1;assert.throws(()=>validate(c,'.',false),/fromTopic/);
});
console.log(JSON.stringify({status:'ok',tests:passed}));
