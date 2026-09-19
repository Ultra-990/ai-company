const {test}=require('node:test');
const assert=require('node:assert/strict');
const {flightFrame}=require('../app/static/organization-os/studio-gallery.js');
const {sceneFrame,springStep,trailPath}=require('../app/static/organization-os/studio-scene.js');
const {buildBrief}=require('../app/static/organization-os/studio-tools.js');
const {blankTarget}=require('../app/static/organization-os/studio-navigation.js');
test('empty-background navigation excludes controls, text and form containers',()=>{
 assert.equal(blankTarget(null),false);
 for(const tagName of ['BODY','MAIN','SECTION','ARTICLE','DIV'])assert.equal(blankTarget({tagName,closest:()=>null}),true);
 for(const tagName of ['INPUT','BUTTON','A','P','IMG','TEXTAREA'])assert.equal(blankTarget({tagName,closest:()=>null}),false);
 assert.equal(blankTarget({tagName:'DIV',closest:()=>({tagName:'FORM'})}),false);
});
test('spring overshoots, converges, and is stable at low frame rates',()=>{
 for(const dt of [1/120,1/60,1/20,1]){
  let s={value:0,velocity:0},peak=0;
  for(let i=0;i<1500;i++){s=springStep(s,100,dt,85);peak=Math.max(peak,s.value);assert.ok(Number.isFinite(s.value)&&Math.abs(s.value)<160);}
  assert.ok(peak>100);assert.equal(s.value,100);assert.equal(s.velocity,0);
 }
});
test('spatial paths change all axes, are bounded, and face forward at focus',()=>{
 for(const mode of ['helix','orbit','wave']){
  const p=sceneFrame(.6,1,1200,mode,1.4),center=sceneFrame(1,1,1200,mode);
  assert.ok(p.x!==0&&p.y!==0&&p.z<0);assert.ok(p.rx!==0||p.ry!==0||p.rz!==0);
  assert.equal(Math.abs(center.rx)+Math.abs(center.ry)+Math.abs(center.rz),0);
  const path=trailPath(.6,1200,800,mode);assert.ok(path.startsWith('M'));assert.equal(path.includes('NaN'),false);
 }
});
test('brief is explicit local scope with independent acceptance and no execution claim',()=>{
 const text=buildBrief('platform','Portal z wyszukiwaniem',['search','accounts','search']);
 assert.ok(text.includes('Portal z wyszukiwaniem'));assert.ok(text.includes('Testy odmowy dostępu'));
 assert.equal((text.match(/Wyszukiwanie/g)||[]).length,1);assert.ok(text.includes('Nie uruchomiono AI'));
 for(const args of [['__proto__','',[]],['website','x'.repeat(601),[]],['website','',['constructor']]])assert.throws(()=>buildBrief(...args));
});
test('scene scroll brings each picture forward without rotating or distorting it',()=>{
 const far=sceneFrame(0,1,1200),near=sceneFrame(.8,1,1200),center=sceneFrame(1,1,1200);
 assert.ok(far.z<near.z&&near.z<center.z);
 assert.equal(center.x,0);assert.equal(center.z,-0);assert.equal(center.opacity,1);
 assert.equal(far.opacity,1);assert.equal(near.opacity,1); // No ghosting between foreground pictures.
 assert.ok(far.saturation<near.saturation&&near.saturation<center.saturation);
 assert.ok(1/(1-far.z/1000)<1/(1-near.z/1000));
 assert.deepEqual(sceneFrame(-10,0,1200),sceneFrame(0,0,1200));
 assert.deepEqual(sceneFrame(10,2,1200),sceneFrame(2,2,1200));
});
test('portrait card flies with uniform scale and horizontal crop, not distortion',()=>{
 const frame=flightFrame({left:100,top:200,width:300,height:400},{left:200,top:100,width:900,height:600});
 assert.equal(frame.transform,'translate(-250px, 100px) scale(0.6666666666666666)');
 assert.equal(frame.clipPath,'inset(0% 25%)');
});
test('landscape source keeps its full aspect ratio',()=>{
 const frame=flightFrame({left:0,top:0,width:300,height:200},{left:100,top:100,width:900,height:600});
 assert.equal(frame.clipPath,'inset(0% 0%)');
 assert.equal(frame.transform,'translate(-100px, -100px) scale(0.3333333333333333)');
});
test('zero-size, invalid or missing rectangles do not produce NaN animations',()=>{
 for(const width of [0,-1,NaN,Infinity,undefined])assert.equal(flightFrame({left:0,top:0,width,height:100},{left:0,top:0,width:900,height:600}),null);
 for(const missing of [null,undefined]){
  assert.equal(flightFrame(missing,{left:0,top:0,width:900,height:600}),null);
  assert.equal(flightFrame({left:0,top:0,width:900,height:600},missing),null);
 }
});
