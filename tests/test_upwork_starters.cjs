const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const {examples} = require('../app/static/organization-os/upwork-starters.js');

function setup() {
  const elements = new Map(), buttons = [], requests = [], confirmations = [];
  let approved = true, response;
  const element = () => ({value:'', textContent:'', hidden:false, children:[],
    classList:{toggle(){}}, append(...nodes){this.children.push(...nodes);},
    replaceChildren(...nodes){this.children=nodes;}, addEventListener(name,fn){this[name]=fn;},
    focus(){this.focused=true;}, scrollIntoView(){},
    set innerHTML(value){throw Error('Unsafe HTML');}});
  const get = id => {if(!elements.has(id))elements.set(id,element());return elements.get(id);};
  const fields = Object.fromEntries(['title','source_url','job_text','criteria','notes'].map(k=>[k,element()]));
  const form=get('upwork-intake');form.elements={namedItem:name=>fields[name]};
  form.reset=()=>Object.values(fields).forEach(f=>{f.value='';});
  const events={};
  const window={addEventListener:(event,fn)=>{events[event]=fn;}, OwnerSession:{active:true,
    fetch:async (path,options)=>{requests.push({path,options});
      return response ? response() : {ok:false,json:async()=>({detail:'Niepewny zapis'})};}}};
  const context={window,document:{getElementById:get,querySelectorAll:()=>buttons,
    createElement:tag=>{const e=element();if(tag==='button')buttons.push(e);return e;}},
    confirm:text=>{confirmations.push(text);return approved;},
    FormData:class {get(name){return fields[name].value;}},
    crypto:{randomUUID:()=> 'synthetic-test-id'}, AbortSignal:{timeout:()=>undefined}};
  vm.runInNewContext(fs.readFileSync('app/static/organization-os/upwork-starters.js','utf8'),context);
  vm.runInNewContext(fs.readFileSync('app/static/organization-os/upwork.js','utf8'),context);
  return {get,fields,requests,confirmations,events,buttons,
    choose:i=>get('upwork-starters').children[i].click(),
    approve:value=>{approved=value;},respond:fn=>{response=fn;},
    submit:()=>form.onsubmit({preventDefault(){},target:form})};
}
const settle=()=>new Promise(resolve=>setImmediate(resolve));

test('three synthetic examples satisfy intake field/context limits',()=>{
  assert.equal(examples.length,3);assert.equal(new Set(examples.map(e=>e.id)).size,3);
  for(const e of examples){
    assert.equal(e.source_url,'');assert.match(e.title,/Ćwiczenie/);
    assert(e.title.length>=3&&e.title.length<=160);
    assert(e.job_text.length>=30&&e.job_text.length<=3000);
    assert(e.notes.length<=500);assert(e.criteria.length>=1&&e.criteria.length<=8);
    assert.equal(new Set(e.criteria).size,e.criteria.length);
    assert(e.criteria.every(s=>s.length>=3&&s.length<=240));
    assert([e.title,e.job_text,e.notes,...e.criteria].reduce((n,s)=>n+Buffer.byteLength(s),0)<=4800);
    assert.match(e.notes,/Vast.ai/);assert.match(e.job_text,/file:\/\//);
  }
});
test('selecting an example only fills the draft without any request',()=>{
  const ui=setup();ui.choose(0);
  assert.equal(ui.requests.length,0);assert.equal(ui.confirmations.length,0);
  assert.equal(ui.fields.title.value,examples[0].title);
  assert.equal(ui.fields.criteria.value,examples[0].criteria.join('\n'));
  assert.equal(ui.get('detail').hidden,true);
  assert.equal(ui.get('analyse').disabled,true);
  assert(ui.fields.title.focused);
});
test('existing draft stays intact after declined replacement',()=>{
  const ui=setup();ui.fields.job_text.value='Opis klienta';ui.approve(false);ui.choose(1);
  assert.equal(ui.fields.job_text.value,'Opis klienta');assert.equal(ui.fields.title.value,'');
  assert.equal(ui.confirmations.length,1);assert.equal(ui.requests.length,0);
});
test('confirmed replacement clears previous source URL and sets text safely',()=>{
  const ui=setup();ui.fields.source_url.value='https://www.upwork.com/jobs/example';ui.choose(2);
  assert.equal(ui.fields.source_url.value,'');
  assert(ui.fields.criteria.value.includes('<img src=x onerror=alert(1)>'));
  assert.equal(ui.requests.length,0);
});
test('uncertain save requires confirmation even after all draft fields are cleared',async()=>{
  const ui=setup();ui.choose(0);ui.submit();await settle();
  assert.equal(ui.requests.length,1);
  Object.values(ui.fields).forEach(f=>{f.value='';});ui.approve(false);ui.choose(1);
  assert.equal(ui.confirmations.length,1);assert.equal(ui.fields.title.value,'');
  assert.equal(ui.requests.length,1);
});
test('a pending request prevents replacing its draft',async()=>{
  const ui=setup();let finish;ui.respond(()=>new Promise(r=>{finish=r;}));
  ui.choose(0);ui.submit();ui.choose(1);
  assert.equal(ui.fields.title.value,examples[0].title);assert.equal(ui.confirmations.length,0);
  finish({ok:false,json:async()=>({detail:'Test'})});await settle();
});
test('pagehide clears the example fields',()=>{
  const ui=setup();ui.choose(0);ui.events.pagehide();
  assert(Object.values(ui.fields).every(f=>f.value===''));assert.equal(ui.requests.length,0);
});
test('page loads catalog before intake controller and keeps API probe secondary',()=>{
  const html=fs.readFileSync('app/templates/organization-os/upwork.html','utf8');
  assert(html.indexOf('upwork-starters.js')<html.indexOf('upwork.js'));
  assert.match(html,/id="upwork-starters"/);
  assert.match(html,/<details class="panel"><summary>Narzędzia dodatkowe/);
});
