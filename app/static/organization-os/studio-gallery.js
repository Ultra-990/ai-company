/* Shared-image motion in the existing opaque preview. No network or libraries. */
(() => {
 'use strict';
 // Uniform scale + crop, never separate X/Y scaling that distorts photographs.
 function flightFrame(source, target) {
  if (![source,target].every(r=>r&&['left','top','width','height'].every(k=>Number.isFinite(r[k]))&&r.width>0&&r.height>0)) return null;
  const scale=Math.max(source.width/target.width,source.height/target.height);
  const width=target.width*scale,height=target.height*scale;
  const x=source.left+(source.width-width)/2-target.left;
  const y=source.top+(source.height-height)/2-target.top;
  const cropX=Math.max(0,(width-source.width)/width*50);
  const cropY=Math.max(0,(height-source.height)/height*50);
  return {transform:`translate(${x}px, ${y}px) scale(${scale})`,clipPath:`inset(${cropY}% ${cropX}%)`,opacity:1};
 }
 if(typeof module!=='undefined'&&module.exports)module.exports={flightFrame};
 if(typeof document==='undefined')return;
 const gallery=document.querySelector('#visuals'),dialog=document.querySelector('#art-viewer');
 if(!gallery||!dialog)return;
 const cards=[...gallery.querySelectorAll('[data-art]')],image=dialog.querySelector('.art-stage img');
 const label=dialog.querySelector('#art-title'),counter=dialog.querySelector('#art-counter');
 const stage=dialog.querySelector('.art-stage'),zoomLabel=dialog.querySelector('#zoom-level');
 const reduce=matchMedia('(prefers-reduced-motion: reduce)'),active=new Set();
 let index=0,initialIndex=0,zoom=1,opener=null,scrollFrame=0,phase='closed',queuedClose=false;
 const ease='cubic-bezier(.22,.75,.15,1)';
 function state(value){
  phase=value;dialog.dataset.phase=value;
  dialog.querySelectorAll('.art-controls button').forEach(b=>b.disabled=value!=='open');
 }
 async function motion(element,frames,duration){
  if(reduce.matches||typeof element.animate!=='function')return;
  const animation=element.animate(frames,{duration,easing:ease,fill:'both'});active.add(animation);
  try{await animation.finished;}catch{/* resize/cancel must not strand a dialog */}
  finally{active.delete(animation);animation.cancel();}
 }
 function finishMotion(){for(const animation of active)try{animation.finish();}catch{animation.cancel();}}
 function setZoom(value){zoom=Math.max(1,Math.min(2.4,value));image.style.transform=`scale(${zoom})`;zoomLabel.textContent=Math.round(zoom*100)+'%';}
 function show(value){
  index=(value+cards.length)%cards.length;const source=cards[index].querySelector('img');
  image.src=source.src;image.alt=source.alt;image.style.transformOrigin='50% 50%';
  label.textContent=cards[index].querySelector('h3').textContent;counter.textContent=`${index+1} / ${cards.length}`;setZoom(1);
 }
 function contentBox(){
  const r=stage.getBoundingClientRect(),ratio=(image.naturalWidth||768)/(image.naturalHeight||512);
  const width=Math.min(r.width,r.height*ratio),height=width/ratio;
  return {left:r.left+(r.width-width)/2,top:r.top+(r.height-height)/2,width,height};
 }
 function thumbnail(button){return (button.querySelector('.visual-image')||button).getBoundingClientRect();}
 async function fly(box,reverse=false){
  if(reduce.matches)return;
  const target=contentBox(),start=flightFrame(box,target);
  if(!start||box.bottom<0||box.top>innerHeight)return motion(image,[{opacity:reverse?1:0},{opacity:reverse?0:1}],240);
  const clone=image.cloneNode();clone.className='art-flight';clone.alt='';clone.setAttribute('aria-hidden','true');
  Object.assign(clone.style,{left:target.left+'px',top:target.top+'px',width:target.width+'px',height:target.height+'px',transform:'none',transformOrigin:'0 0'});
  dialog.append(clone);image.style.visibility='hidden';
  const end={transform:'translate(0px, 0px) scale(1)',clipPath:'inset(0% 0%)',opacity:1};
  try{await motion(clone,reverse?[end,start]:[start,end],reverse?520:720);}
  finally{clone.remove();image.style.visibility='';}
 }
 async function open(value,button){
  if(phase!=='closed')return;
  opener=button;initialIndex=value;const box=thumbnail(button);
  show(value);state('opening');dialog.showModal();document.body.classList.add('art-open');
  dialog.querySelector('[data-close]').focus({preventScroll:true});
  try{await fly(box);}finally{state('open');if(queuedClose){queuedClose=false;close();}}
 }
 async function close(){
  if(phase==='closed'||phase==='closing')return;
  if(phase!=='open'){queuedClose=true;finishMotion();return;}
  state('closing');
  try{
   if(zoom!==1){const before=image.style.transform;setZoom(1);await motion(image,[{transform:before},{transform:'scale(1)'}],180);}
   const target=index===initialIndex?opener:cards[index].querySelector('button');
   await fly(thumbnail(target),true);
  }finally{dialog.close();}
 }
 async function change(direction){
  if(phase!=='open')return;
  state('switching');
  try{
   await motion(image,[{opacity:1,transform:image.style.transform},{opacity:0,transform:`translateX(${-direction*48}px) scale(.96)`}],200);
   show(index+direction);
   await motion(image,[{opacity:0,transform:`translateX(${direction*64}px) scale(1.04)`},{opacity:1,transform:'translateX(0px) scale(1)'}],380);
  }finally{state('open');if(queuedClose){queuedClose=false;close();}}
 }
 document.querySelectorAll('[data-open-art]').forEach(b=>b.addEventListener('click',()=>open(Number(b.dataset.openArt),b)));
 dialog.querySelector('[data-close]').addEventListener('click',close);
 dialog.addEventListener('click',event=>{
  if(event.target.closest('button,a,input,select,textarea')||getSelection()?.toString())return;
  if(event.target===dialog||['art-toolbar','art-controls','art-instructions'].some(c=>event.target.classList.contains(c))){event.stopPropagation();close();return;}
  if(phase==='open'&&zoom===1&&stage.contains(event.target)){
   const r=contentBox();
   if(event.clientX<r.left||event.clientX>r.left+r.width||event.clientY<r.top||event.clientY>r.top+r.height)close();
  }
 });
 dialog.addEventListener('cancel',event=>{event.preventDefault();close();});
 dialog.addEventListener('close',()=>{finishMotion();state('closed');queuedClose=false;document.body.classList.remove('art-open');opener?.focus({preventScroll:true});});
 dialog.querySelector('[data-prev]').addEventListener('click',()=>change(-1));
 dialog.querySelector('[data-next]').addEventListener('click',()=>change(1));
 dialog.querySelector('[data-zoom-in]').addEventListener('click',()=>setZoom(zoom+.2));
 dialog.querySelector('[data-zoom-out]').addEventListener('click',()=>setZoom(zoom-.2));
 dialog.querySelector('[data-reset]').addEventListener('click',()=>setZoom(1));
 dialog.addEventListener('keydown',event=>{
  // Handle the key before the native close watcher: cancel is not always
  // cancelable (for example without a browser user-activation history).
  if(event.key==='Escape'){event.preventDefault();event.stopPropagation();close();}
  if(event.key==='ArrowRight'){event.preventDefault();change(1);}
  if(event.key==='ArrowLeft'){event.preventDefault();change(-1);}
 });
 dialog.addEventListener('wheel',event=>{if(event.ctrlKey||!dialog.open||event.deltaY===0)return;event.preventDefault();if(phase==='open')setZoom(zoom+(event.deltaY<0?.1:-.1));},{passive:false});
 stage.addEventListener('pointermove',event=>{if(reduce.matches||event.pointerType!=='mouse'||zoom<=1||phase!=='open')return;const r=stage.getBoundingClientRect();image.style.transformOrigin=`${Math.max(0,Math.min(100,(event.clientX-r.left)/r.width*100))}% ${Math.max(0,Math.min(100,(event.clientY-r.top)/r.height*100))}%`;});
 stage.addEventListener('pointerleave',()=>image.style.transformOrigin='50% 50%');
 function animate(){
  scrollFrame=0;cards.forEach(card=>{const r=card.getBoundingClientRect();const distance=Math.max(-1,Math.min(1,(r.top+r.height/2-innerHeight/2)/innerHeight));
   card.style.setProperty('--art-scale',reduce.matches?'1':String(1.14-Math.abs(distance)*.1));
   card.style.setProperty('--art-drift',reduce.matches?'0px':distance*16+'px');
  });
 }
 function schedule(){if(!scrollFrame)scrollFrame=requestAnimationFrame(animate);}
 addEventListener('scroll',schedule,{passive:true});
 addEventListener('resize',()=>{finishMotion();schedule();});
 reduce.addEventListener('change',()=>{finishMotion();schedule();});schedule();
})();
