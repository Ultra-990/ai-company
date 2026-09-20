/* Bounded CSS 3D choreography + damped springs. Never intercept page scrolling. */
(()=>{'use strict';
 const clamp=(value,min,max)=>Math.max(min,Math.min(max,value));
 function sceneFrame(progress,index,width,mode='flow',depthScale=1){
  const d=index-clamp(progress,0,2),a=d*1.65,depth=Math.abs(d);
  let x=d*width*.52,y=depth*24,z=-depth*950,rx=0,ry=0,rz=0;
  if(mode==='helix'){x=Math.sin(a)*width*.5;y=Math.sin(a*.8)*width*.15;z=(Math.cos(a)-1)*430-depth*260;rx=Math.sin(a)*10;ry=-Math.sin(a)*20;rz=Math.sin(a*.6)*6;}
  if(mode==='orbit'){x=Math.sin(a)*width*.5;y=(1-Math.cos(a))*width*.09;z=(Math.cos(a)-1)*540-depth*160;ry=-Math.sin(a)*26;rx=Math.sin(a)*-8;}
  if(mode==='wave'){x=d*width*.6;y=Math.sin(d*Math.PI)*width*.2;z=-depth*650;rx=Math.sin(d*Math.PI)*14;rz=Math.sin(d*Math.PI)*-8;}
  return {x,y,z:z*clamp(depthScale,.4,1.4),rx,ry,rz,opacity:Math.max(.2,1-Math.max(0,depth-1)*.7),saturation:Math.max(.15,1-depth*.75),crop:1.02+.12*Math.max(0,1-depth),layer:Math.round(100-depth*30)};
 }
 function springStep(state,target,seconds,elasticity=55){
  const dt=clamp(seconds,0,.05),steps=Math.max(1,Math.ceil(dt/(1/120))),h=dt/steps;
  const damping=26-clamp(elasticity,0,100)*.15,stiffness=150;
  let value=state.value,velocity=state.velocity;
  for(let i=0;i<steps;i++){velocity+=((target-value)*stiffness-damping*velocity)*h;value+=velocity*h;}
  if(Math.abs(value-target)<.02&&Math.abs(velocity)<.04)return {value:target,velocity:0};
  return {value,velocity};
 }
 function trailPath(progress,width,height,mode){
  const points=[];
  for(let i=0;i<=144;i++){
   const t=i/144,angle=t*Math.PI*(mode==='helix'?6:2)+progress*.7;
   let x,y,z;
   if(mode==='helix'){x=(t-.5)*width*1.25;y=Math.sin(angle)*height*.24;z=Math.cos(angle)*240-180;}
   else if(mode==='wave'){x=Math.sin(angle*2)*width*.5;y=Math.sin(angle*3)*height*.25;z=Math.cos(angle)*180-120;}
   else{x=Math.cos(angle)*width*.53;y=Math.sin(angle)*height*.32;z=Math.sin(angle)*220-140;}
   const s=1000/(1000-z);points.push(`${i?'L':'M'}${(width/2+x*s).toFixed(2)},${(height*.48+y*s).toFixed(2)}`);
  }return points.join(' ');
 }
 if(typeof module!=='undefined'&&module.exports)module.exports={sceneFrame,springStep,trailPath};
 if(typeof document==='undefined')return;
 const section=document.querySelector('#visuals'),journey=section?.querySelector('.scene-journey');if(!journey)return;
 const stage=journey.querySelector('.scene-stage'),cards=[...journey.querySelectorAll('[data-art]')];
 const chapters=[...journey.querySelectorAll('[data-scene-chapter]')],counter=journey.querySelector('[data-scene-counter]');
 const word=journey.querySelector('.scene-word'),trail=journey.querySelector('.scene-trail path');
 const reduced=matchMedia('(prefers-reduced-motion: reduce)'),desktop=matchMedia('(min-width: 801px) and (min-height: 620px)');
 const back=journey.querySelector('[data-scene-back]');
 const keys=['x','y','z','rx','ry','rz'];let enabled=false,frame=0,current=-1,last=0,targetProgress=0,settleDeadline=0;
 let settings={path:'helix',elasticity:55,depth:1,paused:false},poses=[],pointer={x:0,y:0},camera={x:{value:0,velocity:0},y:{value:0,velocity:0}};
 function stickyTop(){return parseFloat(getComputedStyle(stage).top)||0;}
 function measure(){const r=journey.getBoundingClientRect();targetProgress=clamp((stickyTop()-r.top)/Math.max(1,journey.offsetHeight-stage.offsetHeight),0,1)*2;}
 function render(now,instant=false){
  frame=0;if(!enabled||!window.StudioFocus.active())return;
  // Low-FPS devices must not keep a spring running indefinitely.
  instant ||= now>=settleDeadline;
  const dt=last?Math.min(.05,(now-last)/1000):1/60;last=now;
  const selected=Math.round(targetProgress),width=stage.clientWidth;let moving=false;
  cards.forEach((card,index)=>{
   const target=sceneFrame(targetProgress,index,width,settings.path,settings.depth);
   if(!poses[index])poses[index]={};
   keys.forEach(key=>{
    const before=poses[index][key]||{value:target[key],velocity:0};
    const next=instant?{value:target[key],velocity:0}:springStep(before,target[key],dt,settings.elasticity);
    poses[index][key]=next;moving ||= next.velocity!==0||next.value!==target[key];
    card.style.setProperty('--scene-'+key,next.value+(key.startsWith('r')?'deg':'px'));
   });
   for(const key of ['opacity','saturation','crop','layer'])card.style.setProperty('--scene-'+key,String(target[key]));
  });
  for(const key of ['x','y']){
   camera[key]=instant?{value:pointer[key],velocity:0}:springStep(camera[key],pointer[key],dt,settings.elasticity);
   moving ||= camera[key].velocity!==0||camera[key].value!==pointer[key];
   stage.style.setProperty('--camera-'+key,camera[key].value+'%');
  }
  trail.setAttribute('d',trailPath(targetProgress,width,stage.clientHeight,settings.path));
  section.dataset.scenePosition=targetProgress.toFixed(4);section.dataset.sceneMoving=String(moving);
  back.disabled=targetProgress<.01&&!window.StudioNavigation?.canBack;
  stage.style.setProperty('--scene-progress',String(targetProgress/2));
  if(selected!==current){current=selected;counter.textContent=`0${selected+1} — 03`;word.textContent=['FORMA','PRZESTRZEŃ','MATERIAŁ'][selected];chapters.forEach((button,index)=>button.setAttribute('aria-current',String(index===selected)));}
  if(moving&&!settings.paused)frame=requestAnimationFrame(render);
 }
 function schedule(){settleDeadline=performance.now()+1800;if(!frame&&enabled&&!settings.paused&&window.StudioFocus.active()){last=0;frame=requestAnimationFrame(render);}}
 function configure(){
  enabled=desktop.matches&&!reduced.matches;section.classList.toggle('scene-ready',enabled);
  if(frame)cancelAnimationFrame(frame);frame=0;last=0;poses=[];
  if(!enabled){current=-1;cards.forEach(card=>card.removeAttribute('style'));delete section.dataset.scenePosition;section.dataset.sceneMoving='false';}
  else{measure();render(performance.now(),true);}
 }
 function go(index,behavior='smooth',remember=true){
  if(!window.StudioFocus.active())return;
  if(!enabled){cards[Math.round(clamp(index,0,2))].scrollIntoView({behavior:'instant',block:'center'});return;}
  if(remember&&Math.abs(index-targetProgress)>.01){const previous=targetProgress;window.StudioNavigation.rememberScene(()=>go(previous,'smooth',false));}
  if(settings.paused||reduced.matches)behavior='instant';
  window.StudioNavigation.move({top:scrollY+journey.getBoundingClientRect().top-stickyTop()+index/2*(journey.offsetHeight-stage.offsetHeight),behavior});
  if(settings.paused){measure();render(performance.now(),true);}
 }
 window.StudioNavigation.registerScene({
  active:()=>enabled&&journey.getBoundingClientRect().top<=stickyTop()+1&&journey.getBoundingClientRect().bottom>stage.offsetHeight,
  canBack:()=>targetProgress>.01,
  back:()=>{go(Math.max(0,Math.ceil(targetProgress)-1),'smooth',false);return true;}
 });
 back.addEventListener('click',()=>window.StudioNavigation.back());
 chapters.forEach(button=>button.addEventListener('click',()=>go(Number(button.dataset.sceneChapter))));
 cards.forEach((card,index)=>card.addEventListener('focusin',()=>{if(enabled&&current!==index&&!window.StudioNavigation?.restoring){go(index,'instant');measure();render(performance.now(),true);}}));
 stage.addEventListener('pointermove',event=>{if(event.pointerType!=='mouse'||!enabled)return;const r=stage.getBoundingClientRect();pointer={x:clamp((event.clientX-r.left)/r.width-.5,-.5,.5)*8,y:clamp((event.clientY-r.top)/r.height-.5,-.5,.5)*6};schedule();});
 stage.addEventListener('pointerleave',()=>{pointer={x:0,y:0};schedule();});
 document.addEventListener('studio:motion',event=>{
  const d=event.detail;if(!d||!['helix','orbit','wave','flow'].includes(d.path)||!Number.isFinite(d.elasticity)||!Number.isFinite(d.depth)||typeof d.paused!=='boolean')return;
  settings={path:d.path,elasticity:clamp(d.elasticity,0,100),depth:clamp(d.depth,.4,1.4),paused:d.paused};section.dataset.sceneMode=settings.path;
  if(settings.paused){if(frame)cancelAnimationFrame(frame);frame=0;section.dataset.sceneMoving='false';}else{measure();schedule();}
 });
 addEventListener('scroll',()=>{measure();schedule();},{passive:true});addEventListener('resize',configure);
 document.addEventListener('studio:suspend',()=>{if(frame)cancelAnimationFrame(frame);frame=0;section.dataset.sceneMoving='false';});
 document.addEventListener('studio:resume',()=>{measure();schedule();});
 reduced.addEventListener('change',configure);desktop.addEventListener('change',configure);configure();
})();
