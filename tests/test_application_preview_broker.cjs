const test=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs');
function setup(){
  const checksum='a'.repeat(64),calls=[],messages=[],elements=new Map();let listener,handler;
  const node=()=>({hidden:true,children:[],setAttribute(){},scrollIntoView(){},
    replaceChildren(...children){this.children=children;},addEventListener(event,fn){this[event]=fn;}});
  const get=id=>{if(!elements.has(id))elements.set(id,node());return elements.get(id);};
  const document={getElementById:get,createElement:()=>({...node(),contentWindow:{
    replies:[],postMessage(data){this.replies.push(data);}}})};
  const window={addEventListener(event,fn){listener=fn;}};
  async function request(url,options){
    calls.push({url,options});
    if(!options)return {checksum,files:[{path:'static/main.js'}]};
    const body=JSON.parse(options.body);
    if(body.path!=='/'&&handler)return handler(body);
    return {source_checksum:checksum,assets:{'static/main.js':'/* public */'},
      response:{status:200,body:'<!doctype html><p>Application</p>',content_type:'text/html'}};
  }
  vm.runInNewContext(fs.readFileSync('app/static/organization-os/application-preview.js','utf8'),
    {window,document,crypto:require('node:crypto').webcrypto});
  const preview=window.createApplicationPreview({request,message:m=>messages.push(m)});
  return {checksum,calls,messages,get,preview,setHandler(fn){handler=fn;},
    open:()=>preview.open({task_id:1,package_id:2,package_checksum:checksum}),
    frame:()=>get('application-host').children[0],
    send:(frame,data,origin='null')=>listener({source:frame.contentWindow,origin,data})};
}
test('public assets only in init; foreign windows and nonopaque origins cannot request execution',async()=>{
  const ui=setup();await ui.open();const frame=ui.frame(),count=ui.calls.length;
  await ui.send(frame,{kind:'application-ready'});
  const init=frame.contentWindow.replies[0];
  assert.deepEqual(Object.keys(init).sort(),['files','html','kind']);
  assert.equal(init.files['static/main.js'],'/* public */');
  await ui.send({contentWindow:{}},{kind:'application-request',id:1,path:'/api/total'});
  await ui.send(frame,{kind:'application-request',id:1,path:'/api/total'},'http://127.0.0.1:8000');
  assert.equal(ui.calls.length,count);
});
test('API reply with a different checksum never reaches application as data',async()=>{
  const ui=setup();await ui.open();const frame=ui.frame();
  ui.setHandler(()=>({source_checksum:'b'.repeat(64),response:{status:200,body:'wrong version'}}));
  await ui.send(frame,{kind:'application-request',id:1,path:'/api/total'});
  const reply=frame.contentWindow.replies.at(-1);
  assert.equal(reply.kind,'application-reply');assert(reply.error);assert.equal(reply.response,undefined);
});
test('pending old frame response cannot reach newly opened application or clear its busy state',async()=>{
  const ui=setup();await ui.open();const old=ui.frame();let resolveOld,resolveNew;
  ui.setHandler(()=>new Promise(resolve=>{resolveOld=resolve;}));
  const pending=ui.send(old,{kind:'application-request',id:1,path:'/api/total'});
  await ui.open();const current=ui.frame();
  ui.setHandler(()=>new Promise(resolve=>{resolveNew=resolve;}));
  const active=ui.send(current,{kind:'application-request',id:1,path:'/api/total'});
  resolveOld({source_checksum:ui.checksum,response:{status:200,body:'old'}});await pending;
  assert.equal(old.contentWindow.replies.length,0);assert.equal(current.contentWindow.replies.length,0);
  const count=ui.calls.length;
  await ui.send(current,{kind:'application-request',id:2,path:'/api/total'});
  assert.equal(ui.calls.length,count);assert(current.contentWindow.replies[0].error);
  resolveNew({source_checksum:ui.checksum,response:{status:200,body:'current'}});await active;
  assert.equal(current.contentWindow.replies.at(-1).response.body,'current');
});
test('request budget, local-path restriction and close are enforced before execution',async()=>{
  const ui=setup();await ui.open();const frame=ui.frame(),initial=ui.calls.length;
  await ui.send(frame,{kind:'application-request',id:0,path:'https://example.com/'});
  assert.equal(ui.calls.length,initial);
  for(let id=1;id<=31;id++)await ui.send(frame,{kind:'application-request',id,path:'/api/total'});
  assert.equal(ui.calls.length,initial+30);assert(frame.contentWindow.replies.at(-1).error);
  ui.preview.close();await ui.send(frame,{kind:'application-request',id:32,path:'/api/total'});
  assert.equal(ui.calls.length,initial+30);assert(ui.get('application-preview').hidden);
});
