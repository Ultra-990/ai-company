/* Trusted preview enhancement. Images come from a hash-checked local manifest. */
(()=>{'use strict';
 const gallery=document.querySelector('#visuals'),dialog=document.querySelector('#art-viewer');
 if(!gallery||!dialog)return;
 const cards=[...gallery.querySelectorAll('[data-art]')], image=dialog.querySelector('img');
 const label=dialog.querySelector('#art-title'),counter=dialog.querySelector('#art-counter');
 const stage=dialog.querySelector('.art-stage'),zoomLabel=dialog.querySelector('#zoom-level');
 const reduce=matchMedia('(prefers-reduced-motion: reduce)');
 let index=0,zoom=1,opener=null,scrollFrame=0;
 function setZoom(value){zoom=Math.max(1,Math.min(2.4,value));image.style.transform=`scale(${zoom})`;zoomLabel.textContent=Math.round(zoom*100)+'%';}
 function show(value){index=(value+cards.length)%cards.length;const source=cards[index].querySelector('img');image.src=source.src;image.alt=source.alt;label.textContent=cards[index].querySelector('h3').textContent;counter.textContent=`${index+1} / ${cards.length}`;setZoom(1);}
 function open(value,button){opener=button;show(value);dialog.showModal();document.body.classList.add('art-open');dialog.querySelector('[data-close]').focus();}
 document.querySelectorAll('[data-open-art]').forEach(button=>button.addEventListener('click',()=>open(Number(button.dataset.openArt),button)));
 dialog.querySelector('[data-close]').addEventListener('click',()=>dialog.close());
 dialog.addEventListener('close',()=>{document.body.classList.remove('art-open');opener?.focus();});
 dialog.querySelector('[data-prev]').addEventListener('click',()=>show(index-1));
 dialog.querySelector('[data-next]').addEventListener('click',()=>show(index+1));
 dialog.querySelector('[data-zoom-in]').addEventListener('click',()=>setZoom(zoom+.2));
 dialog.querySelector('[data-zoom-out]').addEventListener('click',()=>setZoom(zoom-.2));
 dialog.querySelector('[data-reset]').addEventListener('click',()=>setZoom(1));
 dialog.addEventListener('keydown',event=>{if(event.key==='ArrowRight'){event.preventDefault();show(index+1);}if(event.key==='ArrowLeft'){event.preventDefault();show(index-1);}});
 // Only the deliberately opened viewer consumes wheel. Browser Ctrl+wheel and
 // all page scrolling remain native. Buttons provide touch/keyboard equivalents.
 stage.addEventListener('wheel',event=>{if(event.ctrlKey||!dialog.open)return;event.preventDefault();setZoom(zoom+(event.deltaY<0?.1:-.1));},{passive:false});
 stage.addEventListener('pointermove',event=>{if(reduce.matches||event.pointerType!=='mouse'||zoom<=1)return;const r=stage.getBoundingClientRect();image.style.transformOrigin=`${Math.max(0,Math.min(100,(event.clientX-r.left)/r.width*100))}% ${Math.max(0,Math.min(100,(event.clientY-r.top)/r.height*100))}%`;});
 stage.addEventListener('pointerleave',()=>image.style.transformOrigin='50% 50%');
 function animate(){scrollFrame=0;cards.forEach(card=>{const rect=card.getBoundingClientRect();const distance=Math.min(1,Math.abs(rect.top+rect.height/2-innerHeight/2)/innerHeight);card.style.setProperty('--art-scale',reduce.matches?'1':String(1.06-distance*.06));});}
 function schedule(){if(!scrollFrame)scrollFrame=requestAnimationFrame(animate);}
 addEventListener('scroll',schedule,{passive:true});addEventListener('resize',schedule);reduce.addEventListener('change',schedule);schedule();
})();
