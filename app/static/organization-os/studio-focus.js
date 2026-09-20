/* Focus belongs to the active document, never to an OS window or another tab. */
(()=>{'use strict';
 function createScope(doc){
  let epoch=0;
  const active=()=>!doc.hidden&&doc.hasFocus();
  return Object.freeze({active,ticket:()=>epoch,suspend:()=>{epoch++;},
   valid:ticket=>ticket===epoch&&active(),
   focus(element,ticket=epoch){
    if(ticket!==epoch||!active()||!element?.isConnected||element.ownerDocument!==doc)return false;
    element.focus({preventScroll:true});return true;
   }
  });
 }
 const plainKey=event=>!event.altKey&&!event.ctrlKey&&!event.metaKey&&!event.isComposing;
 if(typeof module!=='undefined'&&module.exports)module.exports={createScope,plainKey};
 if(typeof document==='undefined')return;
 const scope=createScope(document);window.StudioFocus=Object.freeze({...scope,plainKey});
 function suspend(){scope.suspend();document.dispatchEvent(new Event('studio:suspend'));}
 addEventListener('blur',suspend);
 document.addEventListener('visibilitychange',()=>{if(document.hidden)suspend();});
 addEventListener('focus',()=>{if(scope.active())document.dispatchEvent(new Event('studio:resume'));});
})();
