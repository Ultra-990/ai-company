const test=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs');
function setup(){
  const node=(attrs={})=>({attrs:{...attrs},childNodes:[],getAttribute(k){return this.attrs[k]??null;},
    setAttribute(k,v){this.attrs[k]=v;},replaceChildren(){},append(){}});
  const images=[node({src:'/static/photo.png'}),node({src:'//foreign/photo.png'}),node({src:'static/../photo.png'})];
  const parsed={documentElement:node({lang:'pl','data-theme':'dark',class:'site',onclick:'evil()',style:'bad'}),
    body:node({id:'content',class:'canvas',onload:'evil()','data-theme':'light',dir:'ltr'}),querySelectorAll(selector){return selector==='img[src]'?images:[]}};
  const document={documentElement:node(),body:node(),head:node(),createElement:()=>node()};
  const messages=[],parent={postMessage(data){messages.push(data);}},window={addEventListener(k,fn){this.listener=fn;}};
  vm.runInNewContext(fs.readFileSync('app/static/organization-os/application-frame.js','utf8'),
    {window,parent,document,Response,setTimeout,clearTimeout,DOMParser:class{parseFromString(){return parsed;}}});
  return {document,parsed,images,window,messages,
    reply:data=>window.listener({source:parent,data}),
    send:(source=parent)=>window.listener({source,data:{kind:'application-init',html:'synthetic',files:{'static/photo.png':'data:image/png;base64,aGVsbG8='}}})};
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
test('only packaged relative PNG images are embedded',()=>{
  const ui=setup();ui.send();
  assert.equal(ui.images[0].attrs.src,'data:image/png;base64,aGVsbG8=');
  assert.equal(ui.images[1].attrs.src,'//foreign/photo.png');
  assert.equal(ui.images[2].attrs.src,'static/../photo.png');
});

test('frame fetch preserves encoded text and blocks invalid requests before messaging',async()=>{
  const ui=setup();ui.send();
  const path='/api/count?text='+encodeURIComponent("Zażółć 123!~*'()");
  const pending=ui.window.fetch(path),sent=ui.messages.at(-1);
  assert.equal(sent.kind,'application-request');assert.equal(sent.path,path);
  ui.reply({kind:'application-reply',id:sent.id,response:{status:200,body:'{"letters":6}',content_type:'application/json'}});
  assert.deepEqual(await (await pending).json(),{letters:6});
  const count=ui.messages.length;
  for(const invalid of ['/api/count;ignored?text=x','/api/count/extra?text=x',
    '/api/count?text=x#fragment','/api/count?text=x\n','/api/count?text=x\r',
    '/api/count?text=a b','/api/count?text='+'a'.repeat(796)]){
    await assert.rejects(ui.window.fetch(invalid));
    assert.equal(ui.messages.length,count,invalid);
  }
});
