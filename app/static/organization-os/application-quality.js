(()=>{'use strict';window.createApplicationQuality=({request,act,message,refresh})=>{
  const $=id=>document.getElementById(id),pending=new Map();let active=null;
  const node=(tag,value)=>{const e=document.createElement(tag);e.textContent=value;return e;};
  const labels={pending:'Zapisany / w toku',passed:'Testy zaliczone',needs_attention:'Wymaga diagnozy',limit_reached:'Limit prób wyczerpany',stopped:'Zatrzymany',stop_requested:'Zatrzymanie zlecone'};
  function clear(){pending.clear();active=null;$('quality-history').replaceChildren();$('quality-stop').hidden=true;}
  async function load(){const data=await request('/api/application-quality');$('quality-history').replaceChildren();
    for(const row of data.cycles){const card=node('article','');card.className='artifact';
      card.append(node('h3',`Cykl #${row.id} · zadanie #${row.task_id} · ${labels[row.state]||row.state}`),node('p',row.message));
      const steps=node('ol','');for(const s of row.steps){const step=node('li',`${({repair:'Naprawa Qwen',test:'Test w izolacji',acceptance:'Przykłady wymagań HTTP'})[s.kind]||s.kind} #${s.id}: ${s.state} · paczka ${s.package_id||'jeszcze nie utworzona'}`);if(s.kind==='acceptance'){const cases=node('ul','');for(const c of s.cases)cases.append(node('li',`${c.passed?'✓':'✗'} ${c.title} · ${c.path} · oczekiwano ${c.json_field?JSON.stringify(c.expected):c.expected_status}, otrzymano ${JSON.stringify(c.observed)} (${c.reason})`));step.append(cases);}steps.append(step);}card.append(steps);
      if(row.final_package_id){const a=node('a',`Wersja wynikowa #${row.final_package_id} — podgląd i pobranie`);a.href=`/os/build?task=${row.task_id}&package=${row.final_package_id}`;card.append(a);}
      if(['pending','stop_requested'].includes(row.state)){
        const resume=node('button','Uruchom / wznów zapisany cykl');resume.type='button';resume.onclick=()=>act(()=>run(row.id));
        const stop=node('button','Zatrzymaj po bieżącej operacji');stop.type='button';stop.onclick=()=>stopCycle(row.id);card.append(resume,stop);
      }
      $('quality-history').append(card);
    }
    if(!data.cycles.length)$('quality-history').append(node('p','Nie rozpoczęto cykli automatycznej kontroli.'));
  }
  async function stopCycle(id){try{await request(`/api/application-quality/${id}/stop`,{method:'POST'});message('Zlecono zatrzymanie po bieżącym teście lub inferencji. Nie przerywamy kontenera bez sprzątania.');await load();}catch(e){message(e.message);}}
  async function run(id){active=id;$('quality-stop').hidden=false;message(`Cykl #${id}: system sam testuje, naprawia i ponawia testy. Może to potrwać kilka minut.`);
    try{const row=await request(`/api/application-quality/${id}/run`,{method:'POST'});await load();await refresh();message(`${labels[row.state]||row.state}: ${row.message}`);}
    finally{active=null;$('quality-stop').hidden=true;}
  }
  function start(binding,plan=null){
    if(plan&&!plan.execution_enabled){message('Wykonanie nowych przypadków HTTP jest wyłączone. Plan pozostaje zapisany.');return;}
    if(!window.confirm('Uruchomić testy i automatycznie naprawiać wykryte błędy przez Qwen? Maksymalnie 2 poprawki, 3 zestawy testów, 15 minut. '+(plan?`Dodatkowo ${plan.cases.length} niezmiennych przykładów HTTP po każdym zaliczonym zestawie. Wybrany plan staje się warunkiem odbioru i wydania. `:'')+'Każda poprawka zachowuje poprzednie pliki. Bez publikacji i automatycznego odbioru biznesowego.'))return;
    act(async()=>{const key=`${binding.task_id}:${binding.package_id}:${binding.package_checksum}:${plan?.id||''}:${plan?.checksum||''}`;
      if(!pending.has(key))pending.set(key,{request_id:crypto.randomUUID(),task_id:binding.task_id,package_id:binding.package_id,package_checksum:binding.package_checksum,max_repairs:2,confirm_automatic_repairs:true,...(plan?{acceptance_plan_id:plan.id,acceptance_plan_checksum:plan.checksum}:{})});
      const row=await request('/api/application-quality',{method:'POST',body:JSON.stringify(pending.get(key))});await run(row.id);
    });
  }
  $('refresh-quality').onclick=()=>load().catch(e=>message(e.message));
  $('quality-stop').onclick=()=>{if(active!==null)stopCycle(active);};
  return {start,clear};
};})();
