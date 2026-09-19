const {test}=require('node:test');
const assert=require('node:assert/strict');
const {flightFrame}=require('../app/static/organization-os/studio-gallery.js');
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
