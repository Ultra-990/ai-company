(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const make = (tag, text, cls) => { const e=document.createElement(tag); if(text!==undefined)e.textContent=text;if(cls)e.className=cls;return e; };
  const link=(text,href,cls)=>{const a=make('a',text,cls);a.href=href;return a;};
  const state={departments:[],root:null,overview:null,next:null,alerts:null,loaded:false};
  let busy=false, stopped=false, timer, signature='', controller;
  const number=n=>Number.isFinite(n)?String(n):'—';
  const progress=n=>n.measurement_state==='unmeasured'?'Nie zmierzono':`${number(n.progress)}% · ${n.measurement_state==='partial'?'pomiar częściowy':'pomiar zadań'}`;
  const workLink=key=>`/os/work?unit=${encodeURIComponent(key)}`;
  function cards(){
    const query=$('command-search').value.trim().toLocaleLowerCase('pl');
    const items=state.departments.filter(n=>[n.name,n.operating_model?.mission,n.operating_model?.outputs].join(' ').toLocaleLowerCase('pl').includes(query));
    $('department-count').textContent=state.loaded?`${items.length} z ${state.departments.length} działów · wybierz rezultat, nie sam procent.`:'Dane działów są niedostępne. Użyj „Odśwież”.';
    $('command-departments').replaceChildren();
    for(const n of items){
      const a=link('',`#department/${encodeURIComponent(n.key)}`,'department-card');
      a.append(make('span',String(state.departments.indexOf(n)+1).padStart(2,'0'),'department-number'),make('h2',n.name),make('p',n.operating_model?.mission||'Zakres wymaga zdefiniowania.'),make('span',`${number(n.subtree_task_count)} zadań · ${progress(n)} →`,'card-meta'));
      $('command-departments').append(a);
    }
    if(state.loaded&&!items.length)$('command-departments').append(make('p','Brak pasujących działów. Zmień wyszukiwanie.','empty-state'));
  }
  function detail(key){
    const box=$('department-detail'),n=state.departments.find(x=>x.key===key);box.replaceChildren();
    if(!n){box.append(make('p',state.loaded?'Nie znaleziono tego działu. Wybierz go z aktualnej struktury.':'Trwa odczyt działów. Jeśli dane się nie pojawią, użyj „Odśwież”.','empty-state'));return;}
    const op=n.operating_model,head=make('div',undefined,'page-intro');
    head.append(make('p','DZIAŁ / ODPOWIEDZIALNOŚĆ','eyebrow'),make('h1',n.name),make('p',op?.mission||'Zakres do ustalenia.'));box.append(head);
    if(op)box.append(link(`${op.action_title} →`,workLink(op.target_key),'primary-button'));
    box.append(make('p',`${number(n.subtree_project_count)} projektów · ${number(n.subtree_task_count)} zadań · ${number(n.subtree_blocked_task_count)} blokad · ${progress(n)}`,'charter-note'));
    const grid=make('div',undefined,'charter-grid');
    for(const [title,text] of [['Co przekazujesz',op?.inputs],['Co ma powstać',op?.outputs]]){const card=make('article',undefined,'charter-card');card.append(make('h2',title),make('p',text||'Wymaga określenia.'));grid.append(card);}
    const next=make('article',undefined,'charter-card');next.append(make('h2','Najbliższy krok'),make('p',n.foundation?.next_step||'Ustal zakres, odpowiedzialność i kryteria odbioru.'));grid.append(next);
    const acceptance=make('article',undefined,'charter-card'),list=make('ul');acceptance.append(make('h2','Po czym poznamy gotowość'));
    for(const c of n.foundation?.completion_criteria||[])list.append(make('li',c));acceptance.append(list);grid.append(acceptance);box.append(grid);
    box.append(make('p','Kierownik planuje → wykonawca przygotowuje wynik → kontroler sprawdza → właściciel odbiera. Konkretne osoby lub role przydzielisz w projekcie.','charter-note'));
    box.append(make('p',op?.note||'Wykonanie wymaga jawnego zlecenia.','charter-note'));
    const tools=make('div',undefined,'decision-tools');tools.append(link('Projekty i przydziały →',op?workLink(op.target_key):'/os/work'),link('Przekazanie klientowi →','/os/publishing'),link('Historia i poprawki →','/os/clients'));box.append(tools);
    const evidence=make('article',undefined,'charter-card');evidence.append(make('h2','Istniejące fundamenty — wymagają odbioru'),make('p',n.foundation?.note||'Brak zinwentaryzowanych materiałów.'));
    const paths=make('ul');for(const a of n.foundation?.artifacts||[])paths.append(make('li',`${a.reference} · ${a.present?'plik obecny':'brak pliku'}`));evidence.append(paths);box.append(evidence);
  }
  function alerts(){
    const box=$('command-alerts');box.replaceChildren();
    if(state.alerts===null){box.append(make('p','Nie można potwierdzić stanu powiadomień. Spróbuj odświeżyć.','empty-state'));return;}
    if(!state.alerts.length){box.append(make('p','Brak aktywnych powiadomień. Nie oznacza to automatycznie braku blokad lub wyników do odbioru — te sprawdzisz w projektach.','empty-state'));return;}
    for(const a of state.alerts){const card=make('article',undefined,'alert-card');card.append(make('p',a.severity||'Informacja','eyebrow'),make('h2',a.title||'Powiadomienie'),make('p',a.message||''));box.append(card);}
  }
  function current(){let raw=location.hash.slice(1)||'overview';if(raw.startsWith('department/')){try{return ['department',decodeURIComponent(raw.slice(11))];}catch{return ['departments'];}}return [new Set(['overview','departments','delivery','decisions']).has(raw)?raw:'overview'];}
  function view(){
    const [name,key]=current();document.querySelectorAll('[data-section]').forEach(e=>e.hidden=e.dataset.section!==name);
    document.querySelectorAll('[data-view]').forEach(e=>{if(e.dataset.view===(name==='department'?'departments':name))e.setAttribute('aria-current','page');else e.removeAttribute('aria-current');});
    $('view-breadcrumb').textContent=({overview:'PRZEGLĄD',departments:'DZIAŁY',department:'ODPOWIEDZIALNOŚĆ',delivery:'REALIZACJA',decisions:'DECYZJE'})[name];
    if(name==='department')detail(key);
  }
  function menu(owner){
    $('command-menu-label').textContent=owner?'KIERUNEK I ZATWIERDZENIA':'PLAN I KOORDYNACJA';$('command-menu-title').textContent=owner?'Centrum właściciela':'Brain · następny krok';
    const body=$('command-menu-body');body.replaceChildren();
    if(!owner)body.append(make('p',state.next?`${state.next.title} — ${state.next.reason||''}`:'Rekomendacja jest niedostępna. Zobacz bieżące projekty.'));
    const entries=owner?[['Stan organizacji','#overview'],['Powiadomienia i decyzje','#decisions'],['Zlecenia i przydziały','/os/work'],['Odbiór zadań i pliki','/os/review'],['Publikacje dla klientów','/os/publishing'],['Historia projektów i klientów','/os/clients'],['Podgląd panelu klienta','/os/client-preview']]:[['Odpowiedzialność działów','#departments'],['Przydziel role w projekcie','/os/work'],['Instrukcje, wyniki i kolejka próbna','/os/work']];
    for(const [title,path] of entries){const a=link(`${title} →`,path);a.addEventListener('click',()=>$('command-menu').close());body.append(a);}
    body.append(make('p',owner?'Publikujesz wyłącznie sprawdzone materiały. Token właściciela podajesz tylko w narzędziach, które go wymagają.':'Brain nie wykonuje obecnie autonomicznej pracy. Kolejka próbna nie uruchamia modelu, GPU ani procesów klienta.'));
    $('command-menu').showModal();
  }
  async function refresh(){
    if(busy||stopped||document.hidden)return;busy=true;$('command-refresh').disabled=true;controller=new AbortController();const deadline=setTimeout(()=>controller.abort(),8000);
    const paths=['tree','overview','next-move','alerts'];
    try{
      const results=await Promise.allSettled(paths.map(async path=>{
        const r=await fetch(`/api/organization-os/${path}`,{signal:controller.signal,cache:'no-store',credentials:'same-origin',redirect:'error'});if(!r.ok)throw new Error(`HTTP ${r.status}`);
        const data=await r.json();
        if(!data||typeof data!=='object'||Array.isArray(data))throw new Error('Niepoprawne dane');
        if(path==='tree'&&(!Array.isArray(data.nodes)||!data.nodes.every(n=>n&&Array.isArray(n.children)&&n.children.every(d=>d&&typeof d.key==='string'&&typeof d.name==='string'))))throw new Error('Niepoprawna struktura');
        if(path==='overview'&&(!Number.isFinite(data.projects)||!Number.isFinite(data.blocked_tasks)))throw new Error('Niepoprawne podsumowanie');
        if(path==='alerts'&&(!Array.isArray(data.alerts)||!data.alerts.every(a=>a&&typeof a.title==='string')))throw new Error('Niepoprawne powiadomienia');
        if(path==='next-move'&&typeof data.title!=='string')throw new Error('Niepoprawna rekomendacja');
        return data;
      }));
      if(stopped)return;
      const failed=results.map((r,i)=>r.status==='rejected'?paths[i]:null).filter(Boolean),[tree,overview,next,notifications]=results.map(r=>r.status==='fulfilled'?r.value:null);
      if(tree&&Array.isArray(tree.nodes)){
        const root=tree.nodes.find(n=>n.kind==='organization')||tree.nodes[0];state.root=root;state.departments=root?.children||[];state.loaded=true;
        const nextSignature=JSON.stringify(state.departments);if(nextSignature!==signature){signature=nextSignature;cards();if(current()[0]==='department')detail(current()[1]);}
      }
      state.overview=overview;state.next=next;state.alerts=Array.isArray(notifications?.alerts)?notifications.alerts:null;alerts();
      $('metric-projects').textContent=number(overview?.projects);$('metric-review').textContent=number(overview?.awaiting_review_tasks);$('metric-blocked').textContent=number(overview?.blocked_tasks);
      $('metric-progress').textContent=state.root?.measurement_state!=='unmeasured'&&Number.isFinite(overview?.organization_progress)?`${overview.organization_progress}%`:'—';
      $('metric-coverage').textContent=overview?`${number(overview.unassigned_tasks)} zadań poza projektami · pomiar nie oznacza gotowości firmy`:'Brak aktualnego pomiaru';
      $('command-next-title').textContent=next?.title||'Rekomendacja chwilowo niedostępna';$('command-next-reason').textContent=next?.reason||'Nie uruchomiono żadnego zadania. Otwórz projekt i sprawdź jego stan.';
      $('command-error').hidden=!failed.length;$('command-error').textContent=failed.length?`Nie odczytano: ${failed.join(', ')}. ${state.loaded?'Ostatnio odczytana struktura pozostaje widoczna. ':''}Menu i narzędzia nadal działają. Spróbuj odświeżyć.`:'';
      $('command-sync').textContent=failed.length?'Dane częściowo niedostępne':`Odczyt ${new Date().toLocaleTimeString('pl-PL')} · odświeżanie co 30 s`;
      if(!state.loaded)cards();
    }catch{
      if(!stopped){$('command-error').hidden=false;$('command-error').textContent='Nie udało się wyświetlić danych. Menu i narzędzia nadal działają. Spróbuj odświeżyć.';$('command-sync').textContent='Dane wymagają ponownego odczytu';}
    }finally{clearTimeout(deadline);busy=false;if(!stopped)$('command-refresh').disabled=false;}
  }
  $('command-owner').addEventListener('click',()=>menu(true));$('command-brain').addEventListener('click',()=>menu(false));$('command-menu-close').addEventListener('click',()=>$('command-menu').close());
  $('command-search').addEventListener('input',cards);$('command-refresh').addEventListener('click',refresh);
  window.addEventListener('hashchange',()=>{view();$('command-main').focus({preventScroll:true});window.scrollTo({top:0,behavior:'instant'});});
  document.addEventListener('visibilitychange',()=>{if(!document.hidden)refresh();});
  window.addEventListener('pagehide',()=>{stopped=true;clearInterval(timer);controller?.abort();});
  window.addEventListener('pageshow',e=>{if(e.persisted){stopped=false;timer=setInterval(refresh,30000);refresh();}});
  cards();view();refresh();timer=setInterval(refresh,30000);
})();
