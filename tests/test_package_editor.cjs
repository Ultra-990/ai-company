const test=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs');
const settle=()=>new Promise(resolve=>setImmediate(resolve));
function setup(){
  const requests=[],errors=[];let fail=false,counter=0;
  const node=tag=>({tag,textContent:'',value:'',children:[],attributes:{},
    append(...items){this.children.push(...items);},replaceChildren(...items){this.children=items;},
    setAttribute(k,v){this.attributes[k]=v;},addEventListener(event,fn){this[event]=fn;},
    set innerHTML(value){throw Error('Unsafe HTML');}});
  const window={};const context={window,document:{createElement:node},confirm:()=>true,
    crypto:{randomUUID:()=>`request-${++counter}`},URL,setTimeout,console};
  vm.runInNewContext(fs.readFileSync('app/static/organization-os/package-editor.js','utf8'),context);
  const binding={task_id:1,artifact_id:2,checksum:'a'.repeat(64),files:[{path:'src/lib.py',size_bytes:10},{path:'test_app.py',size_bytes:10}]};
  async function request(path,options={}){
    requests.push({path,...options});
    if(path.includes('/source?')){
      const name=new URL('http://local'+path).searchParams.get('path');
      return {path:name,content:'<script>inert text</script>',package_checksum:binding.checksum,protected_test:name==='test_app.py'};
    }
    if(fail){fail=false;throw Error('Uncertain save');}
    return {package:{task_id:1,artifact_id:3}};
  }
  const panel=window.PackageEditor.create({binding,request,act:async fn=>{try{await fn();}catch(e){errors.push(e.message);}}});
  const all=()=>{const walk=n=>[n,...n.children.flatMap(walk)];return walk(panel);};
  const button=text=>all().find(n=>n.tag==='button'&&n.textContent===text);
  const inputs=all().filter(n=>n.tag==='input');
  return {panel,requests,errors,all,button,path:inputs[0],purpose:inputs[1],
    text:all().find(n=>n.tag==='textarea'),pick:all().find(n=>n.tag==='select'),fail:()=>{fail=true;}};
}

test('opening nested file renders inert text without writes',async()=>{
  const ui=setup();assert.equal(ui.requests.length,0);
  ui.pick.value='src/lib.py';ui.button('Otwórz plik').click();await settle();
  assert.match(ui.requests[0].path,/path=src%2Flib.py/);
  assert.equal(ui.text.value,'<script>inert text</script>');
  assert.equal(ui.requests[0].method,undefined);
});
test('staged multi-file edits remain local until explicit version save',async()=>{
  const ui=setup();
  for(const [path,value] of [['src/lib.py','new'],['assets/main.js','js']]){
    ui.path.value=path;ui.text.value=value;ui.button('Dodaj zmianę do szkicu').click();
  }
  assert.equal(ui.requests.length,0);ui.purpose.value='Zmiana modułu';
  ui.button('Zapisz nową wersję źródeł').click();await settle();
  assert.equal(ui.requests.length,1);assert.equal(ui.requests[0].method,'POST');
  const body=JSON.parse(ui.requests[0].body);
  assert.deepEqual(body.changes,{'src/lib.py':'new','assets/main.js':'js'});
  assert.equal(body.base_checksum,'a'.repeat(64));
  assert(ui.all().some(n=>n.tag==='a'&&n.href==='/os/build?task=1&package=3'));
  assert(ui.all().find(n=>n.tag==='fieldset').disabled);
});
test('uncertain request reuses id, changed payload is refused',async()=>{
  const ui=setup();ui.path.value='src/a.py';ui.text.value='new';ui.purpose.value='Change';
  ui.button('Dodaj zmianę do szkicu').click();ui.fail();
  ui.button('Zapisz nową wersję źródeł').click();await settle();
  ui.purpose.value='Different';ui.button('Zapisz nową wersję źródeł').click();await settle();
  assert.equal(ui.requests.length,1);assert(ui.errors.some(e=>e.includes('wcześniejszy zapis')));
  ui.purpose.value='Change';ui.button('Zapisz nową wersję źródeł').click();await settle();
  assert.equal(ui.requests[0].body,ui.requests[1].body);
});
test('existing test is read-only and cannot be added as an edit',async()=>{
  const ui=setup();ui.pick.value='test_app.py';ui.button('Otwórz plik').click();await settle();
  assert(ui.text.readOnly);ui.button('Dodaj zmianę do szkicu').click();
  assert.equal(ui.all().filter(n=>n.tag==='li').length,0);
  ui.path.value='tests/test_extra.py';ui.path.input();assert(!ui.text.readOnly);
});
test('removing a staged change does not remove the original file',()=>{
  const ui=setup();ui.path.value='src/lib.py';ui.text.value='new';ui.button('Dodaj zmianę do szkicu').click();
  ui.button('Usuń ze szkicu').click();assert.equal(ui.all().filter(n=>n.tag==='li').length,0);
  assert.equal(ui.requests.length,0);
});
