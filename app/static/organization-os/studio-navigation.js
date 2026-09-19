/* In-page view history only. Never navigates the parent or discards form data. */
(()=>{'use strict';
 const protectedSelector='a,button,input,select,textarea,label,summary,details,fieldset,form,[contenteditable="true"],[role="button"]';
 function blankTarget(element){return !!element&&['BODY','MAIN','SECTION','ARTICLE','DIV','ASIDE','NAV','DIALOG'].includes(element.tagName)&&!element.closest(protectedSelector);}
 if(typeof module!=='undefined'&&module.exports)module.exports={blankTarget};
 if(typeof document==='undefined')return;
 const strip=document.querySelector('#view-return');if(!strip)return;
 const button=strip.querySelector('button'),stack=[];let press=null,restoring=false;
 function update(){strip.hidden=stack.length===0;document.body.classList.toggle('nav-can-back',stack.length>0);button.disabled=stack.length===0;document.documentElement.style.setProperty('--return-height',strip.hidden?'0px':strip.getBoundingClientRect().height+'px');}
 function go(target,source=document.activeElement){
  if(!target||!document.contains(target))return false;
  stack.push({y:scrollY,source});if(stack.length>24)stack.shift();update();
  target.setAttribute('tabindex','-1');target.focus({preventScroll:true});
  target.scrollIntoView({behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth'});
  return true;
 }
 function back(){
  const previous=stack.pop();if(!previous)return false;update();
  // Scene focus must not create another chapter-history entry during Back.
  const focus=previous.source?.isConnected?previous.source:document.querySelector('#main');
  restoring=true;try{if(focus)focus.focus({preventScroll:true});}finally{restoring=false;}
  scrollTo({top:previous.y,behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth'});
  return true;
 }
 window.StudioNavigation=Object.freeze({go,back,get restoring(){return restoring;},get canBack(){return stack.length>0;}});
 button.addEventListener('click',back);
 document.addEventListener('pointerdown',event=>{press={x:event.clientX,y:event.clientY,yScroll:scrollY};},{passive:true});
 document.addEventListener('click',event=>{
  if(event.defaultPrevented||event.button!==0||event.ctrlKey||event.metaKey||event.shiftKey||event.altKey||document.querySelector('dialog[open]'))return;
  const link=event.target.closest('a[href^="#"]');
  if(link){const target=document.getElementById(link.getAttribute('href').slice(1));if(target){event.preventDefault();go(target,link);}return;}
  if(!blankTarget(event.target)||getSelection()?.toString())return;
  if(press&&(Math.hypot(event.clientX-press.x,event.clientY-press.y)>8||Math.abs(scrollY-press.yScroll)>8))return;
  back();
 });
 new ResizeObserver(update).observe(strip);update();
})();
