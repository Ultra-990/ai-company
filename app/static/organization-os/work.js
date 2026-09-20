/* Owner workbench: HTML preview only inside an opaque-origin, scriptless sandbox. */
(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  let token = '', epoch = 0, busy = false, selected = null, cursor = null, polling = false;
  let controller = new AbortController(), pending = null;
  let packet = null, review = null;
  let queueCursor=null;
  let inferenceCursor=null;
  let unitKeys=new Map();
  const node = (tag, text, className) => { const n = document.createElement(tag); if (text !== undefined) n.textContent = text; if (className) n.className = className; return n; };
  const labels = {pending:'Zaplanowane', in_progress:'W toku', completed:'Ukończone', blocked:'Zablokowane', cancelled:'Anulowane', awaiting_review:'Wynik do odbioru', approved:'Zatwierdzone', rejected:'Odrzucone'};
  function message(text, error=false) { $('message').textContent=text; $('message').classList.toggle('error',error); if($('agent-session').open){$('agent-message').textContent=text;$('agent-message').classList.toggle('error',error);} }
  function clear() {
    epoch++; controller.abort(); controller=new AbortController(); token=''; busy=false; polling=false; selected=null; cursor=null; pending=null;unitKeys=new Map();
    $('access').reset(); $('intake').reset(); $('workspace').hidden=true; $('detail').hidden=true;
    $('project-guide').replaceChildren();$('project-guide').hidden=true;
    closePreview();closeAgent();
    queueCursor=null;$('local-queue-jobs').replaceChildren();$('local-queue-state').textContent='';$('local-queue-more').hidden=true;
    $('inference-runs').replaceChildren();$('inference-state').textContent='';
    inferenceCursor=null;$('inference-more').hidden=true;$('inference-scope').value='project';$('inference-attention').checked=false;
    ['orders','tasks','criteria','artifacts','unit','check-limits','check-findings','teams'].forEach(id=>$(id).replaceChildren());
    $('check-report').hidden=true;$('check-summary').textContent='';$('check-binding').textContent='';
    ['project-title','project-goal','project-meta'].forEach(id=>$(id).textContent='');
    document.querySelectorAll('button,input,textarea,select').forEach(n=>n.disabled=false);
  }
  async function request(path, options={}, blob=false, waitMs=15000) {
    const ticket=epoch, local=new AbortController(), parent=controller.signal;
    const abort=()=>local.abort(); parent.addEventListener('abort',abort,{once:true});
    const timeout=setTimeout(abort,waitMs);
    try {
      const r=await (window.OwnerSession?.fetch||fetch)(path,{...options,cache:'no-store',redirect:'error',credentials:'omit',signal:local.signal,
        headers:{Authorization:`Bearer ${token}`,...(options.body?{'Content-Type':'application/json'}:{})}});
      if(ticket!==epoch)throw new DOMException('Sesja zamknięta','AbortError');
      if(!r.ok){
        let detail='';
        if(r.status===409){try{const body=await r.json();if(typeof body.detail==='string')detail=body.detail.slice(0,1500);}catch{/* generic fallback */}}
        if(ticket!==epoch)throw new DOMException('Sesja zamknięta','AbortError');
        const e=new Error(detail||({401:'Nieprawidłowy token właściciela.',403:'Wymagana rola właściciela.',404:'Nie znaleziono wskazanego zasobu.',409:'Konflikt zapisu lub integralności. Odśwież dane przed ponowieniem.',422:'Sprawdź wymagane pola i ich długości. Kryteria: maks. 20 po 500 znaków; wynik: 32000 znaków; dowody odbioru: maks. 50 po 4000 znaków.',503:'Usługa niedostępna. Sprawdź stan przed ponowieniem zapisu.'})[r.status]||`Błąd HTTP ${r.status}`);e.status=r.status;throw e;
      }
      const value=blob?await r.blob():await r.json();
      if(ticket!==epoch)throw new DOMException('Sesja zamknięta','AbortError');
      return value;
    } finally {clearTimeout(timeout);parent.removeEventListener('abort',abort);}
  }
  async function act(callback) {
    if(busy)return;if(polling){message('Trwa odświeżanie. Spróbuj ponownie za chwilę.');return;}busy=true;const ticket=epoch;
    const controls=[...document.querySelectorAll('button,input,textarea,select')].filter(n=>!['logout','theme','preview-close'].includes(n.id)&&!n.closest('.app-navigation,#owner-session-dialog'));
    controls.forEach(n=>n.disabled=true);
    try {await callback();}catch(e){if(ticket!==epoch)return;if([401,403].includes(e.status))clear();message(e.name==='AbortError'?'Niepewny wynik żądania. Sprawdź listę; ponowienie formularza zachowa identyfikator zlecenia.':e.message,true);}
    finally {if(ticket===epoch){busy=false;controls.forEach(n=>n.disabled=false);}}
  }
  function markSelected(){document.querySelectorAll('[data-project]').forEach(b=>b.setAttribute('aria-current',String(Number(b.dataset.project)===selected)));}
  async function loadOrders(append=false) {
    const data=await request('/api/work-orders'+(append&&cursor?`?before=${cursor}`:''));
    if(!append)$('orders').replaceChildren();
    if(!data.orders.length&&!append)$('orders').append(node('p','Nie ma jeszcze zleceń. Dodaj pierwsze po lewej.','muted'));
    for(const o of data.orders){const b=node('button',`#${o.project_id} · ${o.title}`,'order');b.type='button';b.dataset.project=o.project_id;b.addEventListener('click',()=>act(()=>loadDetail(o.project_id)));$('orders').append(b);}
    cursor=data.next_cursor;$('more').hidden=!cursor;markSelected();
  }
  async function download(taskId,artifactId) {
    const blob=await request(`/api/tasks/${taskId}/workspace-packages/${artifactId}/download`,{},true);
    const url=URL.createObjectURL(blob), a=node('a');a.href=url;a.download=`task-${taskId}-package-${artifactId}.zip`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
    message('Pobrano paczkę. Zapis nie oznacza wykonania ani odbioru.');
  }
  async function diskExport(taskId, packageId, create) {
    const result=await request(`/api/tasks/${taskId}/workspace-packages/${packageId}/disk-export`,create?{method:'POST'}:{});
    if(create)await loadDetail(selected);
    message(`${create?'Zapis na dysku Linux':'Weryfikacja zapisu'}: ${result.directory} · ${result.file_count} plików · sumy zgodne. Kod nie został uruchomiony.`);
  }
  function resetPreview() {
    $('preview-frame').removeAttribute('srcdoc');
    $('preview-binding').textContent='';$('preview-limits').replaceChildren();
  }
  function closePreview() {if($('preview').open)$('preview').close();resetPreview();}
  function previewSize(phone) {
    $('preview-stage').classList.toggle('phone',phone);
    $('preview-phone').setAttribute('aria-pressed',String(phone));
    $('preview-wide').setAttribute('aria-pressed',String(!phone));
  }
  async function previewPackage(taskId,packageId) {
    closePreview();
    let data;
    try {data=await request(`/api/tasks/${taskId}/workspace-packages/${packageId}/preview`);}
    catch(e){if(e.status===422)e.message='Ta paczka nie mieści się w profilu podglądu: wymagane index.html, do 5000 elementów, 128 poziomów i 128 KiB lokalnego CSS. Pobierz ZIP lub sprawdź pliki.';throw e;}
    if(data.profile!=='organization-os.static-preview.v1'||typeof data.document!=='string')throw new Error('Nieobsługiwany kontrakt podglądu.');
    const frame=$('preview-frame');
    // Never grant script or same-origin privileges. No token enters the document.
    frame.setAttribute('sandbox','');frame.referrerPolicy='no-referrer';
    frame.srcdoc=data.document;
    $('preview-binding').textContent=`Zadanie #${data.task_id} · Paczka #${data.package_id} · SHA-256: ${data.source_checksum} · Pominięte elementy/atrybuty: ${data.omitted_items}`;
    $('preview-limits').replaceChildren(...data.limitations.map(t=>node('li',t)));
    previewSize(false);$('preview').showModal();
    message('Otworzono statyczny podgląd konkretnej wersji. Nie zmieniono postępu ani odbioru.');
  }
  function renderCheck(report) {
    $('check-report').hidden=false;
    const outcomes={checks_passed:'Kontrole profilu zaliczone',issues_found:'Wykryto problemy',incomplete:'Analiza niepełna'};
    $('check-summary').textContent=`${outcomes[report.outcome]||report.outcome}. Zaliczone: ${report.counts.passed}; problemy: ${report.counts.failed}; uwagi: ${report.counts.warning}. Nie uruchomiono kodu ani nie odebrano produktu.`;
    $('check-binding').textContent=`Raport #${report.report_id} · Paczka #${report.package_id} · SHA-256 źródła: ${report.source_checksum}`;
    $('check-limits').replaceChildren(...report.not_checked.map(t=>node('li',t)));
    $('check-findings').replaceChildren();
    const statuses={failed:'PROBLEM',warning:'UWAGA',passed:'OK'};
    for(const c of [...report.checks].sort((a,b)=>({failed:0,warning:1,passed:2}[a.status]-{failed:0,warning:1,passed:2}[b.status]))){
      const p=node('p',`${statuses[c.status]||c.status} · ${c.path||'Paczka'}${c.line?`:${c.line}`:''} — ${c.message}`);$('check-findings').append(p);
    }
  }
  async function inspectPackage(taskId,packageId) {
    $('check-report').hidden=true;
    const report=await request(`/api/tasks/${taskId}/workspace-packages/${packageId}/static-check`,{method:'POST'});
    await loadDetail(selected);renderCheck(report);message(`Raport #${report.report_id} zapisany. To kontrola plików bez wykonywania aplikacji.`);
  }
  async function loadCheck(taskId,reportId) {
    $('check-report').hidden=true;
    renderCheck(await request(`/api/tasks/${taskId}/static-checks/${reportId}`));message('Odczytano raport i ponownie sprawdzono powiązanie z paczką.');
  }
  function resetAgent(){
    packet=null;review=null;
    ['agent-instructions','agent-result','agent-source','agent-review-content','agent-review-reason','agent-review-evidence'].forEach(id=>$(id).value='');
    $('agent-binding').textContent='';$('agent-message').textContent='';
    $('agent-handoff').hidden=true;$('agent-review').hidden=true;
  }
  function closeAgent(){if($('agent-session').open)$('agent-session').close();resetAgent();}
  async function openPacket(taskId,packetId=null){
    const data=await request(packetId?`/api/tasks/${taskId}/agent-packets/${packetId}`:`/api/tasks/${taskId}/agent-packet`,packetId?{}:{method:'POST'});
    resetAgent();packet=data;
    $('agent-code').hidden=data.packet.role!=='builder';
    $('agent-multifile').hidden=data.packet.role!=='builder';
    $('agent-code-options').hidden=data.packet.role!=='builder';$('agent-auto-test').checked=false;
    $('agent-title').textContent=`Instrukcja · zadanie #${taskId}`;
    $('agent-binding').textContent=`Wersja #${data.packet_id} · SHA-256: ${data.checksum} · Model nieuruchomiony`;
    $('agent-instructions').value=JSON.stringify(data.packet,null,2);
    $('agent-handoff').hidden=false;if(!$('agent-session').open)$('agent-session').showModal();
    message('Instrukcja zapisana. Dostarcz rzeczywisty wynik; nie uruchomiono żadnego modelu.');
  }
  async function openReview(taskId){
    const data=await request(`/api/tasks/${taskId}/review`);
    resetAgent();review={...data,task_id:taskId};
    $('agent-title').textContent=`Odbiór właściciela · zadanie #${taskId}`;
    $('agent-binding').textContent=`Próba #${data.id} · SHA-256: ${data.result_checksum} · Źródło zapisu: ${data.worker_id}`;
    $('agent-review-content').value=data.result_content;
    $('agent-review').hidden=false;if(!$('agent-session').open)$('agent-session').showModal();
    message('Sprawdź treść i dowody przed akceptacją. Import nie potwierdza wykonania testów.');
  }
  function renderDetail(data) {
    if(selected!==data.project_id){closePreview();$('check-report').hidden=true;$('check-findings').replaceChildren();resetInference();}
    selected=data.project_id;$('detail').hidden=false;markSelected();
    window.ProjectGuide?.render($('project-guide'),data,(action,taskId)=>{
      const targets={history:'inference-refresh',assignment:'delegate',details:'project-title',artifacts:'artifacts'};
      const target=$(action==='task'?`project-task-${taskId}`:targets[action]);
      if(target){if(!['BUTTON','A','INPUT'].includes(target.tagName))target.setAttribute('tabindex','-1');target.focus({preventScroll:true});target.scrollIntoView({block:'center'});}
    },bound=>{
      const project=data.project_id;
      act(async()=>{
        const prepared=await request(`/api/work-orders/${project}/prepare-next`,{method:'POST',body:JSON.stringify(bound)});
        await loadDetail(project);
        await openPacket(prepared.instruction.task_id,prepared.instruction.packet_id);
      });
    });
    $('project-title').textContent=`#${data.project_id} · ${data.brief.title}`;$('project-goal').textContent=data.brief.goal;
    $('project-meta').textContent=`Plan #${data.plan_id} · Bez automatycznego uruchomienia · Przydziel role, przygotuj instrukcję i odbierz konkretny wynik.`;
    const unitKey=unitKeys.get(data.brief.organization_unit_id)||'';
    const website=unitKey.startsWith('digital-experience.')||unitKey.startsWith('web-platforms.');
    $('starter').hidden=!website;$('starter-note').hidden=!website;
    $('criteria').replaceChildren(...data.brief.acceptance_criteria.map(c=>node('li',c)));
    $('tasks').replaceChildren();
    for(const t of data.tasks){
      // Stable anchors let the guide navigate without copying IDs or executing work.
      const card=node('article',undefined,'task');card.append(node('h3',`#${t.id} · ${t.title}`),node('p',labels[t.attempt_status]||labels[t.status]||t.status,'tag'),node('p',`Rola: ${t.assigned_role||'nieprzypisana'} · Zgoda: ${labels[t.approval_status]||t.approval_status}`,'muted'),node('p',t.completion_criterion),node('p',t.queued?'Zadanie oznaczone jako kolejkowane.':'Poza kolejką automatycznego wykonania.','muted'));
      card.id=`project-task-${t.id}`;card.tabIndex=-1;
      const d=t.delegation;
      if(d){
        for(const [key,label] of [['manager','Kierownik'],['worker','Wykonawca'],['reviewer','Kontroler']])card.append(node('p',`${label}: ${d[key]?.name||'brak'}`));
        card.append(node('p',d.predecessor_id?`Poprzedni etap: #${d.predecessor_id}`:'Pierwszy etap — brak poprzednika.','muted'));
        const blockers=node('ul');for(const reason of d.planning_blockers)blockers.append(node('li',reason));card.append(blockers);
        if(d.planning_ready)card.append(node('p','Zależności planu spełnione. To nie jest zgoda na wykonanie.','tag'));
        card.append(node('p',d.execution_hold,'muted'));
        const brief=node('details');brief.append(node('summary','Instrukcja dla agenta'),node('p',d.execution_brief));card.append(brief);
        if(d.planning_ready&&['pending','blocked'].includes(t.status)){
          const b=node('button','Przygotuj instrukcję');b.type='button';b.dataset.agentPacket=t.id;
          b.addEventListener('click',()=>act(()=>openPacket(t.id)));card.append(b);
        }
      }else card.append(node('p','Brak delegacji. Przygotuj zespół i przydziel agentów.','muted'));
      if(t.attempt_status==='awaiting_review'){
        const b=node('button','Odbierz wynik');b.type='button';b.dataset.agentReview=t.id;
        b.addEventListener('click',()=>act(()=>openReview(t.id)));card.append(b);
      }
      const graphics=node('a','Grafika do tego zadania →');graphics.href=`/os/media?task=${t.id}`;card.append(graphics);
      $('tasks').append(card);
    }
    $('artifacts').replaceChildren();
    if(!data.artifacts.length)$('artifacts').append(node('p','Brak zapisanych plików i dowodów.'));
    for(const a of data.artifacts){const card=node('article',undefined,'artifact');card.append(node('strong',`#${a.id} · ${a.type}`),node('p',a.description||a.name));
      if(a.type==='source_code'&&['organization-os.workspace.v1','organization-os.workspace-media.v1'].includes(a.name)){
        const b=node('button','Pobierz ZIP');b.type='button';b.addEventListener('click',()=>act(()=>download(a.task_id,a.id)));
        const inspect=node('button','Sprawdź pliki');inspect.type='button';inspect.dataset.checkPackage=a.id;inspect.addEventListener('click',()=>act(()=>inspectPackage(a.task_id,a.id)));
        const disk=node('button','Zapisz na dysku Linux');disk.type='button';disk.dataset.diskExport=a.id;disk.addEventListener('click',()=>act(()=>diskExport(a.task_id,a.id,true)));
        const verify=node('button','Sprawdź zapis na dysku');verify.type='button';verify.dataset.diskVerify=a.id;verify.addEventListener('click',()=>act(()=>diskExport(a.task_id,a.id,false)));
        const preview=node('button','Podgląd strony');preview.type='button';preview.dataset.previewPackage=a.id;preview.addEventListener('click',()=>act(()=>previewPackage(a.task_id,a.id)));
        const build=node('a','Testy aplikacji Python →');build.href=`/os/build?task=${a.task_id}&package=${a.id}`;
        const actions=node('div',undefined,'actions');actions.append(b);
        if(a.name!=='organization-os.workspace-media.v1')actions.append(preview,inspect);
        actions.append(disk,verify,build);card.append(actions);
      }
      if(a.type==='test_result'&&a.name==='organization-os.static-check.v1'){
        const open=node('button','Otwórz raport kontroli');open.type='button';open.dataset.checkReport=a.id;open.addEventListener('click',()=>act(()=>loadCheck(a.task_id,a.id)));card.append(open);
      }
      if(a.type==='plan'&&a.name==='organization-os.agent-packet.v1'){
        const b=node('button','Otwórz zapisaną instrukcję');b.type='button';b.addEventListener('click',()=>act(()=>openPacket(a.task_id,a.id)));card.append(b);
      }
      $('artifacts').append(card);
    }
  }
  async function loadDetail(id){const changed=selected!==id;const data=await request(`/api/work-orders/${id}`);renderDetail(data);if(changed)$('project-guide').scrollIntoView({block:'start'});message('Wczytano aktualny stan projektu.');}
  async function loadTeams(initialize=false){
    const data=await request('/api/agent-teams'+(initialize?'/initialize':''),initialize?{method:'POST'}:{});
    $('teams').replaceChildren(node('p',data.note));
    if(!data.teams.length)$('teams').append(node('p','Brak zespołów. Użyj „Przygotuj zespoły działów”.'));
    for(const team of data.teams){
      const box=node('details',undefined,'artifact');box.append(node('summary',`${team.department} · ${team.agents.length} ról${team.active?'':' · dział nieaktywny'}`));
      if(team.charter){box.append(node('p',team.charter.mission));const a=node('a','Zleć pracę temu działowi →');a.href='/os/work?unit='+encodeURIComponent(team.charter.target_key);box.append(a);}
      const list=node('ul');
      const states={not_started:'Brak wykonań Qwen',idle:'Brak oczekującego wykonania',queued:'Wykonanie oczekuje na uruchomienie',running:'Rejestr zgłasza pracę modelu — sprawdź historię',uncertain:'Niepewny stan — wymaga kontroli',awaiting_review:'Wynik oczekuje na odbiór',rejected:'Wynik odrzucony — wymaga poprawy',failed:'Nieudane wykonanie',stale:'Nieaktualna instrukcja'};
      for(const agent of team.agents){
        const item=node('li');item.append(node('p',`#${agent.id} · ${agent.role_title} · przełożony #${agent.supervisor_id} · ${agent.active?'dostępny do przydziału':'wyłączony'}`));
        item.append(node('p',`${states[agent.runtime_status]||'Brak danych o wykonaniu'} · przypisane zadania (łącznie): ${agent.assigned_tasks??0}`));
        if(agent.latest_run_states&&Object.keys(agent.latest_run_states).length)item.append(node('p','Ostatnie wykonania przypisanych zadań: '+Object.entries(agent.latest_run_states).map(([s,n])=>`${s}: ${n}`).join(', ')));
        if(agent.specialization){const p=agent.specialization,d=node('details');d.append(node('summary',p.specialization+' · instrukcja roli'),node('p',p.instruction),node('p',p.runtime_mode==='coordination_only'?'Rola koordynacji/kontroli — brak osobnej autonomicznej sesji. Odbiór wykonuje właściciel.':'Lokalny Qwen na żądanie dla gotowego zadania; bez narzędzi hosta.'));item.append(d);}
        list.append(item);
      }
      box.append(list);
      if(team.department_id){const area=node('section'),button=node('button','Pokaż zadania tego działu');button.type='button';button.addEventListener('click',()=>act(()=>loadTeamWork(team.department_id,area)));box.append(button,area);}
      $('teams').append(box);
    }
    message(initialize?`Przygotowano zespoły. Nowe role: ${data.created}. Nie uruchomiono żadnego modelu.`:'Wczytano strukturę zespołów.');
  }
  async function loadTeamWork(departmentId,area,before=null){
    const data=await request(`/api/agent-teams/${departmentId}/work`+(before?`?before=${before}`:''));
    if(!before)area.replaceChildren();
    if(!data.tasks.length&&!before)area.append(node('p','Nie przypisano jeszcze zadań. Użyj „Zleć pracę temu działowi”, zapisz zakres i przydziel zespół.'));
    for(const task of data.tasks){const row=node('article',undefined,'task');row.append(node('h3',`#${task.task_id} · ${task.title}`),node('p',`Status zadania: ${task.status} · wykonawca: ${task.worker?.name||'brak'} · kontroler: ${task.reviewer?.name||'brak'}`));
      if(task.run)row.append(node('p',`Ostatnia inferencja #${task.run.id}: ${task.run.state}. Odbiór to osobny stan zadania.`));
      for(const blocker of task.planning_blockers)row.append(node('p',blocker));
      const a=node('a','Otwórz projekt, instrukcję i wynik →');a.href='/os/work?project='+task.project_id;row.append(a);area.append(row);
    }
    area.querySelector('[data-more-work]')?.remove();
    if(data.next_cursor){const more=node('button','Starsze zadania');more.type='button';more.dataset.moreWork='';more.addEventListener('click',()=>act(()=>loadTeamWork(departmentId,area,data.next_cursor)));area.append(more);}
    message('Odczytano zadania działu. Nie uruchomiono modelu. Stan odświeżasz przyciskiem.');
  }
  $('initialize-teams').addEventListener('click',()=>act(()=>loadTeams(true)));
  $('agent-close').addEventListener('click',closeAgent);
  $('agent-session').addEventListener('close',()=>{if(!$('agent-session').open)resetAgent();});
  $('agent-download').addEventListener('click',()=>{
    if(!packet)return;
    const url=URL.createObjectURL(new Blob([JSON.stringify(packet.packet,null,2)],{type:'application/json'}));
    const a=node('a');a.href=url;a.download=`task-${packet.task_id}-instruction-${packet.packet_id}.json`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
  });
  $('agent-prompt').addEventListener('click',()=>{
    if(!packet)return;const bound=packet;
    act(async()=>{
      const prompt=await request(`/api/tasks/${bound.task_id}/agent-packets/${bound.packet_id}/prompt`);
      if(packet!==bound)return;
      $('agent-instructions').value=prompt.text;
      $('agent-instructions').focus();$('agent-instructions').select();
      $('agent-message').textContent='Prompt gotowy do skopiowania. Nie wysłano go do modelu. Wynik wklej poniżej i oddaj do odbioru; nie deklaruj niewykonanych testów.';
    });
  });
  function resetInference(){inferenceCursor=null;$('inference-more').hidden=true;$('inference-runs').replaceChildren();$('inference-state').textContent='Odśwież historię dla wybranego zakresu.';}
  async function loadInference(append=false){
    const scoped=$('inference-scope').value==='project';
    if(scoped&&!selected){resetInference();$('inference-state').textContent='Wybierz projekt z listy lub zmień zakres na „Wszystkie projekty”.';return;}
    const params=new URLSearchParams();
    if(scoped)params.set('project_id',selected);
    if($('inference-attention').checked)params.set('attention_only','true');
    if(append&&inferenceCursor)params.set('before',inferenceCursor);
    const data=await request('/api/local-inference?'+params);
    $('inference-state').textContent=`${scoped?'Projekt #'+selected:'Wszystkie projekty'} · Nierozstrzygnięte: ${data.attention_count??0}. `+(data.enabled?`${data.model} · jeden przebieg naraz · limit ${data.timeout_seconds} s · bez narzędzi. Wyniki wymagają odbioru.`:'Wykonanie modelu wyłączone w konfiguracji lub Emergency Stop.');
    if(!append)$('inference-runs').replaceChildren();
    const labels={queued:'Oczekuje na osobne uruchomienie',running:'Model generuje odpowiedź',awaiting_review:'Wynik przekazany do odbioru zadania',failed:'Przebieg nieudany — brak automatycznej ponownej próby',uncertain:'Niepewne zakończenie transportu — slot pozostaje zablokowany',stale:'Zmieniła się instrukcja lub polityka — wynik nieprzyjęty',cancelled:'Anulowano przed startem'};
    for(const run of data.runs){
      const card=node('article',undefined,'artifact');card.append(node('h3',`Qwen #${run.id} · zadanie #${run.task_id}`),node('p',labels[run.state]||run.state),node('p',`Model: ${run.model} · ${run.model_digest.slice(0,12)} · ${run.metrics.elapsed_seconds??'—'} s`));
      if(run.error_code)card.append(node('p',run.error_code));
      if(run.metrics.repair_validation)card.append(node('p',`Poprawka odrzucona: ${run.metrics.repair_validation}`));
      if(run.metrics.assembly){
        const assembly=run.metrics.assembly;
        card.append(node('p',`Poprawione pliki: ${(assembly.changed_files||[]).join(', ')}. Pozostałe pliki i testy zachowano.`));
        card.append(node('p',`Surowa odpowiedź Qwen: artefakt #${assembly.raw_artifact_id}; SHA-256 ${assembly.raw_response_checksum}.`));
      }
      if(run.metrics.package_id){const a=node('a',`Paczka #${run.metrics.package_id} → uruchom testy w izolacji`);a.href=`/os/build?task=${run.task_id}&package=${run.metrics.package_id}`;card.append(a);}
      if(run.metrics.retry_history?.length)card.append(node('p',`Zachowane nieudane próby: ${run.metrics.retry_history.length}.`));
      if(['failed','uncertain','running'].includes(run.state)){
        const retry=node('button','Przygotuj ponowienie po kontroli bezczynności');retry.type='button';
        retry.addEventListener('click',()=>act(async()=>{
          await request(`/api/local-inference/${run.id}/retry`,{method:'POST',body:JSON.stringify({request_id:crypto.randomUUID(),confirm:true})});
          await loadInference();message('Przebieg ponownie oczekuje. Model uruchomisz osobnym przyciskiem; historia błędu jest zachowana.');
        }));card.append(retry);
      }
      if(run.result_content){const d=node('details');d.append(node('summary',run.metrics.assembly?'Źródła po złożeniu poprawki — wymagają odbioru':'Wynik modelu — sprawdź w zadaniu przed akceptacją'),node('p',run.result_content));card.append(d);}
      if(run.state==='queued'){
        const go=node('button','Uruchom ten przebieg Qwen');go.type='button';go.addEventListener('click',()=>act(async()=>{
          message('Trwa generowanie, maksymalnie około 3 minut. Zamknięcie strony nie jest potwierdzeniem anulowania.');
          await request(`/api/local-inference/${run.id}/run`,{method:'POST'},false,195000);await loadInference();if(selected)await loadDetail(selected);
        }));
        const cancel=node('button','Anuluj oczekujący wpis');cancel.type='button';cancel.addEventListener('click',()=>act(async()=>{await request(`/api/local-inference/${run.id}/cancel`,{method:'POST'});await loadInference();}));card.append(go,cancel);
      }
      $('inference-runs').append(card);
    }
    if(!data.runs.length)$('inference-runs').append(node('p','Brak wykonań. W zadaniu przygotuj instrukcję, następnie wybierz „Uruchom lokalny Qwen”.'));
    inferenceCursor=data.next_cursor;$('inference-more').hidden=!inferenceCursor;
  }
  $('inference-refresh').addEventListener('click',()=>act(loadInference));
  $('inference-more').addEventListener('click',()=>act(()=>loadInference(true)));
  $('inference-scope').addEventListener('change',resetInference);
  $('inference-attention').addEventListener('change',resetInference);
  function generate(outputProfile){
    if(!packet)return;const bound=packet,project=selected,autoTest=['python-web-v1','python-web-multifile-v1'].includes(outputProfile)&&$('agent-auto-test').checked;
    act(async()=>{
      const run=await request('/api/local-inference',{method:'POST',body:JSON.stringify({request_id:crypto.randomUUID(),task_id:bound.task_id,packet_id:bound.packet_id,packet_checksum:bound.checksum,output_profile:outputProfile})});
      message('Uruchamiam rzeczywisty lokalny model. Limit około 3 minut. Nie uruchamiam wygenerowanego kodu.');
      const result=run.state==='queued'?await request(`/api/local-inference/${run.id}/run`,{method:'POST'},false,195000):run;
      let tested=null;
      if(autoTest&&result.state==='awaiting_review'&&result.metrics?.package_id){
        message('Qwen zapisał pliki. Uruchamiam zatwierdzony profil kontenera; bez sieci i GPU.');
        tested=await request('/api/package-runs',{method:'POST',body:JSON.stringify({request_id:crypto.randomUUID(),task_id:result.task_id,package_id:result.metrics.package_id,package_checksum:result.metrics.package_checksum,confirm_execution:true})},false,95000);
      }
      closeAgent();await loadInference();if(project)await loadDetail(project);
      message(result.state==='awaiting_review'?(outputProfile==='python-web-multifile-v1'?'Qwen zapisał wersję modułową. W „Budowa i testy” sprawdź testy, podgląd i odbiór konkretnej paczki. Sam zapis nie kończy zadania.':'Qwen dostarczył wynik. Otwórz „Odbierz wynik” przy zadaniu i sprawdź jego treść oraz dowody.'):`Stan wykonania: ${result.state}. Sprawdź historię Qwen; niczego automatycznie nie ponawiano.`);
      if(tested)message(`Qwen zapisał pliki, wykonanie testów #${tested.id}: ${tested.state}. Raport i ZIP znajdziesz w „Budowa i testy”. Odbiór pozostaje do wykonania.`);
    });
  }
  $('agent-infer').addEventListener('click',()=>generate('text'));
  $('agent-code').addEventListener('click',()=>generate('python-web-v1'));
  $('agent-multifile').addEventListener('click',()=>generate('python-web-multifile-v1'));
  async function loadLocalQueue(append=false){
    const data=await request('/api/local-model-queue'+(append&&queueCursor?`?before=${queueCursor}`:''));
    const states={queued:'Oczekuje na symulację',running:'Trwa próba',simulation_complete:'Symulacja zakończona — zadanie niewykonane',failed:'Próba nieudana',stale:'Instrukcja nieaktualna',cancelled:'Anulowana'};
    $('local-queue-state').textContent=`Inferencja wyłączona. ${data.reason} Limit równoległości: ${data.concurrency}.`;
    if(!append)$('local-queue-jobs').replaceChildren();
    for(const job of data.jobs){
      const card=node('article',undefined,'artifact');card.append(node('h3',`Próba #${job.id} · zadanie #${job.task_id}`),node('p',states[job.state]||job.state),node('p',`Instrukcja #${job.packet_id} · próby: ${job.attempts}`));
      if(job.error_code)card.append(node('p',`Powód: ${job.error_code}. Bez automatycznego ponowienia.`));
      if(job.result_content){const result=node('details');result.append(node('summary','Odpowiedź symulacyjna — nie wynik pracy modelu'),node('p',job.result_content));card.append(result);}
      if(job.state==='queued'){const cancel=node('button','Anuluj próbę');cancel.type='button';cancel.addEventListener('click',()=>act(async()=>{await request(`/api/local-model-queue/${job.id}/cancel`,{method:'POST'});await loadLocalQueue();}));card.append(cancel);}
      $('local-queue-jobs').append(card);
    }
    if(!data.jobs.length&&!append)$('local-queue-jobs').append(node('p','Kolejka pusta. Przygotuj instrukcję gotowego zadania, a następnie wybierz „Dodaj instrukcję do kolejki próbnej”.'));
    queueCursor=data.next_cursor;$('local-queue-more').hidden=!queueCursor;
  }
  $('local-queue-refresh').addEventListener('click',()=>act(()=>loadLocalQueue()));
  $('local-queue-more').addEventListener('click',()=>act(()=>loadLocalQueue(true)));
  $('local-queue-next').addEventListener('click',()=>act(async()=>{
    const data=await request('/api/local-model-queue/simulate-next',{method:'POST'});await loadLocalQueue();
    message(data.job?'Próba zapisana w kolejce. Nie uruchomiono modelu ani nie zmieniono zadania.':'Brak oczekujących pozycji.');
  }));
  $('agent-queue').addEventListener('click',()=>{
    if(!packet)return;const bound=packet;
    if(!bound.queueRequestId)bound.queueRequestId=crypto.randomUUID();
    act(async()=>{
      const job=await request('/api/local-model-queue',{method:'POST',body:JSON.stringify({request_id:bound.queueRequestId,task_id:bound.task_id,packet_id:bound.packet_id,packet_checksum:bound.checksum})});
      await loadLocalQueue();message(`Pozycja próbna #${job.id} zapisana. Zamknij instrukcję i wybierz „Symuluj jedną oczekującą pozycję”. Model pozostaje wyłączony.`);
    });
  });
  $('agent-result-form').addEventListener('submit',e=>{
    e.preventDefault();if(!packet)return;
    const bound=packet,project=selected;
    const body={packet_id:bound.packet_id,packet_checksum:bound.checksum,result_content:$('agent-result').value,source_note:$('agent-source').value};
    act(async()=>{
      await request(`/api/tasks/${bound.task_id}/agent-results`,{method:'POST',body:JSON.stringify(body)});
      closeAgent();await loadDetail(project);message('Wynik zapisany do odbioru. Kliknij „Odbierz wynik” w zadaniu i sprawdź go.');
    });
  });
  $('agent-review-form').addEventListener('submit',e=>{
    e.preventDefault();if(!review||!e.submitter)return;
    const bound=review,project=selected;
    const body={attempt_id:bound.id,result_checksum:bound.result_checksum,accepted:e.submitter.value==='accept',reason:$('agent-review-reason').value,evidence:$('agent-review-evidence').value.split('\n').map(x=>x.trim()).filter(Boolean)};
    act(async()=>{
      await request(`/api/tasks/${bound.task_id}/review`,{method:'POST',body:JSON.stringify(body)});
      closeAgent();await loadDetail(project);message(body.accepted?'Odebrano konkretną wersję wyniku. Następny etap wymaga osobnego działania.':'Wynik odrzucono. Przygotuj nową instrukcję z uwagami i dostarcz poprawkę.');
    });
  });
  $('refresh-teams').addEventListener('click',()=>act(()=>loadTeams(false)));
  $('delegate').addEventListener('click',()=>act(async()=>{
    if(!selected)return;
    const data=await request(`/api/work-orders/${selected}/delegate`,{method:'POST'});
    renderDetail(data);message('Zapisano kierowników, wykonawców, kontrolerów i kolejność etapów. Wykonanie pozostaje wstrzymane.');
  }));
  $('access').addEventListener('submit',e=>{e.preventDefault();act(async()=>{
    token=$('token').value.trim();const data=await request('/api/work-orders/options');
    unitKeys=new Map(data.units.map(u=>[u.id,u.key]));
    $('unit').replaceChildren();for(const u of data.units){const o=node('option',`${u.key||u.id} · ${u.name}`);o.value=u.id;$('unit').append(o);}
    const requested=new URLSearchParams(location.search).get('unit');
    const preferred=data.units.find(u=>u.key===(requested||'digital-experience.websites'));if(preferred)$('unit').value=preferred.id;
    $('workspace').hidden=false;await loadOrders();
    if(new URLSearchParams(location.search).get('teams')==='1'){await loadTeams();$('teams-title').scrollIntoView({block:'start'});}
    const project=new URLSearchParams(location.search).get('project');
    if(project){if(!/^[1-9][0-9]{0,9}$/.test(project))throw Error('Nieprawidłowy numer projektu w adresie.');await loadDetail(Number(project));message(`Otworzono projekt #${project}. Niczego automatycznie nie uruchomiono.`);return;}
    message(requested&&!preferred?'Wybrany dział nie jest dostępny. Wybierz aktualną gałąź w formularzu.':requested?`Wybrano: ${preferred.name}. Uzupełnij cel, zakres i kryteria. Niczego jeszcze nie utworzono.`:'Połączono. Zlecenia i pliki zapisują się w istniejącej bazie.');
  });});
  $('intake').addEventListener('submit',e=>{e.preventDefault();const f=new FormData($('intake'));act(async()=>{
    const brief={title:f.get('title').trim(),goal:f.get('goal').trim(),audience:f.get('audience').trim(),constraints:f.get('constraints').trim(),organization_unit_id:Number(f.get('organization_unit_id')),acceptance_criteria:f.get('criteria').split('\n').map(x=>x.trim()).filter(Boolean)};
    const signature=JSON.stringify(brief);
    if(pending&&pending.signature!==signature)throw new Error('Po niepewnym zapisie najpierw sprawdź listę. Aby zmienić zakres, wybierz „Rozpocznij nowy formularz”.');
    if(!pending)pending={signature,id:crypto.randomUUID()};
    const data=await request('/api/work-orders',{method:'POST',body:JSON.stringify({...brief,request_id:pending.id})});
    renderDetail(data);await loadOrders();message(`Zapisano projekt #${data.project_id} i cztery zadania. Niczego nie uruchomiono. Powtórne wysłanie tego formularza nie tworzy duplikatu.`);
  });});
  $('new-request').addEventListener('click',()=>{if(pending&&!confirm('Rozpocząć nowe zlecenie? Jeśli poprzedni zapis był niepewny, najpierw sprawdź listę.'))return;pending=null;$('intake').reset();message('Nowy formularz. Dotychczasowe projekty pozostają zapisane.');});
  $('starter').addEventListener('click',()=>act(async()=>{if(!selected)return;const id=selected;await request(`/api/work-orders/${id}/website-starter`,{method:'POST'});await loadDetail(id);message('Szkielet HTML/CSS zapisany. Pobierz ZIP poniżej. To szablon, nie produkt odebrany ani wynik AI.');}));
  $('refresh').addEventListener('click',()=>act(async()=>{await loadOrders();if(selected)await loadDetail(selected);else message('Odświeżono listę.');}));
  $('more').addEventListener('click',()=>act(()=>loadOrders(true)));
  $('logout').addEventListener('click',()=>{clear();message('Dostęp i dane formularza wyczyszczone z karty. Projekty pozostają w bazie.');});
  $('preview-close').addEventListener('click',closePreview);
  $('preview').addEventListener('close',()=>{if(!$('preview').open)resetPreview();});
  $('preview-wide').addEventListener('click',()=>previewSize(false));
  $('preview-phone').addEventListener('click',()=>previewSize(true));
  window.addEventListener('pagehide',clear);
  setInterval(async()=>{if($('workspace').hidden||(!token&&!window.OwnerSession?.active)||busy||polling||document.hidden||$('preview').open||$('agent-session').open||document.activeElement?.closest('#intake,#detail,#orders,#project-guide'))return;
    polling=true;const ticket=epoch;try{await loadOrders();if(selected)renderDetail(await request(`/api/work-orders/${selected}`));}catch(e){if(ticket===epoch){if([401,403].includes(e.status))clear();message('Nie udało się odświeżyć danych. Widoczny stan może być nieaktualny.',true);}}finally{if(ticket===epoch)polling=false;}
  },30000);
})();
