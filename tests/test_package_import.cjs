const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const settle=()=>new Promise(resolve=>setImmediate(resolve));
function setup(){
  const nodes=Object.fromEntries(['media-import','media-task','media-file'].map(id=>[id,{value:'',addEventListener(k,fn){this[k]=fn;}}]));
  const requests=[],saved=[],messages=[];const window={};
  vm.runInNewContext(fs.readFileSync('app/static/organization-os/package-import.js','utf8'),{window,document:{getElementById:id=>nodes[id]}});
  const importer=window.PackageImport.create({request:async(path,options)=>{requests.push({path,options});return {artifact_id:7};},
    act:fn=>fn().catch(e=>messages.push(e.message)),onSaved:async p=>saved.push(p),message:text=>messages.push(text)});
  nodes['media-task'].value='13';
  const select=(text,size=100)=>nodes['media-file'].files=[{size,text:typeof text==='function'?text:async()=>text}];
  return {nodes,requests,saved,messages,importer,select,submit:()=>nodes['media-import'].submit({preventDefault(){}})};
}
const payload=JSON.stringify({purpose:'Synthetic',files:{'app.py':'text'},images:{'static/image.png':'base64'}});
test('import sends complete selected package and opens saved version without execution',async()=>{
  const ui=setup();ui.select(payload);ui.submit();await settle();
  assert.equal(ui.requests.length,1);assert.equal(ui.requests[0].path,'/api/tasks/13/workspace-media-packages');
  assert.equal(ui.requests[0].options.method,'POST');assert.deepEqual(JSON.parse(ui.requests[0].options.body),JSON.parse(payload));
  assert.equal(ui.saved[0].artifact_id,7);assert.match(ui.messages[0],/Zapisano paczkę #7/);
});
test('logout during file read prevents sending sources or restoring selected package',async()=>{
  const ui=setup();let release;ui.select(()=>new Promise(resolve=>release=resolve));
  ui.submit();ui.importer.clear();release(payload);await settle();
  assert.equal(ui.requests.length,0);assert.equal(ui.saved.length,0);assert.equal(ui.nodes['media-task'].value,'');
});
test('invalid or oversized import is rejected before sending to server',async()=>{
  for(const [text,size] of [['not json',100],['{}',100],[payload,24*1024*1024+1]]){
    const ui=setup();ui.select(text,size);ui.submit();await settle();
    assert.equal(ui.requests.length,0);assert.equal(ui.messages.length,1);
  }
});
