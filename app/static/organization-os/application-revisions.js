(()=>{'use strict';window.createApplicationRevisions=({request,act,message,refresh})=>{
  const $=id=>document.getElementById(id);let binding=null,pending=null;
  const text=(tag,value)=>{const e=document.createElement(tag);e.textContent=value;return e;};
  function clear(){binding=pending=null;$('revision-form').reset();$('revision-editor').hidden=true;$('revision-history').replaceChildren();}
  function open(run){binding={task_id:run.task_id,package_id:run.package_id,package_checksum:run.package_checksum};pending=null;
    $('revision-form').reset();$('revision-binding').textContent=`Zadanie #${run.task_id} · wersja źródeł #${run.package_id} · ${run.package_checksum}`;
    $('revision-editor').hidden=false;$('revision-editor').scrollIntoView({behavior:'smooth',block:'start'});$('revision-description').focus();}
  async function load(){const data=await request('/api/application-revisions');$('revision-history').replaceChildren();
    for(const row of data.revisions){const card=text('article','');card.className='artifact';
      card.append(text('h3',`Poprawka #${row.id} · paczka bazowa #${row.package_id}`),text('p',row.description),
        text('p','Oczekiwany rezultat: '+row.expected_result),text('p',`Qwen: ${row.state} · testy: ${row.test_state||'nie uruchomiono'}`));
      if(row.error_code)card.append(text('p','Przyczyna: '+row.error_code));
      if(row.new_package_id){const a=text('a',`Nowa wersja #${row.new_package_id} — testy i podgląd`);a.href=`/os/build?task=${row.task_id}&package=${row.new_package_id}`;card.append(a);}
      if(['queued','awaiting_review'].includes(row.state)){const b=text('button',row.state==='queued'?'Uruchom poprawkę Qwen':'Sprawdź / dokończ testy tej poprawki');b.type='button';b.onclick=()=>act(()=>execute(row.id));card.append(b);}
      if(['failed','uncertain'].includes(row.state))card.append(text('p','Nie ponowiono modelu automatycznie. Sprawdź wykonanie w Centrum realizacji.'));
      $('revision-history').append(card);
    }
    if(!data.revisions.length)$('revision-history').append(text('p','Nie zgłoszono jeszcze poprawek.'));
  }
  async function execute(id){message(`Qwen pracuje nad poprawką #${id}. Wynik i testy zostaną zapisane; zamknięcie karty nie anuluje pracy.`);
    const row=await request(`/api/application-revisions/${id}/run`,{method:'POST'});await load();await refresh();
    message(`Poprawka #${id}: ${row.state}; testy: ${row.test_state||'nie uruchomiono'}. Nowa paczka: ${row.new_package_id||'brak'}. Wymagany ponowny odbiór.`);
  }
  $('refresh-revisions').onclick=()=>act(load);$('cancel-revision').onclick=()=>{$('revision-editor').hidden=true;};
  $('revision-form').onsubmit=e=>{e.preventDefault();if(!binding)return;act(async()=>{
    const data={...binding,description:$('revision-description').value.trim(),expected_result:$('revision-expected').value.trim(),
      evidence:$('revision-evidence').value.split('\n').map(x=>x.trim()).filter(Boolean),auto_test:$('revision-test').checked,confirm_revision:true};
    const key=JSON.stringify(data);if(!pending||pending.key!==key)pending={key,body:{...data,request_id:crypto.randomUUID()}};
    const row=await request('/api/application-revisions',{method:'POST',body:JSON.stringify(pending.body)});
    message(`Zapisano poprawkę #${row.id}. Poprzednia paczka pozostaje w historii.`);await execute(row.id);
  });};
  return {open,clear};
};})();
