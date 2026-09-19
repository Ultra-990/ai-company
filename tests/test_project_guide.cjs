const test=require('node:test');
const assert=require('node:assert/strict');
const {render}=require('../app/static/organization-os/project-guide.js');

function setup(){
  const events=[];
  const doc={createElement:tag=>({tag,ownerDocument:doc,children:[],dataset:{},attributes:{},
    append(...children){this.children.push(...children);},
    replaceChildren(...children){this.children=children;},
    setAttribute(key,value){this.attributes[key]=value;},
    addEventListener(event,fn){this[event]=fn;},
    set innerHTML(value){throw Error('HTML injection');}})};
  const host=doc.createElement('section');
  return {host,events,render:(data,prepare)=>render(host,data,(action,id)=>events.push({action,id}),prepare)};
}
function data(action='task',state='instruction'){
  const stage={task_id:7,title:'Etap <img onerror=alert(1)>',state,reason:'Sprawdź zakres',action};
  return {brief:{title:'Projekt <script>nie wykonuj</script>'},tasks:[{id:7}],
    guidance:{version:1,stages:[stage],current:stage,accepted_stages:0,total_stages:1}};
}
function flatten(host){return [host,...host.children.flatMap(flatten)];}

test('rendering uses text and never performs an action automatically',()=>{
  const ui=setup();ui.render(data());
  assert.deepEqual(ui.events,[]);
  assert(flatten(ui.host).some(n=>n.textContent==='Projekt <script>nie wykonuj</script>'||n.textContent?.includes('Projekt <script>')));
  assert(flatten(ui.host).some(n=>n.attributes['aria-current']==='step'));
  const button=flatten(ui.host).find(n=>n.tag==='button');button.click();
  assert.deepEqual(ui.events,[{action:'task',id:7}]);
});
test('next action sends navigation intent only',()=>{
  for(const action of ['history','assignment','details','artifacts']){
    const ui=setup();ui.render(data(action));
    flatten(ui.host).filter(n=>n.tag==='button').at(-1).click();
    assert.deepEqual(ui.events,[{action,id:7}]);
  }
});
test('unknown or executable actions cannot become buttons',()=>{
  const ui=setup();ui.render(data('javascript:alert(1)'));
  assert.equal(flatten(ui.host).filter(n=>n.tag==='button').length,1);
  assert.deepEqual(ui.events,[]);
});
test('foreign/missing task cannot be navigated to',()=>{
  const ui=setup();const d=data();d.tasks=[];ui.render(d);
  assert.equal(flatten(ui.host).filter(n=>n.tag==='button').length,0);
});
test('missing or incompatible contract replaces stale project information',()=>{
  const ui=setup();ui.render(data());ui.render({brief:{title:'Nowy projekt'}});
  assert.equal(flatten(ui.host).filter(n=>n.tag==='button').length,0);
  assert(flatten(ui.host).some(n=>n.textContent?.includes('Nie udało się ustalić etapu')));
});
test('accepted stages do not imply release or resource permission',()=>{
  const ui=setup();ui.render(data('artifacts','accepted'));
  const text=flatten(ui.host).map(n=>n.textContent||'').join(' ');
  assert.match(text,/nie jest procent gotowości wydania/);
  assert.match(text,/Nie uruchamiają Qwena/);
  assert.match(text,/Vast.ai/);
});

test('preparation requires explicit click and sends the exact checkpoint',()=>{
  const ui=setup(), calls=[], d=data();
  d.coordination={can_prepare:true,task_id:7,revision:'a'.repeat(64)};
  ui.render(d,body=>calls.push(body));
  assert.deepEqual(calls,[]);
  flatten(ui.host).find(n=>n.tag==='button'&&n.textContent.startsWith('Przygotuj')).click();
  assert.deepEqual(calls,[{task_id:7,expected_revision:'a'.repeat(64)}]);
});
test('invalid or forbidden preparation cannot become a button',()=>{
  for(const c of [{can_prepare:false,task_id:7,revision:'a'.repeat(64)},
    {can_prepare:true,task_id:7,revision:'bad'}, {can_prepare:true,task_id:8,revision:'a'.repeat(64)}]){
    const ui=setup(),d=data();d.coordination=c;ui.render(d,()=>assert.fail());
    assert(!flatten(ui.host).some(n=>n.tag==='button'&&n.textContent.startsWith('Przygotuj')));
  }
});
