const test=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs');
function setup(){
  const requests=[];let fail=false,current=true;
  const node=tag=>({tagName:tag,children:[],textContent:'',value:'',checked:false,
    append(...items){for(const item of items)item.parent=this;this.children.push(...items);},
    setAttribute(){},addEventListener(event,fn){this[event]=fn;},
    remove(){this.parent.children=this.parent.children.filter(item=>item!==this);},
    set innerHTML(v){throw Error('Unsafe HTML');}});
  const window={},document={createElement:node};
  vm.runInNewContext(fs.readFileSync('app/static/organization-os/package-review.js','utf8'),
    {window,document,crypto:require('node:crypto').webcrypto});
  const request=async(path,options)=>{requests.push({path,options});
    if(options){if(fail)throw Error('network');return {review_id:12,current,recorded_accepted:JSON.parse(options.body).accepted};}
    return {binding:{package_id:2,source_checksum:'a'.repeat(64),scope:{title:'<script>untrusted</script>'},report_checksum:'b'.repeat(64)},context_checksum:'c'.repeat(64),note:'Not published'};
  };
  const section=window.PackageReview.create({run:{id:7,package_id:2,package_checksum:'a'.repeat(64)},request,act:fn=>fn()});
  return {section,requests,setFail(v){fail=v;},setCurrent(v){current=v;},load:()=>section.children[0].click(),
    form:()=>section.children.find(n=>n.tagName==='form')};
}
function fields(form){const inputs=form.children.filter(n=>n.tagName==='label').map(n=>n.children[0]);
  inputs[0].value='Scope checked for this version';inputs[1].value='Evidence reviewed manually';
  inputs[2].value='accept';inputs[3].checked=true;return inputs;}
test('reading context never accepts; explicit decision and confirmation required',async()=>{
  const ui=setup();await ui.load();assert.equal(ui.requests.length,1);
  const form=ui.form(),values=fields(form);values[3].checked=false;
  form.submit({preventDefault(){}});assert.equal(ui.requests.length,1);
  assert(form.children.some(n=>n.textContent==='<script>untrusted</script>'));
});
test('failed request retries same UUID and successful decision clears form',async()=>{
  const ui=setup();await ui.load();const form=ui.form();fields(form);ui.setFail(true);
  // Submit returns the action promise to make completion/error testable.
  await assert.rejects(form.submit({preventDefault(){}}),/network/);
  ui.setFail(false);await form.submit({preventDefault(){}});
  const first=JSON.parse(ui.requests[1].options.body),second=JSON.parse(ui.requests[2].options.body);
  assert.deepEqual(first,second);assert(first.confirm_review);assert.equal(ui.form(),undefined);
});
