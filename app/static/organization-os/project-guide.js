/* Read-only project navigator. No network, model calls or status mutations. */
(function (root) {
  'use strict';
  const labels = {accepted:'Odebrano', assignment:'Przydział', instruction:'Instrukcja',
    blocked:'Blokada', review:'Do odbioru', repair:'Do poprawy', execution_hold:'Sprawdź wykonanie',
    cancelled:'Anulowano', unverified:'Brak dowodu', inspect:'Do sprawdzenia', inconsistent:'Niespójne dane'};
  const actions = {task:'Otwórz bieżący etap', history:'Przejdź do historii wykonań',
    assignment:'Przejdź do przydziału agentów', details:'Sprawdź szczegóły', artifacts:'Przejdź do plików i testów'};
  function render(host, data, navigate, prepare) {
    const doc = host.ownerDocument;
    const element = (tag, text) => {const el = doc.createElement(tag); if(text !== undefined)el.textContent=text;return el;};
    host.replaceChildren();host.hidden=false;
    const heading=element('h2', `Twój następny krok · ${data.brief?.title || 'Projekt'}`);
    heading.id='project-guide-title';host.append(heading);
    const guide=data.guidance;
    if(guide?.version!==1 || !Array.isArray(guide.stages) || !guide.current){
      host.append(element('p','Nie udało się ustalić etapu. Odśwież projekt lub sprawdź szczegóły poniżej.'));return;
    }
    const validIds=new Set((data.tasks || []).map(t=>t.id).filter(Number.isSafeInteger));
    function button(text, action, taskId) {
      const b=element('button',text);b.type='button';
      b.addEventListener('click',()=>navigate(action,taskId));return b;
    }
    const current=guide.current;
    host.append(element('p',`${guide.accepted_stages} z ${guide.total_stages} etapów odebranych. To nie jest procent gotowości wydania.`));
    const timeline=element('ol');timeline.className='project-stages';
    for(const stage of guide.stages){
      const item=element('li');item.dataset.state=stage.state;
      if(stage.task_id===current.task_id)item.setAttribute('aria-current','step');
      item.append(element('strong',labels[stage.state] || 'Do sprawdzenia'));
      if(validIds.has(stage.task_id))item.append(button(stage.title,'task',stage.task_id));
      else item.append(element('span',stage.title));
      timeline.append(item);
    }
    host.append(timeline,element('h3',current.title),element('p',current.reason));
    const taskRequired=current.action==='task';
    if(actions[current.action] && (!taskRequired || validIds.has(current.task_id)))
      host.append(button(actions[current.action],current.action,current.task_id));
    const coordination=data.coordination;
    if(typeof prepare==='function' && coordination?.can_prepare===true
       && coordination.task_id===current.task_id && validIds.has(coordination.task_id)
       && /^[0-9a-f]{64}$/.test(coordination.revision)){
      const b=element('button','Przygotuj bieżący etap — bez uruchamiania modelu');b.type='button';
      b.addEventListener('click',()=>prepare({task_id:coordination.task_id,expected_revision:coordination.revision}));
      host.append(b);
    }
    const note=element('p','Nawigacja prowadzi do kontrolek; „Przygotuj bieżący etap” zapisuje lub otwiera instrukcję tego etapu. Nie uruchamiają Qwena, testów ani publikacji. Dostępność zasobów, w tym zakończenie wynajmu Vast.ai, wymaga osobnego potwierdzenia.');
    note.className='muted';host.append(note);
  }
  root.ProjectGuide={render};
  if(typeof module==='object' && module.exports)module.exports={render};
})(typeof window==='object'?window:globalThis);
