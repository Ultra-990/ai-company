/* No wheel interception or continuous render loop. Scroll is always native. */
(() => {
 'use strict';
 const clamp=(value,min,max)=>Math.max(min,Math.min(max,value));
 function sceneFrame(progress,index,width){
  const distance=index-clamp(progress,0,2),depth=Math.abs(distance);
  return {x:distance*width*.52,y:depth*24,z:-depth*950,
   opacity:Math.max(.2,1-Math.max(0,depth-1)*.7),saturation:Math.max(.15,1-depth*.75),
   crop:1.02+.12*Math.max(0,1-depth),layer:Math.round(100-depth*30)};
 }
 if(typeof module!=='undefined'&&module.exports)module.exports={sceneFrame};
 if(typeof document==='undefined')return;
 const section=document.querySelector('#visuals'),journey=section?.querySelector('.scene-journey');
 if(!journey)return;
 const stage=journey.querySelector('.scene-stage'),cards=[...journey.querySelectorAll('[data-art]')];
 const chapters=[...journey.querySelectorAll('[data-scene-chapter]')],counter=journey.querySelector('[data-scene-counter]');
 const word=journey.querySelector('.scene-word'),reduced=matchMedia('(prefers-reduced-motion: reduce)');
 const desktop=matchMedia('(min-width: 801px) and (min-height: 620px)');
 let enabled=false,frame=0,current=-1;
 function draw(){
  frame=0;if(!enabled)return;
  const rect=journey.getBoundingClientRect(),travel=Math.max(1,journey.offsetHeight-stage.offsetHeight);
  const progress=clamp(-rect.top/travel,0,1)*2;
  const selected=Math.round(progress),width=stage.clientWidth;
  section.dataset.scenePosition=progress.toFixed(4);
  stage.style.setProperty('--scene-progress',String(progress/2));
  cards.forEach((card,index)=>{
   const pose=sceneFrame(progress,index,width);
   for(const key of ['x','y','z'])card.style.setProperty('--scene-'+key,pose[key]+'px');
   for(const key of ['opacity','saturation','crop','layer'])card.style.setProperty('--scene-'+key,String(pose[key]));
  });
  if(selected!==current){
   current=selected;counter.textContent=`0${selected+1} — 03`;
   word.textContent=['FORMA','PRZESTRZEŃ','MATERIAŁ'][selected];
   chapters.forEach((button,index)=>button.setAttribute('aria-current',String(index===selected)));
  }
 }
 function schedule(){if(!frame&&enabled)frame=requestAnimationFrame(draw);}
 function configure(){
  enabled=desktop.matches&&!reduced.matches;
  section.classList.toggle('scene-ready',enabled);
  if(!enabled){
   if(frame)cancelAnimationFrame(frame);frame=0;current=-1;
   cards.forEach(card=>card.removeAttribute('style'));
   delete section.dataset.scenePosition;
  }else draw();
 }
 function go(index,behavior='smooth'){
  if(!enabled)return;
  const top=scrollY+journey.getBoundingClientRect().top;
  const travel=journey.offsetHeight-stage.offsetHeight;
  scrollTo({top:top+index/2*travel,behavior});
 }
 chapters.forEach(button=>button.addEventListener('click',()=>go(Number(button.dataset.sceneChapter))));
 // Tabbing to a picture makes it the foreground image, without animation.
 cards.forEach((card,index)=>card.addEventListener('focusin',()=>{if(enabled&&current!==index)go(index,'instant');}));
 addEventListener('scroll',schedule,{passive:true});
 addEventListener('resize',configure);reduced.addEventListener('change',configure);desktop.addEventListener('change',configure);
 configure();
})();
