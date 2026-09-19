/* Shared appearance only. Never store tokens, client data or navigation URLs. */
(() => {
  'use strict';
  const media = matchMedia('(prefers-color-scheme: dark)');
  const read = key => {try {return localStorage.getItem(key);} catch {return null;}};
  const save = (key,value) => {try {localStorage.setItem(key,value);} catch {}};
  let orbitId=0;
  const motion=matchMedia('(prefers-reduced-motion: reduce)');
  window.CompanyOrbit={mount(orb){
    const ns='http://www.w3.org/2000/svg',id=`orbit-mask-${++orbitId}`;
    const make=(tag,attrs={})=>{const n=document.createElementNS(ns,tag);for(const [k,v] of Object.entries(attrs))n.setAttribute(k,v);return n;};
    const svg=make('svg',{'class':'orb-moon-track',viewBox:'-75 -75 150 150','aria-hidden':'true'});
    const defs=make('defs'),mask=make('mask',{id,maskUnits:'userSpaceOnUse',x:-75,y:-75,width:150,height:150});
    mask.append(make('rect',{x:-75,y:-75,width:150,height:150,fill:'white'}),make('circle',{r:50,fill:'black'}));defs.append(mask);
    const ring=make('g',{transform:'rotate(-25)','class':'planet-ring'});
    ring.append(make('ellipse',{rx:70,ry:27,mask:`url(#${id})`}),make('path',{d:'M -70 0 A 70 27 0 0 0 70 0'}));
    const moon=make('circle',{'class':'orb-moon',r:4.5});svg.append(defs,ring,moon);orb.append(svg);
    let frame=0,started=0,active=false,visible=true;
    const pose=phase=>{
      const x=70*Math.cos(phase),y=27*Math.sin(phase),a=-25*Math.PI/180;
      moon.setAttribute('cx',x*Math.cos(a)-y*Math.sin(a));moon.setAttribute('cy',x*Math.sin(a)+y*Math.cos(a));
      if(y<0)moon.setAttribute('mask',`url(#${id})`);else moon.removeAttribute('mask');
      moon.dataset.depth=y<0?'behind':'front';
    };
    const tick=time=>{frame=0;if(!active||!visible||document.hidden||motion.matches)return;pose((time-started)/5000*2*Math.PI);frame=requestAnimationFrame(tick);};
    const stop=()=>{cancelAnimationFrame(frame);frame=0;};
    const update=()=>{
      active=orb.matches(':hover,:focus-visible');stop();
      svg.classList.toggle('is-orbiting',active);
      pose(Math.PI/2);started=performance.now()-1250;
      if(active&&visible&&!document.hidden&&!motion.matches)frame=requestAnimationFrame(tick);
    };
    for(const event of ['pointerenter','pointerleave','focus','blur'])orb.addEventListener(event,update);
    document.addEventListener('visibilitychange',update);motion.addEventListener('change',update);
    new IntersectionObserver(entries=>{visible=entries[0].isIntersecting;update();}).observe(orb);
    window.addEventListener('pagehide',stop);pose(Math.PI/2);
  }};
  let preference = read('organization-theme'), palette = read('organization-palette');
  const current = () => ['dark','light'].includes(preference) ? preference : media.matches?'dark':'light';
  function apply() {
    if(!['neutral','green','blue'].includes(palette))palette='neutral';
    const theme=current();document.documentElement.dataset.theme=theme;document.documentElement.dataset.palette=palette;
    document.querySelectorAll('[data-theme-toggle]').forEach(b=>{
      b.textContent=theme==='dark'?'☀ Tryb jasny':'☾ Tryb ciemny';
      b.setAttribute('aria-label',theme==='dark'?'Włącz tryb jasny':'Włącz tryb ciemny');
    });
    document.querySelectorAll('[data-palette-select]').forEach(s=>s.value=palette);
  }
  apply();
  document.addEventListener('DOMContentLoaded',()=>{
    document.querySelectorAll('.ai-orb').forEach(orb=>{
      window.CompanyOrbit.mount(orb);
    });
    const navigation=document.querySelector('.app-navigation');
    if(navigation){
      if(['/os','/os/spatial'].includes(location.pathname)){
        navigation.classList.add('has-view-switch');
        const views=document.createElement('div');views.className='view-switch';views.setAttribute('role','group');views.setAttribute('aria-label','Widok organizacji');
        for(const [href,text] of [['/os','Pulpit'],['/os/spatial','Spatial']]){
          const a=document.createElement('a');a.href=href;a.textContent=text;
          if(location.pathname===href)a.setAttribute('aria-current','page');views.append(a);
        }
        navigation.querySelector('[data-home]').hidden=true;
        navigation.append(views);
      }
      const controls=document.createElement('div');controls.className='appearance-controls';
      const label=document.createElement('label');label.textContent='Paleta';
      const select=document.createElement('select');select.dataset.paletteSelect='';
      for(const [value,text] of [['neutral','Biała / czarna'],['green','Zielona'],['blue','Niebieska']]){
        const option=document.createElement('option');option.value=value;option.textContent=text;select.append(option);
      }
      label.append(select);const toggle=document.createElement('button');toggle.type='button';toggle.dataset.themeToggle='';toggle.id='theme';
      controls.append(label,toggle);navigation.append(controls);
    }
    apply();
    document.querySelectorAll('[data-theme-toggle]').forEach(b=>b.addEventListener('click',()=>{
      preference=current()==='dark'?'light':'dark';save('organization-theme',preference);apply();
    }));
    document.querySelectorAll('[data-palette-select]').forEach(s=>s.addEventListener('change',()=>{
      palette=s.value;save('organization-palette',palette);apply();
    }));
    document.querySelectorAll('[data-back]').forEach(a=>a.addEventListener('click',e=>{
      // Use history only with a same-origin referrer; href is a safe fallback.
      try {if(document.referrer && new URL(document.referrer).origin===location.origin && history.length>1){e.preventDefault();history.back();}} catch {}
    }));
  });
  media.addEventListener('change',apply);
  window.addEventListener('storage',e=>{
    if(e.key==='organization-theme'||e.key==='organization-palette'||e.key===null){preference=read('organization-theme');palette=read('organization-palette');apply();}
  });
  window.addEventListener('pageshow',()=>{preference=read('organization-theme');palette=read('organization-palette');apply();});
})();
