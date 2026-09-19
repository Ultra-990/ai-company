const test=require('node:test'), assert=require('node:assert/strict');
const fs=require('node:fs'), vm=require('node:vm');
const settle=()=>new Promise(resolve=>setImmediate(resolve));

function setup(role='analyst'){
  const elements=new Map(),requests=[],timers=[];
  let failure=false;
  const document={
    getElementById(id){if(!elements.has(id)){const el=document.createElement('div');el.id=id;}return elements.get(id);},
    querySelectorAll(){return [];},hidden:false,
    createElement(tag){let id='';return {
      tagName:tag.toUpperCase(),ownerDocument:document,children:[],dataset:{},value:'',textContent:'',open:false,
      attributes:{},classList:{toggle(){},remove(){},add(){}},
      get id(){return id;},set id(value){id=value;elements.set(value,this);},
      append(...nodes){this.children.push(...nodes);},replaceChildren(...nodes){this.children=nodes;},
      setAttribute(key,value){this.attributes[key]=value;},removeAttribute(key){delete this.attributes[key];},
      addEventListener(event,fn){this[event]=fn;},reset(){},focus(){document.activeElement=this;},
      scrollIntoView(){this.scrolled=true;},closest(){return null;},showModal(){this.open=true;},close(){this.open=false;},
      set innerHTML(value){throw Error('Unsafe HTML');}
    };}
  };
  const stage={task_id:7,title:'Zakres',state:'instruction',reason:'Przygotuj instrukcję',action:'task'};
  const detail={project_id:1,plan_id:2,brief:{title:'Projekt',goal:'Cel',organization_unit_id:3,acceptance_criteria:['Kryterium']},
    tasks:[{id:7,title:'Zakres',status:'pending',progress:0,approval_status:'pending',delegation:null}],artifacts:[],
    guidance:{version:1,stages:[stage],current:stage,accepted_stages:0,total_stages:1},
    coordination:{can_prepare:true,task_id:7,revision:'a'.repeat(64)}};
  const packet={task_id:7,packet_id:9,checksum:'b'.repeat(64),packet:{role}};
  async function fetch(path,options={}){
    requests.push({path,method:options.method||'GET',body:options.body});
    let data;
    if(path.endsWith('/prepare-next')){
      if(failure)return {ok:false,status:409,json:async()=>({detail:'Stan projektu zmienił się.'})};
      data={instruction:packet};
    }else if(path==='/api/work-orders/options')data={units:[{id:3,key:'digital-experience.websites',name:'Strony'}]};
    else if(path==='/api/work-orders')data={orders:[{project_id:1,title:'Projekt'}],next_cursor:null};
    else if(path==='/api/work-orders/1')data=detail;
    else if(path==='/api/tasks/7/agent-packets/9')data=packet;
    else if(path==='/api/local-inference')data={id:20,state:'queued'};
    else if(path==='/api/local-inference/20/run')data={id:20,task_id:7,state:'awaiting_review',metrics:{package_id:30,package_checksum:'c'.repeat(64)}};
    else if(path==='/api/package-runs')data={id:40,state:'passed'};
    else if(path.startsWith('/api/local-inference?'))data={enabled:false,runs:[],attention_count:0,next_cursor:null};
    else throw Error('Unexpected request '+path);
    return {ok:true,json:async()=>data};
  }
  const window={OwnerSession:{active:true,fetch},addEventListener(){}};
  const context={window,document,AbortController,DOMException,URLSearchParams,location:{search:'?project=1'},
    setTimeout,clearTimeout,setInterval:fn=>timers.push(fn),console,crypto:require('node:crypto')};
  vm.runInNewContext(fs.readFileSync('app/static/organization-os/project-guide.js','utf8'),context);
  vm.runInNewContext(fs.readFileSync('app/static/organization-os/work.js','utf8'),context);
  const get=id=>document.getElementById(id);get('inference-scope').value='project';
  const flatten=el=>[el,...el.children.flatMap(flatten)];
  return {get,requests,timers,document,fail:()=>{failure=true;},
    buttons:()=>flatten(get('project-guide')).filter(n=>n.tagName==='BUTTON'),
    connect:()=>get('access').submit({preventDefault(){}})};
}

test('opening project reads data, shows guide and navigates to task without writes',async()=>{
  const ui=setup();ui.connect();await settle();
  assert(ui.get('project-guide').scrolled);
  assert.equal(ui.requests.length,3);
  assert(ui.requests.every(r=>r.method==='GET'));
  ui.buttons()[0].click();
  assert.equal(ui.document.activeElement,ui.get('project-task-7'));
  assert.equal(ui.requests.length,3);
});
test('double click prepares once with checkpoint and opens persisted instruction',async()=>{
  const ui=setup();ui.connect();await settle();
  const button=ui.buttons().find(n=>n.textContent.startsWith('Przygotuj'));
  button.click();button.click();await settle();
  const writes=ui.requests.filter(r=>r.method==='POST');
  assert.equal(writes.length,1);assert.equal(writes[0].path,'/api/work-orders/1/prepare-next');
  assert.deepEqual(JSON.parse(writes[0].body),{task_id:7,expected_revision:'a'.repeat(64)});
  assert(ui.get('agent-session').open);
  assert(ui.requests.some(r=>r.path==='/api/tasks/7/agent-packets/9'&&r.method==='GET'));
  assert(!ui.requests.some(r=>r.path.includes('local-inference')));
});
test('stale checkpoint reports conflict without starting another action',async()=>{
  const ui=setup();ui.connect();await settle();ui.fail();
  ui.buttons().find(n=>n.textContent.startsWith('Przygotuj')).click();await settle();
  assert.match(ui.get('message').textContent,/zmienił/);
  assert(!ui.get('agent-session').open);
  assert.equal(ui.requests.filter(r=>r.method==='POST').length,1);
});
test('multifile button is builder-only and optional tests use saved package binding',async()=>{
  for(const autoTest of [false,true]){
    const ui=setup('builder');ui.connect();await settle();
    ui.buttons().find(n=>n.textContent.startsWith('Przygotuj')).click();await settle();
    assert.equal(ui.get('agent-multifile').hidden,false);
    ui.get('agent-auto-test').checked=autoTest;
    ui.get('agent-multifile').click();await settle();
    const requested=ui.requests.find(r=>r.path==='/api/local-inference');
    assert.equal(JSON.parse(requested.body).output_profile,'python-web-multifile-v1');
    const tests=ui.requests.filter(r=>r.path==='/api/package-runs');
    assert.equal(tests.length,autoTest?1:0);
    if(autoTest){const body=JSON.parse(tests[0].body);assert.equal(body.package_id,30);assert.equal(body.package_checksum,'c'.repeat(64));assert.equal(body.confirm_execution,true);}
    assert(!ui.requests.some(r=>r.path.endsWith('/release')||r.path.endsWith('/review')));
  }
  const ui=setup();ui.connect();await settle();
  ui.buttons().find(n=>n.textContent.startsWith('Przygotuj')).click();await settle();
  assert.equal(ui.get('agent-multifile').hidden,true);
});
test('history defaults to selected project and supports attention filter',async()=>{
  const ui=setup();ui.connect();await settle();
  ui.get('inference-refresh').click();await settle();
  assert.equal(ui.requests.at(-1).path,'/api/local-inference?project_id=1');
  ui.get('inference-attention').checked=true;ui.get('inference-attention').change();
  ui.get('inference-refresh').click();await settle();
  assert.equal(ui.requests.at(-1).path,'/api/local-inference?project_id=1&attention_only=true');
  ui.get('inference-scope').value='all';ui.get('inference-scope').change();
  ui.get('inference-refresh').click();await settle();
  assert.equal(ui.requests.at(-1).path,'/api/local-inference?attention_only=true');
});
test('logout clears project and history and stops polling requests',async()=>{
  const ui=setup();ui.connect();await settle();ui.get('logout').click();
  assert(ui.get('workspace').hidden);assert(ui.get('project-guide').hidden);
  assert.equal(ui.get('project-guide').children.length,0);
  assert.equal(ui.get('inference-runs').children.length,0);
  const count=ui.requests.length;await ui.timers[0]();
  assert.equal(ui.requests.length,count);
});
