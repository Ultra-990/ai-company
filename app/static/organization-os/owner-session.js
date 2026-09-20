/* HttpOnly session adapter, explicitly used only by internal owner panels. */
(() => {
  'use strict';
  let session = null, expiryTimer;
  const endpoint = '/api/owner-session';
  const channel = typeof BroadcastChannel === 'function' ? new BroadcastChannel('owner-session-events') : null;
  const make = (tag, text) => { const n=document.createElement(tag); if(text)n.textContent=text; return n; };
  async function request(path, options={}) {
    if(typeof path!=='string'||!path.startsWith('/api/')||path.startsWith('/api/client/'))throw Error('Niedozwolony adres panelu właściciela.');
    if(!session)return fetch(path,options);
    const headers=new Headers(options.headers);
    if(session){headers.delete('Authorization');headers.set('X-Owner-CSRF',session.csrf);}
    headers.set('X-Owner-Origin',location.origin);
    const response=await fetch(path,{...options,headers,credentials:session?'same-origin':'omit',redirect:'error',cache:'no-store'});
    if(session&&response.status===401){session=null;location.reload();}
    return response;
  }
  window.OwnerSession={fetch:request,get active(){return !!session;}};
  async function boot(){
    const nav=document.querySelector('.app-navigation');if(!nav)return;
    const button=make('button','Zaloguj właściciela');button.type='button';button.id='owner-session-button';button.hidden=true;
    const state=make('span','');state.id='owner-session-state';state.setAttribute('role','status');nav.append(state,button);
    const dialog=make('dialog');dialog.id='owner-session-dialog';dialog.setAttribute('aria-labelledby','owner-session-title');
    const title=make('h2','Jedno logowanie właściciela');title.id='owner-session-title';
    const info=make('p','Wpisz token raz. Sesja działa między panelami do 8 godzin lub do wylogowania/restartu serwera. Nie jest kodem klienta.');
    const form=make('form'),label=make('label','Token właściciela'),input=make('input');
    input.id='owner-session-token';input.type='password';input.required=true;input.maxLength=4096;input.autocomplete='off';label.htmlFor=input.id;
    const submit=make('button','Zaloguj'),cancel=make('button','Anuluj');cancel.type='button';
    const message=make('p');message.id='owner-session-message';message.setAttribute('role','status');
    form.append(label,input,submit,cancel);dialog.append(title,info,form,message);document.body.append(dialog);
    cancel.onclick=()=>dialog.close();dialog.addEventListener('close',()=>{input.value='';message.textContent='';});
    const logout=async()=>{
      button.disabled=true;
      try{
        const r=await request(endpoint,{method:'DELETE',signal:AbortSignal.timeout(10000)});
        if(!r.ok)throw Error('Wylogowanie nie zostało potwierdzone. Spróbuj ponownie.');
        session=null;channel?.postMessage('logout');location.reload();
      }catch(e){state.textContent=e.message;}finally{button.disabled=false;}
    };
    button.onclick=()=>{if(session)logout();else{dialog.showModal();input.focus();}};
    form.onsubmit=async e=>{
      e.preventDefault();submit.disabled=true;message.textContent='Logowanie…';
      const secret=input.value.trim();input.value='';
      try{
        const r=await fetch(endpoint,{method:'POST',headers:{Authorization:'Bearer '+secret,'X-Owner-Origin':location.origin},credentials:'same-origin',redirect:'error',cache:'no-store',signal:AbortSignal.timeout(10000)});
        if(!r.ok){const data=await r.json();throw Error(data.detail||'Nie udało się zalogować.');}
        location.reload();
      }catch(e){message.textContent=e.message;}finally{submit.disabled=false;}
    };
    if(channel)channel.onmessage=e=>{if(e.data==='logout')location.reload();};
    try{
      const r=await fetch(endpoint,{headers:{'X-Owner-Origin':location.origin},credentials:'same-origin',redirect:'error',cache:'no-store',signal:AbortSignal.timeout(5000)});
      if(r.ok){const data=await r.json();if(data.authenticated&&typeof data.csrf==='string'&&data.expires_at*1000>Date.now())session=data;}
    }catch{state.textContent='Nie potwierdzono sesji.';}
    if(!session&&['localhost','127.0.0.1','[::1]'].includes(location.hostname)){
      try{
        const r=await fetch(endpoint+'/local',{method:'POST',headers:{'X-Owner-Origin':location.origin},credentials:'same-origin',redirect:'error',cache:'no-store',signal:AbortSignal.timeout(5000)});
        if(r.ok){const data=await r.json();if(data.authenticated&&data.mode==='local'&&typeof data.csrf==='string'&&data.expires_at*1000>Date.now())session=data;}
      }catch{state.textContent='Nie potwierdzono lokalnego dostępu.';}
    }
    if(!session){button.hidden=false;return;}
    button.hidden=session.mode==='local';button.textContent='Wyloguj właściciela';
    document.body.dataset.ownerAccess=session.mode||'token';
    state.textContent=session.mode==='local'?'Właściciel · ten komputer':'Właściciel zalogowany';
    expiryTimer=setTimeout(()=>location.reload(),Math.max(0,session.expires_at*1000-Date.now()));
    const ids=['token','history-token','delivery-token','publishing-token'];
    if(document.body.dataset.ownerPreview==='true')ids.push('client-token');
    for(const id of ids){const el=document.getElementById(id);if(!el)continue;el.required=false;el.value='';for(const label of el.labels||[])label.hidden=true;el.hidden=true;}
    const note=document.getElementById('delivery-token-note');if(note)note.textContent='Działa wspólna sesja właściciela. Wybierz ID zadania; tokena nie trzeba wpisywać ponownie.';
    for(const id of ['logout','history-logout',...(document.body.dataset.ownerPreview==='true'?['client-logout']:[])]){
      if(session.mode==='local'){const el=document.getElementById(id);if(el)el.hidden=true;continue;}
      document.getElementById(id)?.addEventListener('click',e=>{e.preventDefault();e.stopImmediatePropagation();logout();},{capture:true});
    }
    // Only read-only access forms auto-open; never submit publication/review actions.
    const access=document.getElementById('access')||document.getElementById('history-access');
    if(access)access.dispatchEvent(new Event('submit',{bubbles:true,cancelable:true}));
    if(document.body.dataset.ownerPreview==='true')document.getElementById('client-login')?.dispatchEvent(new Event('submit',{bubbles:true,cancelable:true}));
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot);else boot();
  window.addEventListener('pagehide',()=>{clearTimeout(expiryTimer);session=null;});
  window.addEventListener('pageshow',e=>{if(e.persisted)location.reload();});
})();
