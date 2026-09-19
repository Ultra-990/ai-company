(() => {
  "use strict";
  const $ = (id) => document.getElementById(id);
  const ownerPreview=document.body.dataset.ownerPreview==='true';
  let previewShare=null,example=false;
  const names = { planned:"Zaplanowany", in_progress:"W realizacji", review:"Do uzgodnienia / odbioru", completed:"Ukończony", blocked:"Zablokowany" };
  let token = "", epoch = 0, active = null;
  let published = null, chosen = null, view = 'workflow', signature = '', activity = new AbortController();
  let decisionBound=null,pendingDecision=null,sending=false,feedbackCursor=null;
  const element=(tag,text,className)=>{const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(className)n.className=className;return n;};
  const key=(stage,index)=>stage.key||`${index}:${stage.title}`;
  const symbol=state=>({completed:'✓',in_progress:'◉',review:'◎',blocked:'!'}[state]||'○');
  function record(kind, index=null){
    if(ownerPreview||!published||!token)return;
    const controller=new AbortController(),parent=activity.signal,abort=()=>controller.abort();parent.addEventListener('abort',abort,{once:true});
    const timeout=setTimeout(abort,8000);
    (ownerPreview&&window.OwnerSession?window.OwnerSession.fetch:fetch)('/api/client/activity',{method:'POST',headers:{Authorization:`Bearer ${token}`,'Content-Type':'application/json'},body:JSON.stringify({kind,stage_index:index,publication_updated_at:published.updated_at}),credentials:'omit',cache:'no-store',redirect:'error',signal:controller.signal})
      .catch(()=>{}).finally(()=>{clearTimeout(timeout);parent.removeEventListener('abort',abort);});
  }
  function changeView(next, report=true){
    view=next;
    for(const name of ['workflow','materials','reviews'])$('client-view-'+name).hidden=name!==view;
    document.querySelectorAll('[data-client-view]').forEach(b=>{if(b.dataset.clientView===view)b.setAttribute('aria-current','page');else b.removeAttribute('aria-current');});
    if(report)record({workflow:'view_workflow',materials:'view_materials',reviews:'view_reviews'}[view]);
  }
  function selectStage(index, focus=false, report=false){
    const stages=published?.project.milestones||[],s=stages[index];if(!s)return;
    chosen=key(s,index);changeView('workflow',false);
    $('client-stage-detail').hidden=false;
    $('client-stage-title').textContent=s.title;$('client-stage-position').textContent=`ETAP ${index+1} / ${stages.length}`;
    $('client-stage-status').textContent=names[s.status];
    $('client-stage-description').textContent=s.description||'Wykonawca nie opublikował jeszcze szczegółowego zakresu tego etapu.';
    $('client-stage-deliverable').textContent=s.deliverable||'Rezultat nie został jeszcze udostępniony. Sam status nie zastępuje materiału.';
    $('client-stage-review').textContent=s.review_note||'Brak opublikowanych ustaleń dotyczących odbioru.';
    const saved=(published.client_decisions||[]).find(r=>r.stage_index===index);
    $('client-stage-decision').textContent=saved?`Twoja decyzja: ${saved.decision==='accepted'?'akceptacja':'prośba o poprawki'} · ${new Date(saved.created_at).toLocaleString('pl-PL')}\n${saved.comment}${saved.owner_reply?'\nOdpowiedź wykonawcy: '+saved.owner_reply:'\nWykonawca nie potwierdził jeszcze obsługi zgłoszenia.'}`:'';
    $('client-feedback-open').hidden=s.status!=='review'||!!saved||!published.publication_checksum;
    $('client-feedback-open').onclick=()=>openDecision(index);
    $('client-stage-criteria').replaceChildren(...(s.acceptance_criteria?.length?s.acceptance_criteria:['Kryteria nie zostały jeszcze opublikowane.']).map(t=>element('li',t)));
    $('client-stage-prev').disabled=index===0;$('client-stage-next').disabled=index===stages.length-1;
    document.querySelectorAll('[data-stage-index]').forEach(b=>{const current=Number(b.dataset.stageIndex)===index;if(b.closest('#client-stage-menu')){if(current)b.setAttribute('aria-current','step');else b.removeAttribute('aria-current');}else b.setAttribute('aria-pressed',String(current));});
    if(focus){$('client-stage-detail').focus({preventScroll:true});$('client-stage-detail').scrollIntoView({block:'start',behavior:'instant'});}
    if(report)record('view_stage',index);
  }
  function message(text, error = false) { $("client-message").textContent = text; $("client-message").classList.toggle("is-error", error); }
  function logout() {
    epoch++; token = ""; active?.abort(); active = null;
    $("client-login").reset(); $("client-login").hidden = false;
    $("client-project").hidden = true; $("client-logout").hidden = true;
    for (const key of ["title","state","summary","next-step","updated","expiry","progress-number"]) $("client-"+key).textContent = "";
    $("client-progress").value = 0; $("client-milestones").replaceChildren();
    activity.abort();activity=new AbortController();published=null;chosen=null;signature='';view='workflow';
    previewShare=null;example=false;
    if(ownerPreview&&$('client-preview-selector')){$('client-preview-selector').hidden=true;$('client-preview-select').replaceChildren();}
    if(ownerPreview&&$('client-preview-select'))$('client-preview-select').disabled=false;
    $('client-feedback-form').querySelectorAll('button,input,textarea,select').forEach(n=>n.disabled=false);
    closeDecision();pendingDecision=null;sending=false;feedbackCursor=null;$('client-feedback-history').replaceChildren();$('client-feedback-older').hidden=true;$('client-stage-decision').textContent='';
    $('client-welcome').hidden=false;$('client-stage-detail').hidden=true;
    ['stage-menu','materials','reviews','stage-criteria'].forEach(id=>$('client-'+id).replaceChildren());
    ['stage-title','stage-position','stage-status','stage-description','stage-deliverable','stage-review','stage-count','material-count','review-count'].forEach(id=>$('client-'+id).textContent='');
    $("client-refresh").disabled = false;
  }
  function show(data) {
    const p = data.project;
    const previousView=view;
    const first=!published,changed=signature!==JSON.stringify(data);published=data;
    $("client-title").textContent = p.title; $("client-state").textContent = names[p.status];
    $("client-summary").textContent = p.summary; $("client-next-step").textContent = p.next_step;
    $("client-progress-number").textContent = `${p.progress}%`; $("client-progress").value = p.progress;
    if(changed){
    signature=JSON.stringify(data);
    $("client-milestones").replaceChildren();$('client-stage-menu').replaceChildren();$('client-materials').replaceChildren();$('client-reviews').replaceChildren();
    for (const [index, milestone] of p.milestones.entries()) {
      const li=element('li'),b=element('button'),head=element('span',undefined,'client-flow-header');b.type='button';b.dataset.stageIndex=index;b.dataset.state=milestone.status;
      head.append(element('span',milestone.status==='completed'?'✓':String(index+1).padStart(2,'0'),'client-step-number'),element('span',names[milestone.status]));
      b.append(head,element('strong',milestone.title),element('p',(milestone.description||'Zakres do opublikowania.').slice(0,140)));
      b.addEventListener('click',()=>selectStage(index,true,true));li.append(b);$('client-milestones').append(li);
      const item=element('li'),link=element('button');link.type='button';link.dataset.stageIndex=index;link.append(element('span',symbol(milestone.status),'client-menu-status'),element('span',milestone.title));link.addEventListener('click',()=>selectStage(index,true,true));item.append(link);$('client-stage-menu').append(item);
      for(const section of ['materials','reviews']){
        if(section==='materials'?!milestone.deliverable:milestone.status!=='review')continue;
        const card=element('article',undefined,'client-card');card.append(element('p',`ETAP ${index+1} · ${names[milestone.status]}`,'eyebrow'),element('h3',milestone.title),element('p',section==='materials'?milestone.deliverable:milestone.review_note||'Wykonawca oznaczył etap do uzgodnienia. Poproś o szczegóły.','client-document'));
        const open=element('button','Zobacz etap →','client-material-open');open.type='button';open.addEventListener('click',()=>selectStage(index,true,true));card.append(open);$('client-'+section).append(card);
      }
    }
    if(!p.milestones.length){$('client-milestones').append(element('li','Plan etapów nie został jeszcze opublikowany. Powyżej widzisz ustalony zakres i następny krok — nie dodajemy fikcyjnych wykonanych prac.','client-empty'));$('client-stage-detail').hidden=true;chosen=null;}
    else {let index=p.milestones.findIndex((s,i)=>key(s,i)===chosen);if(index<0)index=p.milestones.findIndex(s=>['in_progress','review','blocked'].includes(s.status));selectStage(index<0?0:index);}
    for(const section of ['materials','reviews'])if(!$('client-'+section).children.length)$('client-'+section).append(element('p',section==='materials'?'Nie udostępniono jeszcze materiałów. Pojawią się tutaj po publikacji.':'Brak opublikowanych etapów oczekujących na odbiór.','client-empty'));
    $('client-stage-count').textContent=`${p.milestones.filter(s=>s.status==='completed').length} z ${p.milestones.length} etapów oznaczonych jako ukończone`;
    $('client-material-count').textContent=`${p.milestones.filter(s=>s.deliverable).length} udostępnionych`;
    $('client-review-count').textContent=`${p.milestones.filter(s=>s.status==='review').length} etapów`;
    }
    $("client-updated").textContent = `Ostatnia publikacja: ${new Date(data.updated_at).toLocaleString("pl-PL")}`;
    $("client-expiry").textContent = `Dostęp do: ${new Date(data.expires_at).toLocaleString("pl-PL")}`;
    $("client-login").hidden = true; $("client-project").hidden = false; $("client-logout").hidden = false;
    $('client-welcome').hidden=true;changeView(previousView,false);if(first)record('open_project');
  }
  async function refresh() {
    if ((!token && !(ownerPreview && window.OwnerSession?.active)) || active || document.hidden || $('client-feedback-dialog').open || sending) return;
    const ticket = epoch; const controller = new AbortController(); active = controller;
    const timeout = setTimeout(() => controller.abort(), 10000); $("client-refresh").disabled = true;
    if(ownerPreview)$('client-preview-select').disabled=true;
    try {
      if(ownerPreview&&example)return;
      if(ownerPreview&&previewShare===null){
        const list=await (ownerPreview&&window.OwnerSession?window.OwnerSession.fetch:fetch)('/api/client-history',{headers:{Authorization:`Bearer ${token}`},credentials:'omit',cache:'no-store',redirect:'error',signal:controller.signal});
        if(ticket!==epoch)return;
        if(!list.ok){if([401,403].includes(list.status)){logout();message('Podaj swój token właściciela, nie kod klienta.',true);return;}throw Error('unavailable');}
        const data=await list.json();if(ticket!==epoch)return;
        const requested=Number(new URLSearchParams(location.search).get('share'));
        $('client-preview-select').replaceChildren(...data.shares.map(s=>{const o=element('option',`#${s.project_id} · ${s.title} · publikacja #${s.id}`);o.value=s.id;return o;}));
        previewShare=Number.isSafeInteger(requested)&&requested>0?requested:data.shares[0]?.id;
        if(!previewShare){previewShare=null;message('Nie ma jeszcze publikacji dla klientów. Użyj „Pokaż przykład” lub utwórz publikację: Pulpit → Właściciel → Udostępnienia dla klientów.');return;}
        if(!data.shares.some(s=>s.id===previewShare)){const o=element('option',`Publikacja #${previewShare}`);o.value=previewShare;$('client-preview-select').append(o);}
        $('client-preview-select').value=previewShare;$('client-preview-selector').hidden=false;
      }
      const response = await (ownerPreview&&window.OwnerSession?window.OwnerSession.fetch:fetch)(ownerPreview?`/api/client-shares/${previewShare}`:"/api/client/overview", { headers:{ Authorization:`Bearer ${token}` }, credentials:"omit", cache:"no-store", redirect:"error", signal:controller.signal });
      if (ticket !== epoch) return;
      if (response.status === 401 || (ownerPreview && response.status === 403)) { logout(); message(ownerPreview?'Zaloguj właściciela lub podaj jego poprawny token, nie kod klienta.':"Nie potwierdzono dostępu. Użyj kodu projektu otrzymanego od wykonawcy — token właściciela tutaj nie działa. Kod projektu może być też nieprawidłowy, wygasły lub wycofany.", true); return; }
      if (!response.ok) throw new Error("unavailable");
      let data = await response.json(); if (ticket !== epoch) return;
      if(ownerPreview)data={project:data.project,updated_at:data.share.updated_at,expires_at:data.share.expires_at,source:'owner_preview'};
      show(data);message(ownerPreview?'Podgląd właściciela: nie wymaga kodu klienta, nie rejestruje jego aktywności i nie pozwala wysłać decyzji za klienta.':"Widok aktualny. Pokazujemy informacje udostępnione przez wykonawcę.");
    } catch (_) {
      if (ticket === epoch) message("Nie udało się odświeżyć danych. Ostatnio wyświetlony stan może być nieaktualny.", true);
    } finally {
      clearTimeout(timeout);
      if (ticket === epoch) { active = null; $("client-refresh").disabled = false;if(ownerPreview)$('client-preview-select').disabled=false; }
    }
  }
  $("client-login").addEventListener("submit", (event) => {
    event.preventDefault(); const value = $("client-token").value.trim(); logout(); token = value;
    message("Wczytywanie projektu…"); refresh();
  });
  $("client-logout").addEventListener("click", () => { logout(); message("Wylogowano. Kod został usunięty z pamięci strony."); });
  $("client-refresh").addEventListener("click", refresh);
  // Keep the existing workflow structure; attach the decision controls to its stage.
  const decisionNote=element('p','','client-decision-note');decisionNote.id='client-stage-decision';
  const decisionButton=element('button','Odpowiedz: akceptacja lub poprawki','client-material-open');decisionButton.id='client-feedback-open';decisionButton.type='button';decisionButton.hidden=true;
  $('client-stage-review').after(decisionNote,decisionButton);
  const reviewIntro=$('client-view-reviews').querySelector('.client-muted');reviewIntro.textContent='Wybierz etap do odbioru, sprawdź materiały i wyślij decyzję. Historia Twoich zgłoszeń i odpowiedzi wykonawcy jest dostępna poniżej.';
  const historyButton=element('button','Pokaż historię moich decyzji','client-material-open');historyButton.id='client-feedback-load';historyButton.type='button';
  const feedbackList=element('div');feedbackList.id='client-feedback-history';
  const olderButton=element('button','Starsze decyzje','client-material-open');olderButton.id='client-feedback-older';olderButton.type='button';olderButton.hidden=true;
  $('client-view-reviews').append(historyButton,feedbackList,olderButton);
  function closeDecision(){if($('client-feedback-dialog').open)$('client-feedback-dialog').close();decisionBound=null;pendingDecision=null;$('client-feedback-form').reset();$('client-feedback-binding').textContent='';$('client-feedback-message').textContent='';}
  function openDecision(index){
    if(sending||!published?.publication_checksum)return;
    closeDecision();decisionBound={stage_index:index,publication_checksum:published.publication_checksum,request_id:crypto.randomUUID()};
    $('client-feedback-binding').textContent=`Etap: ${published.project.milestones[index].title} · Wersja SHA-256: ${decisionBound.publication_checksum}`;
    $('client-feedback-dialog').showModal();
  }
  async function feedbackRequest(path,options={}){
    const ticket=epoch,controller=new AbortController(),parent=activity.signal,abort=()=>controller.abort();parent.addEventListener('abort',abort,{once:true});const timer=setTimeout(abort,10000);
    try{
      const r=await (ownerPreview&&window.OwnerSession?window.OwnerSession.fetch:fetch)(path,{...options,headers:{Authorization:`Bearer ${token}`,...(options.body?{'Content-Type':'application/json'}:{})},credentials:'omit',cache:'no-store',redirect:'error',signal:controller.signal});
      if(ticket!==epoch)throw new DOMException('Sesja zamknięta','AbortError');
      if(r.status===401){logout();message('Dostęp wygasł lub został wycofany.');throw Error('Sesja zamknięta.');}
      const data=await r.json();if(ticket!==epoch)throw new DOMException('Sesja zamknięta','AbortError');
      if(!r.ok)throw Error(typeof data.detail==='string'?data.detail.slice(0,1500):'Nie udało się potwierdzić operacji. Sprawdź pola i spróbuj ponownie.');
      return data;
    }finally{clearTimeout(timer);parent.removeEventListener('abort',abort);}
  }
  async function performFeedback(fn){
    if(sending)return;sending=true;const ticket=epoch;
    const controls=[...$('client-feedback-form').querySelectorAll('button,input,textarea,select')];controls.forEach(n=>n.disabled=true);
    try{await fn();}catch(e){if(ticket===epoch){const text=e.name==='AbortError'?'Niepewny zapis. Sprawdź historię; ponowienie identycznej decyzji nie tworzy duplikatu.':e.message;if($('client-feedback-dialog').open)$('client-feedback-message').textContent=text;else message(text,true);}}
    finally{if(ticket===epoch){sending=false;controls.forEach(n=>n.disabled=false);}}
  }
  async function loadFeedback(append=false){
    const data=await feedbackRequest('/api/client/feedback'+(append&&feedbackCursor?`?before=${feedbackCursor}`:''));
    if(!append)feedbackList.replaceChildren();
    for(const r of data.feedback){const card=element('article',undefined,'client-card');card.append(element('h3',r.stage_title),element('p',`${r.decision==='accepted'?'Zaakceptowano':'Zgłoszono poprawki'} · ${new Date(r.created_at).toLocaleString('pl-PL')}`),element('p',r.comment,'client-document'),element('p',r.owner_reply?'Odpowiedź wykonawcy: '+r.owner_reply:'Oczekuje na odpowiedź wykonawcy.'));feedbackList.append(card);}
    if(!data.feedback.length&&!append)feedbackList.append(element('p','Nie wysłano jeszcze decyzji.','client-empty'));
    feedbackCursor=data.next_cursor;olderButton.hidden=!feedbackCursor;
  }
  historyButton.addEventListener('click',()=>performFeedback(()=>loadFeedback()));olderButton.addEventListener('click',()=>performFeedback(()=>loadFeedback(true)));
  if(ownerPreview){
    document.title='Podgląd panelu klienta · Właściciel';$('client-token').maxLength=4096;
    historyButton.hidden=true;reviewIntro.textContent='Podgląd właściciela jest tylko do odczytu. Nie możesz tutaj wysłać decyzji w imieniu klienta.';
    $('client-login').querySelector('h2').textContent='Podgląd klienta dla właściciela';
    $('client-login').querySelector('label').textContent='Twój token właściciela (ten sam co w Centrum realizacji)';
    const paragraphs=$('client-login').querySelectorAll('p');paragraphs[0].textContent='Nie potrzebujesz kodu klienta. Po połączeniu wybierz istniejącą publikację. Jeśli chcesz tylko obejrzeć interfejs, użyj przykładu poniżej.';if(paragraphs[1])paragraphs[1].textContent='Podgląd nie zmienia projektu ani nie zapisuje aktywności odbiorcy kodu.';
    const demo=element('button','Pokaż przykład panelu klienta — bez logowania','client-material-open');demo.type='button';demo.id='client-preview-example';
    const selector=element('label','Publikacja do podglądu (30 najnowszych; inne dostępne z historii)');selector.id='client-preview-selector';selector.hidden=true;
    const select=element('select');select.id='client-preview-select';selector.append(select);$('client-message').before(demo,selector);
    select.addEventListener('change',()=>{previewShare=Number(select.value);refresh();});
    demo.addEventListener('click',()=>{logout();example=true;show({project:{title:'PRZYKŁAD — strona pracowni',summary:'Dane demonstracyjne pokazują wygląd panelu. To nie jest rzeczywisty projekt ani raport pracy.',progress:40,status:'in_progress',next_step:'Przykład: uzgodnienie układu portfolio.',milestones:[{key:'scope',title:'Ustalenia',status:'completed',description:'Cel, zakres i kryteria.',deliverable:'Przykładowa specyfikacja: strona główna, portfolio, kontakt.'},{key:'design',title:'Projekt interfejsu',status:'review',description:'Układ strony i wersji mobilnej.',deliverable:'Przykład opisu makiety do omówienia.'},{key:'build',title:'Budowa strony',status:'in_progress',description:'Przykładowy etap tworzenia komponentów.'},{key:'test',title:'Testy i przekazanie',status:'planned',description:'Kontrola funkcji oraz instrukcja użycia.'}]},updated_at:new Date().toISOString(),expires_at:new Date().toISOString(),source:'example'});$('client-expiry').textContent='PRZYKŁAD · bez dostępu do danych klientów';message('TRYB DEMONSTRACYJNY — wszystkie dane są przykładowe. Nic nie zostało zapisane.');});
    $('client-logout').addEventListener('click',()=>{selector.hidden=true;select.replaceChildren();});
  }
  $('client-feedback-close').addEventListener('click',closeDecision);
  $('client-feedback-dialog').addEventListener('close',()=>{if(!$('client-feedback-dialog').open)closeDecision();});
  $('client-feedback-form').addEventListener('submit',e=>{
    e.preventDefault();if(!decisionBound)return;
    const body={...decisionBound,decision:$('client-feedback-choice').value,comment:$('client-feedback-comment').value.trim(),confirmed:$('client-feedback-confirm').checked};
    if(pendingDecision&&JSON.stringify(pendingDecision)!==JSON.stringify(body)){$('client-feedback-message').textContent='Po niepewnym zapisie sprawdź historię przed zmianą decyzji. Nie nadpisujemy poprzedniego zgłoszenia.';return;}
    pendingDecision=body;
    performFeedback(async()=>{await feedbackRequest('/api/client/feedback',{method:'POST',body:JSON.stringify(body)});closeDecision();message('Decyzja zapisana. Nie zmieniono wewnętrznych zadań ani uprawnień agentów.');}).then(()=>{if(token&&!$('client-feedback-dialog').open)refresh();});
  });
  document.querySelectorAll('[data-client-view]').forEach(b=>b.addEventListener('click',()=>changeView(b.dataset.clientView)));
  for(const [id,offset] of [['prev',-1],['next',1]])$('client-stage-'+id).addEventListener('click',()=>{const stages=published?.project.milestones||[];selectStage(stages.findIndex((s,i)=>key(s,i)===chosen)+offset,true,true);});
  window.addEventListener("pagehide", logout);
  document.addEventListener("visibilitychange", () => { if (!document.hidden) refresh(); });
  setInterval(refresh, 30000);
})();
