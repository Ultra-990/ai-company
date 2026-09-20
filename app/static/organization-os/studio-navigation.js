/* In-page view history only. Never navigates the parent or discards form data. */
(()=>{'use strict';
 const protectedSelector='a,button,input,select,textarea,label,summary,details,fieldset,form,[contenteditable="true"],[role="button"]';
 function blankTarget(element){return !!element&&['BODY','MAIN','SECTION','ARTICLE','DIV','ASIDE','NAV','DIALOG'].includes(element.tagName)&&!element.closest(protectedSelector);}
 if(typeof module!=='undefined'&&module.exports)module.exports={blankTarget};
 if(typeof document==='undefined')return;
 const strip=document.querySelector('#view-return');if(!strip)return;
 const button=strip.querySelector('button'),stack=[];let press=null,restoring=false,scene=null,movingUntil=0;
 function move(options){if(!window.StudioFocus.active())return;movingUntil=options.behavior==='smooth'?performance.now()+1800:0;scrollTo(options);}
 document.addEventListener('studio:suspend',()=>{movingUntil=0;press=null;});
 // Manual input takes priority over any in-flight navigation animation.
 addEventListener('wheel',event=>{
  if(event.ctrlKey||!event.deltaY||movingUntil<=performance.now()||document.querySelector('dialog[open]'))return;
  // Chromium can discard the first wheel delta while cancelling smooth scroll.
  // Apply that one delta explicitly; subsequent scrolling remains native.
  movingUntil=0;event.preventDefault();
  const unit=event.deltaMode===1?16:event.deltaMode===2?innerHeight:1;
  scrollTo({top:scrollY+event.deltaY*unit,left:scrollX+event.deltaX*unit,behavior:'instant'});
 },{passive:false});
 addEventListener('scrollend',()=>{movingUntil=0;},{passive:true});
 function update(){strip.hidden=stack.length===0;document.body.classList.toggle('nav-can-back',stack.length>0);button.disabled=stack.length===0;document.documentElement.style.setProperty('--return-height',strip.hidden?'0px':strip.getBoundingClientRect().height+'px');}
 function go(target,source=document.activeElement){
  if(!window.StudioFocus.active()||!target||!document.contains(target))return false;
  stack.push({kind:'section',y:scrollY,source});if(stack.length>24)stack.shift();update();
  target.setAttribute('tabindex','-1');window.StudioFocus.focus(target);
  const behavior=matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth';
  movingUntil=behavior==='smooth'?performance.now()+1800:0;target.scrollIntoView({behavior});
  return true;
 }
 function back(){
  if(!window.StudioFocus.active()||document.querySelector('dialog[open]'))return false;
  // Wheel-only movement can return to a chapter before leaving the scene.
  if(stack.at(-1)?.kind!=='scene'&&scene?.active()&&scene.canBack())return scene.back();
  const previous=stack.pop();if(!previous)return false;update();
  if(previous.restore){previous.restore();return true;}
  // Scene focus must not create another chapter-history entry during Back.
  const focus=previous.source?.isConnected?previous.source:document.querySelector('#main');
  restoring=true;try{window.StudioFocus.focus(focus);}finally{restoring=false;}
  move({top:previous.y,behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth'});
  return true;
 }
 function rememberScene(restore){stack.push({kind:'scene',restore});if(stack.length>24)stack.shift();update();}
 window.StudioNavigation=Object.freeze({go,back,move,rememberScene,registerScene(value){scene=value;},get restoring(){return restoring;},get canBack(){return stack.length>0;}});
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
