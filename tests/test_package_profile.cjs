const test=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs');
function setup(overrides={}){
  const requests=[],errors=[];
  const node=tag=>({tag,children:[],textContent:'',append(...items){this.children.push(...items);},
    replaceChildren(...items){this.children=items;},setAttribute(){},addEventListener(name,fn){this[name]=fn;},
    set innerHTML(_){throw Error('Unsafe HTML');}});
  const window={},document={createElement:node};
  vm.runInNewContext(fs.readFileSync('app/static/organization-os/package-profile.js','utf8'),{window,document});
  const binding={task_id:1,artifact_id:2,checksum:'a'.repeat(64)};
  const response={task_id:1,package_id:2,package_checksum:binding.checksum,compatible:true,issues:[],...overrides};
  const panel=window.PackageProfile.create({binding,request:async path=>{requests.push(path);return response;},act:async fn=>{try{await fn();}catch(error){errors.push(error.message);}}});
  return {panel,requests,errors,click:()=>panel.children[2].click(),output:panel.children[3]};
}
test('inspection is explicit, GET-only and does not imply test success',async()=>{
  const ui=setup();assert.equal(ui.requests.length,0);await ui.click();
  assert.deepEqual(ui.requests,['/api/tasks/1/workspace-packages/2/multifile-inspection']);
  assert.match(ui.output.children[0].textContent,/zgodne/);
  assert.match(ui.output.children[2].textContent,/Ta kontrola nie uruchomiła aplikacji/);
  assert.match(ui.output.children[2].textContent,/odbiór tej wersji i wydanie ZIP/);
});
test('issue paths and messages remain inert text',async()=>{
  const ui=setup({compatible:false,issues:[{path:'<img onerror=bad>',line:7,message:'<script>bad</script>'}]});
  await ui.click();assert.match(ui.output.children[1].children[0].textContent,/<img onerror=bad> · wiersz 7: <script>bad/);
});
test('response for another package version is rejected',async()=>{
  const ui=setup({package_checksum:'b'.repeat(64)});await ui.click();
  assert.equal(ui.errors.length,1);assert.equal(ui.output.children.length,0);
});
