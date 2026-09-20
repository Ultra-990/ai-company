/* Explicit local rules, not fake AI generation or a submitted client order. */
(()=>{'use strict';
 const types={website:'Interaktywna strona',application:'Aplikacja internetowa',platform:'Platforma / społeczność',automation:'Automatyzacja AI',media:'Studio generowania mediów'};
 const modules={
  scene:['Scena interaktywna','Działa klawiatura, telefon, reduced motion i pominięcie sceny.'],
  cms:['CMS','Uprawniony redaktor edytuje treść; wersja robocza nie publikuje się bez decyzji.'],
  accounts:['Konta i uprawnienia','Testy odmowy dostępu między kontami, wylogowania i odzyskania dostępu.'],
  search:['Wyszukiwanie','Wyniki zgodne z zapytaniem i uprawnieniami; stany puste i błędy są czytelne.'],
  ai:['Asystent AI','Uzgodniony model, zbiór ewaluacyjny, limity kosztu/czasu i obsługa błędnych odpowiedzi.'],
  media:['Generowanie mediów','Zweryfikowane modele/licencje, kolejka, postęp, anulowanie i zapis rezultatu.'],
  payments:['Płatności','Tryb testowy, weryfikacja webhooka, idempotencja i brak podwójnego obciążenia.'],
  analytics:['Analityka i zgody','Zdefiniowane zdarzenia, minimalizacja danych i przetestowane wybory użytkownika.']};
 function buildBrief(type,goal,selected){
  if(!Object.hasOwn(types,type)||typeof goal!=='string'||goal.length>600||!Array.isArray(selected)||selected.some(k=>!Object.hasOwn(modules,k)))throw new Error('Nieprawidłowy brief.');
  const keys=[...new Set(selected)];
  return ['FORMA / BRIEF ROBOCZY — NIE ZLECENIE',`Typ: ${types[type]}`,`Cel: ${goal.trim()||'Do ustalenia z właścicielem projektu.'}`,'',
   'MODUŁY I KRYTERIA ODBIORU',...(keys.length?keys.map((k,i)=>`${i+1}. ${modules[k][0]}\n   ${modules[k][1]}`):['Brak wybranych modułów.']),
   '', 'ETAPY','1. Uzgodnienie zakresu, danych i odpowiedzialności.','2. Prototyp interakcji i odbiór kierunku.','3. Implementacja z testami niezależnymi od wykonawcy.','4. Testy bezpieczeństwa, dostępności i scenariuszy błędów.','5. Odbiór właściciela, instrukcja i osobna decyzja o wdrożeniu.',
   '', 'DO USTALENIA','Budżet, termin, hosting, integracje, prawa do materiałów i wymagania prywatności.',
   'To lokalny szablon planu. Nie uruchomiono AI, płatności, wdrożenia ani komunikacji z klientem.'].join('\n');
 }
 if(typeof module!=='undefined'&&module.exports)module.exports={buildBrief};
 if(typeof document==='undefined')return;
 const studio=document.querySelector('#studio');if(!studio)return;
 const menu=document.querySelector('#studio-menu'),trigger=document.querySelector('#studio-menu-toggle');let jump=null,menuPhase='closed',closeTicket=0;
 function closeMenu(){if(menuPhase!=='open'||!window.StudioFocus.active())return;closeTicket=window.StudioFocus.ticket();menuPhase='closing';menu.dataset.phase=menuPhase;menu.close();}
 trigger.addEventListener('click',()=>{if(menuPhase!=='closed'||!window.StudioFocus.active())return;jump=null;menuPhase='open';menu.dataset.phase=menuPhase;menu.showModal();trigger.setAttribute('aria-expanded','true');window.StudioFocus.focus(menu.querySelector('#studio-menu-close'));});
 menu.querySelector('#studio-menu-close').addEventListener('click',closeMenu);
 menu.addEventListener('click',event=>{
  if(event.target.closest('button,a,input,select,textarea,label,summary')||getSelection()?.toString())return;
  if(['DIALOG','DIV','NAV','DETAILS'].includes(event.target.tagName)){event.stopPropagation();closeMenu();}
 });
 menu.addEventListener('keydown',event=>{if(window.StudioFocus.plainKey(event)&&event.key==='Escape'){event.preventDefault();event.stopPropagation();closeMenu();}});
 menu.addEventListener('cancel',event=>{event.preventDefault();closeMenu();});
 menu.querySelectorAll('[data-studio-jump]').forEach(button=>button.addEventListener('click',()=>{if(menuPhase!=='open')return;jump=document.getElementById(button.dataset.studioJump);closeMenu();}));
 menu.addEventListener('close',()=>{
  trigger.setAttribute('aria-expanded','false');
  if(window.StudioFocus.valid(closeTicket)){if(jump)window.StudioNavigation.go(jump,trigger);else window.StudioFocus.focus(trigger,closeTicket);}
  jump=null;
  menuPhase='closed';menu.dataset.phase=menuPhase;
 });
 const path=studio.querySelector('#motion-path'),elasticity=studio.querySelector('#motion-elasticity'),depth=studio.querySelector('#motion-depth'),pause=studio.querySelector('#motion-pause');
 function settings(){
  document.querySelector('#elasticity-value').textContent=elasticity.value+'%';document.querySelector('#depth-value').textContent=depth.value+'%';
  document.dispatchEvent(new CustomEvent('studio:motion',{detail:{path:path.value,elasticity:Number(elasticity.value),depth:Number(depth.value)/100,paused:pause.getAttribute('aria-pressed')==='true'}}));
  document.querySelector('#motion-status').textContent=`${path.selectedOptions[0].textContent} · ${pause.getAttribute('aria-pressed')==='true'?'ruch wstrzymany':'ruch aktywny na dużym ekranie'} · bez wysyłania danych.`;
 }
 [path,elasticity,depth].forEach(e=>e.addEventListener('input',settings));
 pause.addEventListener('click',()=>{const paused=pause.getAttribute('aria-pressed')!=='true';pause.setAttribute('aria-pressed',String(paused));pause.textContent=paused?'Wznów ruch':'Zatrzymaj ruch';settings();});
 studio.querySelector('#motion-reset').addEventListener('click',()=>{path.value='helix';elasticity.value='55';depth.value='100';pause.setAttribute('aria-pressed','false');pause.textContent='Zatrzymaj ruch';settings();});
 const selected=()=>[...studio.querySelectorAll('.studio-modules input:checked')].map(e=>e.value);
 const count=()=>document.querySelector('#brief-count').textContent=`Wybrane moduły: ${selected().length} / 8. To plan funkcji, nie deklaracja ich wdrożenia.`;
 studio.querySelectorAll('.studio-modules input').forEach(e=>e.addEventListener('change',count));count();
 studio.querySelector('#brief-build').addEventListener('click',()=>{
  const output=studio.querySelector('#brief-output');output.value=buildBrief(studio.querySelector('#brief-type').value,studio.querySelector('#brief-goal').value,selected());
  studio.querySelector('#brief-status').textContent='Brief gotowy lokalnie. Możesz go zaznaczyć i skopiować; nic nie zostało wysłane.';
 });
 studio.querySelector('#brief-select').addEventListener('click',()=>{const output=studio.querySelector('#brief-output');output.focus();output.select();studio.querySelector('#brief-status').textContent=output.value?'Zaznaczono tekst. Użyj Ctrl+C lub systemowego polecenia Kopiuj.':'Najpierw utwórz brief.';});
 settings();
})();
