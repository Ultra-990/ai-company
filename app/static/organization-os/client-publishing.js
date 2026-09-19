(() => {
  const $ = (name) => document.getElementById("publishing-" + name);
  const dialog = document.getElementById("client-publishing");
  let busy = false, epoch = 0, controller = new AbortController();
  function say(text) { $("message").textContent = text; }
  function clear() {
    epoch++; controller.abort(); controller = new AbortController(); busy = false;
    $("form").reset(); $("result").hidden = true; $("client-code").value = "";
    $("share-id").value = ""; $("shares").replaceChildren();
    $('milestones').replaceChildren();
    dialog.querySelectorAll("input,textarea,select,button").forEach((el) => { el.disabled = false; });
  }
  document.getElementById("open-client-publishing").addEventListener("click", () => {
    clear(); document.getElementById("owner-menu").close(); dialog.showModal(); (window.OwnerSession?.active?dialog.querySelector('input:not([hidden])'):$("token")).focus();
    say("Kod klienta ma ograniczony zakres i termin ważności.");
  });
  $("close").addEventListener("click", () => dialog.close());
  dialog.addEventListener("close", clear); dialog.addEventListener("cancel", clear);
  window.addEventListener("pagehide", () => { clear(); dialog.close(); });
  const integer = (value) => { const n = Number(value); if (!Number.isSafeInteger(n) || n < 1) throw new Error("Podaj poprawny identyfikator."); return n; };
  const make=(tag,text)=>{const n=document.createElement(tag);if(text!==undefined)n.textContent=text;return n;};
  function stage(data={}){
    if($('milestones').children.length>=30){say('Maksymalnie 30 etapów.');return;}
    const box=make('fieldset');box.dataset.stageKey=data.key||crypto.randomUUID();box.append(make('legend','Etap workflow'));
    for(const [field,label,max] of [['title','Nazwa',200],['description','Co powstaje?',2000],['deliverable','Udostępniony rezultat — treść lub opis materiału',6000],['acceptance_criteria','Kryteria odbioru — jedno w wierszu (do 12)',6012],['review_note','Ustalenia, blokada lub prośba o odbiór',2000]]){
      const l=make('label',label),input=make(field==='title'?'input':'textarea');input.dataset.field=field;input.maxLength=max;if(field==='title')input.required=true;else input.rows=3;
      input.value=field==='acceptance_criteria'?(data[field]||[]).join('\n'):data[field]||'';l.append(input);box.append(l);
    }
    const label=make('label','Status'),select=make('select');select.dataset.field='status';
    for(const [value,title] of [['planned','Zaplanowany'],['in_progress','W realizacji'],['review','Do odbioru'],['completed','Ukończony'],['blocked','Zablokowany']]){const option=make('option',title);option.value=value;select.append(option);}
    select.value=data.status||'planned';label.append(select);box.append(label);
    const remove=make('button','Usuń etap z nowej publikacji');remove.type='button';remove.addEventListener('click',()=>box.remove());box.append(remove);$('milestones').append(box);
  }
  $('add-stage').addEventListener('click',()=>stage());
  const publication = () => ({ title:$("name").value.trim(), summary:$("summary").value.trim(),
    next_step:$("next").value.trim(), status:$("state").value, progress:Number($("progress").value),
    milestones:[...$('milestones').children].map(box=>{const s={key:box.dataset.stageKey};for(const input of box.querySelectorAll('[data-field]'))s[input.dataset.field]=input.dataset.field==='acceptance_criteria'?input.value.split('\n').map(x=>x.trim()).filter(Boolean):input.value.trim();return s;}) });
  async function action(operation) {
    if (busy) return;
    const token = $("token").value.trim();
    if (!token && !window.OwnerSession?.active) { say("Zaloguj właściciela w górnym pasku lub podaj token."); return; }
    busy = true; const ticket = epoch;
    const fields = [...dialog.querySelectorAll("input,textarea,select,button")].filter((el) => el.id !== "publishing-close");
    fields.forEach((el) => { el.disabled = true; });
    const timeout = setTimeout(() => controller.abort(), 15000);
    const request = async (path, method="GET", payload) => {
      const response = await (window.OwnerSession?.fetch||fetch)(path, { method, headers:{Authorization:`Bearer ${token}`, "Content-Type":"application/json"},
        ...(payload ? {body:JSON.stringify(payload)} : {}), signal:controller.signal, credentials:"omit", cache:"no-store", redirect:"error" });
      if (ticket !== epoch) throw new Error("closed");
      if (!response.ok) {
        if ([401,403].includes(response.status)) { clear(); say("Nieprawidłowy token lub brak uprawnień właściciela."); }
        throw new Error(`Operacja nie została potwierdzona (HTTP ${response.status}). Sprawdź dane i stan udostępnienia.`);
      }
      const data = await response.json(); if (ticket !== epoch) throw new Error("closed"); return data;
    };
    try { await operation(request); }
    catch (error) { if (ticket === epoch) say(error.name === "AbortError" ? "Brak potwierdzenia. Przed ponowieniem sprawdź listę dostępów projektu." : error.message); }
    finally {
      clearTimeout(timeout);
      if (ticket === epoch) { busy = false; controller = new AbortController(); fields.forEach((el) => { el.disabled = false; }); }
    }
  }
  $("form").addEventListener("submit", (event) => {
    event.preventDefault();
    const data = publication(), projectId = $("project").value, days = $("days").value;
    action(async (request) => {
      if (!$("confirm").checked) throw new Error("Potwierdź sprawdzenie informacji dla klienta.");
      const share = await request("/api/client-shares", "POST", {...data, project_id:integer(projectId), expires_in_days:integer(days)});
      $("client-code").value = share.token; $("share-id").value = share.id; $("result").hidden = false;
      $("confirm").checked = false;
      say(`Utworzono udostępnienie #${share.id}, ważne do ${new Date(share.expires_at).toLocaleString("pl-PL")}. Zachowaj kod przed zamknięciem.`);
    });
  });
  $("list").addEventListener("click", () => {
    const id = $("project").value;
    action(async (request) => {
      const data = await request(`/api/client-shares?project_id=${integer(id)}`);
      $("shares").replaceChildren();
      if (!data.shares.length) $("shares").textContent = "Brak udostępnień tego projektu.";
      for (const share of data.shares) {
        const row = document.createElement("p");
        row.textContent = `#${share.id} · ${share.revoked ? "cofnięty" : share.expired ? "wygasły" : "aktywny"} · ważność ${new Date(share.expires_at).toLocaleString("pl-PL")}`;
        $("shares").append(row);
      }
      say("Lista do 30 najnowszych dostępów. Wpisz ID dostępu, który chcesz zmienić lub cofnąć.");
    });
  });
  $("update").addEventListener("click", () => {
    const data = publication(), id = $("share-id").value;
    action(async (request) => {
      if (!$("confirm").checked) throw new Error("Potwierdź treść przed aktualizacją.");
      await request(`/api/client-shares/${integer(id)}`, "PUT", data);
      $("confirm").checked = false; say("Zaktualizowano widok klienta. Kod i termin ważności pozostają bez zmian.");
    });
  });
  $('load').addEventListener('click',()=>{
    const id=$('share-id').value;
    action(async request=>{
      const data=await request(`/api/client-shares/${integer(id)}`),p=data.project;
      $('project').value=data.share.project_id;
      for(const [field,key] of [['name','title'],['summary','summary'],['next','next_step'],['state','status'],['progress','progress']])$(field).value=p[key];
      $('milestones').replaceChildren();for(const s of p.milestones)stage(s);
      $('confirm').checked=false;say('Wczytano istniejący workflow. Zmień dane, sprawdź je i opublikuj aktualizację. Nie odtworzono kodu klienta.');
    });
  });
  $("revoke").addEventListener("click", () => {
    const id = $("share-id").value;
    action(async (request) => {
      if (!window.confirm(`Cofnąć dostęp #${id}? Klient nie będzie mógł ponownie pobierać danych.`)) return;
      await request(`/api/client-shares/${integer(id)}/revoke`, "POST");
      $("client-code").value = ""; $("result").hidden = true; say(`Dostęp #${id} cofnięty.`);
    });
  });
})();
