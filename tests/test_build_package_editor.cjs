const test=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs');
const settle=()=>new Promise(resolve=>setImmediate(resolve));
function setup(profile=null,runs=[]){
  const elements=new Map(),requests=[];let delayed=false,release;
  const node=tag=>{let id='';return {tagName:tag.toUpperCase(),children:[],value:'',textContent:'',
    get id(){return id;},set id(value){id=value;elements.set(id,this);},
    append(...nodes){this.children.push(...nodes);},prepend(...nodes){this.children.unshift(...nodes);},
    replaceChildren(...nodes){this.children=nodes;},after(n){this.next=n;},remove(){elements.delete(id);},
    setAttribute(){},addEventListener(event,fn){this[event]=fn;},
    set innerHTML(value){throw Error('Unsafe HTML');}};};
  const get=id=>{if(!elements.has(id)){const n=node('div');n.id=id;}return elements.get(id);};
  const document={createElement:node,getElementById:get,querySelectorAll:()=>[]};
  const data={task_id:1,artifact_id:2,checksum:'a'.repeat(64),execution_profile:profile,files:[{path:'src/lib.py',size_bytes:10}]};
  async function fetch(path){requests.push(path);return {ok:true,json:async()=>{
    if(path==='/api/package-runs')return {runs};
    if(delayed)await new Promise(resolve=>{release=resolve;});return data;
  }};}
  const window={createApplicationPreview:()=>({close(){}}),createApplicationRevisions:()=>({clear(){}}),
    createApplicationQuality:()=>({clear(){}}),OwnerSession:{fetch},addEventListener(){}};
  const context={window,document,AbortSignal,URLSearchParams,location:{search:'?task=1&package=2'},console};
  vm.runInNewContext(fs.readFileSync('app/static/organization-os/package-editor.js','utf8'),context);
  vm.runInNewContext(fs.readFileSync('app/static/organization-os/package-profile.js','utf8'),context);
  vm.runInNewContext(fs.readFileSync('app/static/organization-os/package-review.js','utf8'),context);
  vm.runInNewContext(fs.readFileSync('app/static/organization-os/build.js','utf8'),context);
  return {get,elements,requests,delay(){delayed=true;},release:()=>release(),
    connect:()=>get('access').submit({preventDefault(){}}),load:()=>get('select-package').submit({preventDefault(){}})};
}
test('unsupported layout still has editor but no misleading run form',async()=>{
  const ui=setup();ui.connect();await settle();ui.load();await settle();
  assert(ui.get('run-form').hidden);
  const panel=ui.elements.get('package-requirements');assert(panel);
  assert.match(panel.textContent,/nie mieści się/);
  assert.equal(panel.children[0].children[0].textContent,'Pliki paczki #2 · podgląd i zmiany');
  assert.equal(panel.children[1].children[0].textContent,'Projekt z wieloma modułami');
  ui.get('run-form').submit({preventDefault(){}});await settle();
  assert(ui.requests.every(path=>path==='/api/package-runs'||path==='/api/tasks/1/workspace-packages/2'));
});
test('response decoded after logout cannot restore sources or controls',async()=>{
  const ui=setup();ui.connect();await settle();ui.delay();ui.load();await settle();
  ui.get('logout').click();ui.release();await settle();
  assert(ui.get('workspace').hidden);assert.equal(ui.get('files').children.length,0);
  assert.equal(ui.get('binding').textContent,'');assert(!ui.elements.has('package-requirements'));
});
test('multifile package offers execution but no legacy QA controls',async()=>{
  const ui=setup('python-web-multifile-v1');ui.connect();await settle();ui.load();await settle();
  assert.equal(ui.get('run-form').hidden,false);
  assert.match(ui.elements.get('package-requirements').textContent,/Profil wielomodułowy/);
  assert(ui.requests.every(path=>path==='/api/package-runs'||path==='/api/tasks/1/workspace-packages/2'));
});
test('multifile history keeps candidate and edits without unsupported preview or automatic repair',async()=>{
  const run={id:7,task_id:1,package_id:2,package_checksum:'a'.repeat(64),state:'passed',
    profile:{profile:'python-web-multifile-v1'},result:{},
    capabilities:{test:true,candidate:true,preview:false,automatic_repair:false,release:false}};
  const ui=setup(null,[run]);ui.connect();await settle();
  const all=[];function collect(n){all.push(n.textContent);for(const child of n.children)collect(child);}
  collect(ui.get('runs'));
  assert(all.includes('Pobierz ZIP kandydata do odbioru'));
  assert(all.includes('Otwórz pliki i przygotuj poprawioną wersję'));
  assert(!all.includes('Otwórz aplikację w izolacji'));
  assert(!all.includes('Testuj i napraw automatycznie'));
  assert(!all.includes('Zgłoś poprawkę do tej wersji'));
});
test('certified multifile history enables preview without enabling repair or release',async()=>{
  const run={id:7,task_id:1,package_id:2,package_checksum:'a'.repeat(64),state:'passed',
    profile:{profile:'python-web-multifile-v1'},result:{},
    capabilities:{test:true,candidate:true,preview:true,automatic_repair:false,release:false}};
  const ui=setup(null,[run]);ui.connect();await settle();
  const all=[];function collect(n){all.push(n.textContent);for(const child of n.children)collect(child);}
  collect(ui.get('runs'));
  assert(all.includes('Otwórz aplikację w izolacji'));
  assert(all.includes('Pobierz ZIP kandydata do odbioru'));
  assert(!all.includes('Testuj i napraw automatycznie'));
});
test('multifile package review is shown in build, not redirected to legacy task review',async()=>{
  const run={id:7,task_id:1,package_id:2,package_checksum:'a'.repeat(64),state:'passed',
    profile:{profile:'python-web-multifile-v1'},result:{},
    capabilities:{test:true,candidate:true,preview:true,automatic_repair:false,release:true,package_review:true}};
  const ui=setup(null,[run]);ui.connect();await settle();
  const all=[];function collect(n){all.push(n.textContent);for(const child of n.children)collect(child);}
  collect(ui.get('runs'));
  assert(all.includes('Odbierz lub wycofaj odbiór tej paczki'));
  assert(!all.includes('Otwórz odbiór zadania'));
});
