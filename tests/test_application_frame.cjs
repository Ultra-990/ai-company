const test=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs');
function setup(){
  const node=(attrs={})=>({attrs:{...attrs},childNodes:[],getAttribute(k){return this.attrs[k]??null;},
    setAttribute(k,v){this.attrs[k]=v;},replaceChildren(){},append(){}});
  const parsed={documentElement:node({lang:'pl','data-theme':'dark',class:'site',onclick:'evil()',style:'bad'}),
    body:node({id:'content',class:'canvas',onload:'evil()','data-theme':'light',dir:'ltr'}),querySelectorAll(){return []}};
  const document={documentElement:node(),body:node(),head:node(),createElement:()=>node()};
  const parent={postMessage(){}},window={addEventListener(k,fn){this.listener=fn;}};
  vm.runInNewContext(fs.readFileSync('app/static/organization-os/application-frame.js','utf8'),
    {window,parent,document,DOMParser:class{parseFromString(){return parsed;}}});
  return {document,parsed,send:(source=parent)=>window.listener({source,data:{kind:'application-init',html:'synthetic',files:{}}})};
}
test('preview preserves theme, language and layout attributes but no event handlers',()=>{
  const ui=setup();ui.send();
  assert.deepEqual(ui.document.documentElement.attrs,{lang:'pl',class:'site','data-theme':'dark'});
  assert.deepEqual(ui.document.body.attrs,{dir:'ltr',class:'canvas',id:'content','data-theme':'light'});
});
test('foreign messages and duplicate initialization cannot replace theme',()=>{
  const ui=setup();ui.send({});assert.deepEqual(ui.document.documentElement.attrs,{});
  ui.send();ui.parsed.documentElement.attrs['data-theme']='changed';ui.send();
  assert.equal(ui.document.documentElement.attrs['data-theme'],'dark');
});
test('unbounded root attributes are not copied',()=>{
  const ui=setup();ui.parsed.body.attrs.class='x'.repeat(513);ui.send();
  assert.equal(ui.document.body.attrs.class,undefined);
});
