(() => {
  'use strict';
  const $=id=>document.getElementById('history-'+id),node=(tag,text)=>{const n=document.createElement(tag);if(text!==undefined)n.textContent=text;return n;};
  let token='',epoch=0,busy=false,controller=new AbortController(),cursor=null,selected=null,versions=null,events=null;
  let feedbackCursor=null;
  $('detail').append($('feedback').closest('section'));
  const names={created:'Utworzono dostęp',updated:'Opublikowano zmiany',revoked:'Cofnięto dostęp',baseline:'Zachowany stan sprzed aktualizacji',open_project:'Otwarcie projektu',view_workflow:'Otwarcie workflow',view_stage:'Otwarcie etapu',view_materials:'Otwarcie materiałów',view_reviews:'Otwarcie listy odbiorów'};
  const date=value=>value?new Date(value).toLocaleString('pl-PL'):'Brak zarejestrowanej aktywności';
  function say(t){$('message').textContent=t;}
  function clear(){epoch++;controller.abort();controller=new AbortController();token='';busy=false;cursor=selected=versions=events=feedbackCursor=null;$('access').reset();$('workspace').hidden=true;$('detail').hidden=true;for(const id of ['projects','versions','events','feedback'])$(id).replaceChildren();$('preview').href='/os/client-preview';$('title').textContent='';$('meta').textContent='';document.querySelectorAll('button,input,textarea').forEach(n=>n.disabled=false);}
  async function request(path,options={}){const ticket=epoch,local=new AbortController(),parent=controller.signal,abort=()=>local.abort();parent.addEventListener('abort',abort,{once:true});const timer=setTimeout(abort,10000);
    try{const r=await (window.OwnerSession?.fetch||fetch)(path,{...options,headers:{Authorization:`Bearer ${token}`,...(options.body?{'Content-Type':'application/json'}:{})},cache:'no-store',credentials:'omit',redirect:'error',signal:local.signal});if(ticket!==epoch)throw Error('Sesja zamknięta.');if(!r.ok){if([401,403].includes(r.status)){clear();say('Wymagany poprawny token właściciela.');}throw Error(`Operacja nie została potwierdzona (HTTP ${r.status}). Odśwież historię przed ponowieniem.`);}const data=await r.json();if(ticket!==epoch)throw Error('Sesja zamknięta.');return data;}finally{clearTimeout(timer);parent.removeEventListener('abort',abort);}}
  async function act(fn){if(busy)return;busy=true;const ticket=epoch;const controls=[...document.querySelectorAll('button,input')].filter(n=>n.id!=='history-logout'&&!n.closest('.app-navigation'));controls.forEach(n=>n.disabled=true);try{await fn();}catch(e){if(ticket===epoch)say(e.name==='AbortError'?'Dane nie zostały odświeżone. Spróbuj ponownie.':e.message);}finally{if(ticket===epoch){busy=false;controls.forEach(n=>n.disabled=false);}}}
  async function list(append=false){const data=await request('/api/client-history'+(append&&cursor?`?before=${cursor}`:''));if(!append)$('projects').replaceChildren();for(const s of data.shares){const b=node('button',`Projekt #${s.project_id} · ${s.title} · dostęp #${s.id} · ${s.revoked?'cofnięty':s.expired?'wygasły':'aktywny'} · ${s.progress}% · ${date(s.last_activity_at)}`);b.type='button';b.className='order';b.dataset.shareId=s.id;b.addEventListener('click',()=>act(()=>detail(s.id)));$('projects').append(b);}if(!data.shares.length&&!append)$('projects').append(node('p','Brak udostępnionych projektów. Utwórz publikację w menu właściciela; samo zlecenie nie udostępnia danych klientowi.'));cursor=data.next_cursor;$('more').hidden=!cursor;}
  async function detail(id,mode=null){const query=mode==='versions'?`?before_revision=${versions}`:mode==='events'?`?before_activity=${events}`:'';const data=await request(`/api/client-shares/${id}/history${query}`);selected=id;$('detail').hidden=false;$('title').textContent=`${data.project.title} · dostęp #${id}`;$('meta').textContent=`Projekt #${data.share.project_id} · ${data.share.revoked?'Dostęp cofnięty':data.share.expired?'Dostęp wygasł':'Dostęp aktywny'} · Ostatnia publikacja: ${date(data.share.updated_at)}`;
    $('preview').href=`/os/client-preview?share=${id}`;
    if(!mode){$('feedback').replaceChildren();$('more-feedback').hidden=true;await feedback(id);}
    if(mode!=='events'){if(!mode)$('versions').replaceChildren();for(const r of data.revisions){const d=node('details');d.className='artifact';d.append(node('summary',`#${r.id} · ${names[r.kind]||r.kind} · ${date(r.at)} · ${r.project.progress}%`),node('p',r.project.summary));for(const s of r.project.milestones){const p=node('p',`${s.title} (${s.status})\n${s.description||''}\n${s.deliverable||''}\n${(s.acceptance_criteria||[]).join('\n')}\n${s.review_note||''}`);d.append(p);}$('versions').append(d);}if(!data.revisions.length&&!mode)$('versions').append(node('p','Brak zapisanych wcześniejszych wersji.'));versions=data.next_revision;$('more-versions').hidden=!versions;}
    if(mode!=='versions'){if(!mode)$('events').replaceChildren();for(const a of data.activities){const p=node('p',`${date(a.at)} · ${names[a.kind]||a.kind}${a.stage_title?' · '+a.stage_title:''}`);p.className='artifact';$('events').append(p);}if(!data.activities.length&&!mode)$('events').append(node('p','Brak zarejestrowanych zdarzeń dla tego kodu.'));events=data.next_activity;$('more-events').hidden=!events;}
    say('Wczytano historię. Dane dotyczą opublikowanego zakresu i odbiorcy kodu, nie całej aktywności człowieka.');}
  async function feedback(id,append=false){
    const data=await request(`/api/client-shares/${id}/feedback`+(append&&feedbackCursor?`?before=${feedbackCursor}`:''));
    if(!append)$('feedback').replaceChildren();
    for(const r of data.feedback){
      const card=node('article');card.className='artifact';card.append(node('h4',r.stage_title),node('p',`${r.decision==='accepted'?'Akceptacja':'Prośba o poprawki'} · ${date(r.created_at)}`),node('p',r.comment));
      const snapshot=node('details');snapshot.append(node('summary','Wersja, której dotyczy decyzja'),node('p',`SHA-256: ${r.publication_checksum}`),node('p',r.stage_snapshot.deliverable||'Nie opublikowano rezultatu.'));card.append(snapshot);
      if(r.owner_reply)card.append(node('p',`Odpowiedź wykonawcy (${date(r.acknowledged_at)}): ${r.owner_reply}`));
      else {
        const form=node('form'),label=node('label','Odpowiedź dla klienta (zostanie zapisana w historii)'),input=node('textarea'),button=node('button','Potwierdź obsługę i odpowiedz');input.required=true;input.minLength=3;input.maxLength=2000;input.rows=3;label.append(input);button.type='submit';form.append(label,button);card.append(form);
        form.addEventListener('submit',e=>{e.preventDefault();const reply=input.value.trim();if(reply.length<3){say('Wpisz co najmniej 3 znaki odpowiedzi.');return;}act(async()=>{await request(`/api/client-feedback/${r.id}/acknowledge`,{method:'POST',body:JSON.stringify({reply})});await feedback(id);say('Odpowiedź zapisana i dostępna klientowi. Status zadań nie został zmieniony.');});});
      }
      $('feedback').append(card);
    }
    if(!data.feedback.length&&!append)$('feedback').append(node('p','Brak decyzji klientów dla tego udostępnienia.'));
    feedbackCursor=data.next_cursor;$('more-feedback').hidden=!feedbackCursor;
  }
  $('access').addEventListener('submit',e=>{e.preventDefault();const value=$('token').value.trim();clear();token=value;act(async()=>{await list();$('workspace').hidden=false;say('Połączono z historią właściciela.');});});
  $('logout').addEventListener('click',()=>{clear();say('Dostęp i historia wyczyszczone z tej karty.');});
  $('refresh').addEventListener('click',()=>act(async()=>{await list();if(selected)await detail(selected);}));
  $('more').addEventListener('click',()=>act(()=>list(true)));
  $('more-versions').addEventListener('click',()=>act(()=>detail(selected,'versions')));
  $('more-events').addEventListener('click',()=>act(()=>detail(selected,'events')));
  $('more-feedback').addEventListener('click',()=>act(()=>feedback(selected,true)));
  window.addEventListener('pagehide',clear);
})();
