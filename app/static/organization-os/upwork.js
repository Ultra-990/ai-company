/* Manual intake only. Qwen runs exclusively after an explicit owner action. */
(() => {
  'use strict';
  const $=id=>document.getElementById(id);
  const node=(tag,text)=>{const n=document.createElement(tag);n.textContent=text;return n;};
  let busy=false, selected=null, pending=null, cursor=null, current=null;
  function message(text,error=false){$('message').textContent=text;$('message').classList.toggle('error',error);}
  async function request(path, options={}){
    if(!window.OwnerSession?.active)throw Error('Najpierw zaloguj właściciela w górnym pasku.');
    const r=await window.OwnerSession.fetch(path,{...options,headers:{'Content-Type':'application/json'},signal:AbortSignal.timeout(200000)});
    const data=await r.json();
    if(!r.ok)throw Error(typeof data.detail==='string'?data.detail:JSON.stringify(data.detail||'Nie udało się wykonać operacji.'));
    return data;
  }
  async function act(fn){
    if(busy)return;busy=true;
    // Disable workspace actions, not the shared session/logout control.
    for(const b of document.querySelectorAll('main button'))b.disabled=true;
    try{await fn();}catch(e){message(e.message+' Po przerwie odczytaj stan przed ponowieniem.',true);}
    finally{busy=false;for(const b of document.querySelectorAll('main button'))b.disabled=false;updateAnalysisButton();}
  }
  function updateAnalysisButton(){
    const state=current?.analysis?.state;
    $('analyse').disabled=busy||!selected||!!(state&&state!=='queued');
    $('analyse').textContent=state==='queued'?'Uruchom przygotowaną analizę Qwen':'Analizuj zakres lokalnym Qwenem';
  }
  async function loadOrders(more=false){
    const data=await request('/api/upwork-orders'+(more&&cursor?'?before='+cursor:''));
    if(!more)$('orders').replaceChildren();
    $('profile').textContent='Obecny wykonawca: '+data.profile;
    for(const order of data.orders){const b=node('button',`#${order.project_id} · ${order.title}`);b.type='button';b.className='order';b.disabled=busy;b.onclick=()=>act(()=>loadDetail(order.project_id));$('orders').append(b);}
    if(!more&&!data.orders.length)$('orders').append(node('p','Nie zapisano jeszcze zleceń Upwork.'));
    cursor=data.next_cursor;$('more').hidden=!cursor;
  }
  function render(data){
    current=data;selected=data.project_id;$('detail').hidden=false;
    $('project-title').textContent=data.brief.title;
    $('binding').textContent=`Projekt #${selected} · analiza zadania #${data.tasks[0].id} · kontrakt nie został przyjęty przez system`;
    const intake=data.brief.upwork_intake;
    $('saved-brief').textContent=[intake.job_text,'Kryteria:',...intake.acceptance_criteria,intake.notes,'Źródło: '+(intake.source_url||'opis wklejony ręcznie')].join('\n');
    $('continue').href='/os/work?project='+selected;
    $('stages').replaceChildren();
    const statuses={pending:'Zaplanowane',in_progress:'W toku',blocked:'Zablokowane',completed:'Ukończone',cancelled:'Anulowane'};
    for(const t of data.tasks){const card=node('article','');card.className='task';card.append(node('h3',t.title),node('p',statuses[t.status]||t.status),node('p',t.delegation?.worker?.name||'Przydział nastąpi przy analizie'));$('stages').append(card);}
    const run=data.analysis;
    const states={queued:'Przygotowana — czeka na uruchomienie',running:'Qwen pracuje',awaiting_review:'Wynik zapisany — wymaga odbioru',failed:'Analiza nieudana',uncertain:'Wykonanie niepewne — sprawdź historię Qwen',stale:'Instrukcja nieaktualna',cancelled:'Anulowana'};
    $('analysis-state').textContent=run?`Analiza #${run.id}: ${states[run.state]||run.state}${run.error_code?' · '+run.error_code:''}`:'Analiza nie została uruchomiona.';
    let result=run?.result_content||'Brak odpowiedzi modelu. Nie oznacza to braku ryzyka ani gotowości do wykonania.';
    if(run?.result_content){try{const v=JSON.parse(run.result_content);if(v.fit){const labels={SUPPORTED:'Wstępnie dopasowane',CLARIFY:'Wymaga wyjaśnienia',UNSUPPORTED:'Poza obecnym profilem'};result=`${labels[v.fit]||v.fit}\n\n${v.reason}`;for(const [key,label] of [['questions','Pytania'],['scope','Zakres'],['acceptance_cases','Scenariusze odbioru'],['exclusions','Wyłączenia / braki']]){if(Array.isArray(v[key])&&v[key].length)result+='\n\n'+label+'\n'+v[key].map(s=>'• '+s).join('\n');}}}catch{/* Historical prose remains plain text. */}}
    if(run?.error_code==='scope_contract_invalid')result='Qwen zwrócił nieprawidłową lub zbyt długą analizę. Nie zapisano wyniku zadania. Sprawdź zakres i historię Qwen w Centrum realizacji przed kontrolowanym ponowieniem.';
    $('analysis-result').textContent=result;
    updateAnalysisButton();
  }
  async function loadDetail(id){render(await request('/api/upwork-orders/'+id));}
  window.UpworkStarters?.mount($('upwork-starters'), example => {
    if(busy)return;
    const form=$('upwork-intake');
    const fields=['title','source_url','job_text','criteria','notes'];
    const hasDraft=fields.some(name=>form.elements.namedItem(name).value.trim());
    if((hasDraft||pending)&&!confirm('Zastąpić bieżący formularz przykładem? Po niepewnym zapisie najpierw sprawdź listę. Zapisane projekty pozostaną w historii.'))return;
    pending=null;current=null;selected=null;
    for(const name of fields)form.elements.namedItem(name).value=name==='criteria'?example.criteria.join('\n'):example[name];
    $('detail').hidden=true;updateAnalysisButton();
    message('Wstawiono przykład ćwiczeniowy. Sprawdź kryteria; nic nie zapisano i nie uruchomiono Qwena.');
    form.elements.namedItem('title').focus();
  });
  $('access').onsubmit=e=>{e.preventDefault();act(async()=>{await loadOrders();$('workspace').hidden=false;message('Połączono. Wybierz zlecenie lub zapisz nowe.');});};
  $('upwork-intake').onsubmit=e=>{e.preventDefault();act(async()=>{
    const f=new FormData(e.target),body={title:f.get('title').trim(),job_text:f.get('job_text').trim(),source_url:f.get('source_url').trim(),notes:f.get('notes').trim(),acceptance_criteria:f.get('criteria').split('\n').map(x=>x.trim()).filter(Boolean)};
    const signature=JSON.stringify(body);
    if(pending&&pending.signature!==signature)throw Error('Zmieniono zakres po próbie zapisu. Najpierw sprawdź listę; dla innego zakresu użyj Nowy formularz.');
    pending||={signature,id:crypto.randomUUID()};
    render(await request('/api/upwork-orders',{method:'POST',body:JSON.stringify({...body,request_id:pending.id})}));
    await loadOrders();message('Zapisano projekt i cztery zadania. Qwen jeszcze nie pracuje.');$('detail').scrollIntoView({block:'start'});
  });};
  $('new-intake').onclick=()=>{if(pending&&!confirm('Sprawdź listę po niepewnym zapisie. Rozpocząć osobny formularz?'))return;pending=null;$('upwork-intake').reset();message('Nowy formularz. Zapisane projekty pozostają w historii.');};
  $('analyse').onclick=()=>act(async()=>{
    if(!selected)return;
    const id=selected;message('Przygotowanie kierownika, wykonawców i instrukcji…');
    const run=await request(`/api/upwork-orders/${id}/analysis`,{method:'POST'});
    if(run.state==='queued'){
      message('Lokalny Qwen analizuje zakres. Może to potrwać do 3 minut. Zamknięcie karty nie anuluje wykonania.');
      await request(`/api/local-inference/${run.id}/run`,{method:'POST'});
    }
    await loadDetail(id);message('Odczytano stan analizy. Sprawdź wynik i otwarte pytania poniżej.');
  });
  $('refresh').onclick=()=>act(async()=>{await loadOrders();if(selected)await loadDetail(selected);message('Odświeżono dane.');});
  $('read-state').onclick=()=>act(()=>loadDetail(selected));
  $('more').onclick=()=>act(()=>loadOrders(true));
  window.addEventListener('pagehide',()=>{pending=null;current=null;selected=null;$('upwork-intake').reset();$('orders').replaceChildren();$('analysis-result').textContent='';$('saved-brief').textContent='';$('workspace').hidden=true;});
})();
