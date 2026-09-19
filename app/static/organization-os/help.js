(()=>{'use strict';
const input=document.getElementById('help-search'),articles=[...document.querySelectorAll('.help-article')];
const normalize=s=>s.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/ł/g,'l');
function search(){const terms=normalize(input.value).trim().split(/\s+/).filter(Boolean);let count=0;
  for(const article of articles){const match=terms.every(term=>normalize(article.textContent+' '+article.dataset.keywords).includes(term));article.hidden=!match;if(match)count++;if(terms.length&&match)article.querySelector('details').open=true;}
  document.getElementById('help-count').textContent=`Znalezione instrukcje: ${count} z ${articles.length}.`;
  document.getElementById('help-empty').hidden=count!==0;
}
function clear(){input.value='';search();}
function revealHash(){let id;try{id=decodeURIComponent(location.hash.slice(1));}catch{return;}
  const target=document.getElementById(id);if(!target||!target.matches('.help-article details'))return;
  clear();target.open=true;target.querySelector('summary').focus({preventScroll:true});target.scrollIntoView({block:'start'});
}
input.addEventListener('input',search);input.addEventListener('keydown',e=>{if(e.key==='Escape'){clear();input.focus();}});
document.getElementById('help-clear').onclick=()=>{clear();input.focus();};
document.getElementById('help-print').onclick=()=>window.print();
window.addEventListener('hashchange',revealHash);document.querySelectorAll('a[href^="#"]').forEach(a=>a.addEventListener('click',()=>{if(a.hash===location.hash)revealHash();}));
let printState=[];window.addEventListener('beforeprint',()=>{printState=articles.map(a=>[a,a.hidden,a.querySelector('details').open]);for(const [a] of printState){a.hidden=false;a.querySelector('details').open=true;}});
window.addEventListener('afterprint',()=>{for(const [a,hidden,open] of printState){a.hidden=hidden;a.querySelector('details').open=open;}printState=[];});
// The browser also focuses fragment targets during initial navigation.
// Restore focus to the keyboard-operable summary after that native step.
window.addEventListener('load',()=>requestAnimationFrame(revealHash));
revealHash();
})();
