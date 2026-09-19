import {test} from 'node:test';
import assert from 'node:assert/strict';
import {clamp, sample, wheelStep, zoomStep, focusedPose, relationPairs, atlasAnchors, cameraPose, scrollPosition} from '../app/static/spatial/motion.mjs';

test('camera interpolation reaches exact endpoints and clamps overscroll',()=>{
  const stops=[[0,0,1100],[400,-20,900],[0,30,800]];
  assert.deepEqual(sample(stops,-10),stops[0]);
  assert.deepEqual(sample(stops,9),stops[2]);
  assert.deepEqual(sample(stops,1),stops[1]);
  assert.deepEqual(sample(stops,.5),[200,-10,1000]);
  assert.equal(clamp(5,0,3),3);
});
test('wheel normalizes lines/pages and limits large mouse bursts',()=>{
  assert.equal(wheelStep(1,1,600),wheelStep(16,0,600));
  assert.equal(wheelStep(1,2,600),180/650);
  assert.equal(wheelStep(-5000,0,600),-180/650);
});
test('selected window zoom is bounded and never moves to a different department',()=>{
  const anchors=atlasAnchors(12);
  for(const viewport of [[1440,800],[390,500]])for(let n=1;n<=12;n++){
    const near=focusedPose(anchors,n,...viewport,1.25),far=focusedPose(anchors,n,...viewport,.65);
    assert.deepEqual(near.slice(0,2),far.slice(0,2));assert(near[2]<far[2]);
    assert(near.every(Number.isFinite));
  }
  assert(zoomStep(1,130,0,800)<1);assert(zoomStep(1,-130,0,800)>1);
  assert.equal(zoomStep(.65,5000,0,800),.65);assert.equal(zoomStep(1.25,-5000,0,800),1.25);
});
test('connections require actual registered relations, never imaginary agents',()=>{
  const nodes=[{key:'a',brain_agent_id:2},{key:'b',brain_agent_id:3}];
  const deps=[{source_key:'a',target_key:'b',relation_type:'depends_on'}];
  assert.deepEqual(relationPairs({owner_agent_id:1,brain_agent_id:2},nodes,[...deps,...deps]),[
    ['owner','brain','delegation'],['brain','a','supervision'],['a','b','depends_on'],
  ]);
  assert.deepEqual(relationPairs({},nodes,[]),[]);
  assert.deepEqual(relationPairs({},nodes,[{source_key:'a',target_key:'outside'}]),[]);
});
test('atlas accepts all departments and camera approaches every exact stop',()=>{
  const anchors=atlasAnchors(12);assert.equal(anchors.length,12);
  assert.equal(new Set(anchors.map(String)).size,12);
  for(let i=0;i<12;i++){
    const p=cameraPose(anchors,i+1,1440,840);
    assert.equal(p[0],anchors[i][0]);assert.equal(p[1],anchors[i][1]);
    assert(p[2]>anchors[i][2]);
  }
  const far=cameraPose(anchors,0,1440,840)[2]-anchors[0][2];
  const near=cameraPose(anchors,1,1440,840)[2]-anchors[0][2];
  assert(far/near>2.5,'clear growth, not just lateral movement');
});
test('travel explicitly pulls back between closeups and supports mobile',()=>{
  const a=atlasAnchors(12);
  const first=cameraPose(a,1,390,580),mid=cameraPose(a,1.5,390,580),second=cameraPose(a,2,390,580);
  assert(mid[2]>Math.max(first[2],second[2]));
  assert(cameraPose([],0,390,580).every(Number.isFinite));
});
test('native long scroll maps monotonically to all stops and releases boundaries',()=>{
  assert.equal(scrollPosition(0,300,800,12),0);
  assert.equal(scrollPosition(1100,300,800,12),1);
  assert.equal(scrollPosition(9900,300,800,12),12);
  assert.equal(scrollPosition(30000,300,800,12),12);
});
