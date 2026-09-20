const {test}=require('node:test');
const assert=require('node:assert/strict');
const {createScope,plainKey}=require('../app/static/organization-os/studio-focus.js');

test('focus stays in the visible active document and rejects foreign elements',()=>{
 let foreground=true,calls=0;
 const doc={hidden:false,hasFocus:()=>foreground},scope=createScope(doc);
 const element={isConnected:true,ownerDocument:doc,focus:()=>calls++};
 assert.equal(scope.focus(element),true);assert.equal(calls,1);
 foreground=false;assert.equal(scope.focus(element),false);
 foreground=true;doc.hidden=true;assert.equal(scope.focus(element),false);
 doc.hidden=false;assert.equal(scope.focus({...element,ownerDocument:{}}),false);
 assert.equal(scope.focus({...element,isConnected:false}),false);
 assert.equal(calls,1);
});
test('a delayed callback cannot reuse its focus ticket after losing focus',()=>{
 let calls=0;const doc={hidden:false,hasFocus:()=>true},scope=createScope(doc);
 const element={isConnected:true,ownerDocument:doc,focus:()=>calls++};
 const ticket=scope.ticket();scope.suspend();
 assert.equal(scope.valid(ticket),false);assert.equal(scope.focus(element,ticket),false);
 assert.equal(calls,0);assert.equal(scope.focus(element,scope.ticket()),true);
});
test('modified/system shortcut events and IME are not gallery/menu commands',()=>{
 for(const modifier of ['altKey','ctrlKey','metaKey','isComposing'])assert.equal(plainKey({[modifier]:true}),false);
 assert.equal(plainKey({key:'Escape'}),true);
});
