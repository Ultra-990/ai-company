(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const node = (tag, text) => { const n = document.createElement(tag); n.textContent = text; return n; };
  let task = null, pending = null, result = null, imageURL = null, busy = false, timer = null, deadline = 0;
  const labels = {submitting:'Wysyłanie — nie ponawiaj', queued:'W kolejce / generowanie', uncertain:'Stan niepewny — sprawdź wynik, nie ponawiaj', succeeded:'Obraz zapisany', failed:'Nie wykonano / błąd generowania'};
  async function request(path, options = {}, blob = false) {
    if (!window.OwnerSession?.active) throw Error('Zaloguj właściciela w górnej nawigacji.');
    const response = await window.OwnerSession.fetch(path, {...options, headers:{'Content-Type':'application/json'}, signal:AbortSignal.timeout(30000)});
    if (!response.ok) { let data; try { data = await response.json(); } catch {} throw Error(data?.detail || `Błąd ${response.status}. Wczytaj historię przed ponowieniem.`); }
    return blob ? response.blob() : response.json();
  }
  async function act(fn) {
    if (busy) return; busy = true;
    document.querySelectorAll('main button').forEach(b => b.disabled = true);
    try { await fn(); } catch (error) { $('message').textContent = error.message; }
    finally { busy = false; document.querySelectorAll('main button').forEach(b => b.disabled = false); }
  }
  const base = () => `/api/tasks/${task}/images`;
  function clearResult() {
    if (imageURL) URL.revokeObjectURL(imageURL);
    imageURL = null; result = null; $('image').removeAttribute('src'); $('result').hidden = true;
  }
  async function show(job) {
    const report = await request(`${base()}/${job.id}/report`);
    const blob = await request(`${base()}/${job.id}/download`, {}, true);
    clearResult(); imageURL = URL.createObjectURL(blob); result = {job, report};
    $('image').src = imageURL; $('report').textContent = JSON.stringify(report, null, 2);
    $('result-binding').textContent = `Zadanie #${task} · obraz #${job.id} · odbiór: ${job.review} · SHA-256: ${report.image_sha256}`;
    $('review').hidden = job.review !== 'pending'; $('reason').value = '';
    $('result').hidden = false; $('result').scrollIntoView({behavior:'auto', block:'start'});
  }
  async function history(update = false) {
    if (!task) throw Error('Najpierw wczytaj zadanie.');
    let data = await request(base());
    if (update) {
      for (const job of data.jobs.filter(j => ['submitting','queued','uncertain'].includes(j.state)))
        await request(`${base()}/${job.id}/refresh`, {method:'POST'});
      data = await request(base());
    }
    $('jobs').replaceChildren();
    for (const job of data.jobs) {
      const card = node('article', ''); card.className = 'artifact';
      card.append(node('h3', `Obraz #${job.id} — ${labels[job.state] || job.state}`), node('p', job.inputs.prompt),
        node('p', `Seed ${job.inputs.seed} · odbiór: ${job.review}${job.error_code ? ' · ' + job.error_code : ''}`));
      if (job.artifact_id) { const button = node('button', 'Obejrzyj i odbierz'); button.type = 'button'; button.onclick = () => act(() => show(job)); card.append(button); }
      $('jobs').append(card);
    }
    if (!data.jobs.length) $('jobs').append(node('p','To zadanie nie ma jeszcze wygenerowanych grafik.'));
    clearTimeout(timer);
    if (data.jobs.some(j => ['submitting','queued','uncertain'].includes(j.state)) && Date.now() < deadline)
      timer = setTimeout(() => act(() => history(true)), 4000);
    else if (data.jobs.some(j => ['submitting','queued','uncertain'].includes(j.state)))
      $('message').textContent = 'Generowanie lub stan niepewny. Odśwież historię, aby odebrać wynik. Nie anulowano pracy ComfyUI.';
  }
  $('select-task').onsubmit = e => { e.preventDefault(); act(async () => {
    const id = Number($('task-id').value);
    const data = await request(`/api/tasks/${id}`);
    clearTimeout(timer); clearResult(); pending = null; task = id;
    $('binding').textContent = `Zadanie #${id}: ${data.title} · status: ${data.status} · zgoda: ${data.approval_status}`;
    $('generate').hidden = false; deadline = Date.now() + 300000; await history(true);
  }); };
  $('generate').onsubmit = e => { e.preventDefault(); act(async () => {
    if (!task) throw Error('Wczytaj zadanie.');
    const values = {prompt:$('prompt').value.trim(), seed:Number($('seed').value), confirm:true};
    if (pending && (pending.prompt !== values.prompt || pending.seed !== values.seed))
      throw Error('Poprzednie wysłanie jest niepotwierdzone. Wczytaj historię przed nowym wariantem.');
    pending ||= {...values, request_id:crypto.randomUUID()};
    $('message').textContent = 'Wysyłam jedną grafikę do lokalnego ComfyUI…';
    const run = await request(base(), {method:'POST', body:JSON.stringify(pending)});
    pending = null; deadline = Date.now() + 300000;
    $('message').textContent = `Obraz #${run.id}: ${labels[run.state]}.`; await history(true);
  }); };
  $('refresh').onclick = () => act(async () => { deadline = Date.now() + 300000; await history(true); });
  $('download').onclick = () => { if (!result || !imageURL) return; const a = node('a',''); a.href = imageURL; a.download = `task-${task}-image-${result.job.id}.png`; a.click(); };
  $('review').onsubmit = e => { e.preventDefault(); act(async () => {
    if (!result) return;
    const reviewed = await request(`${base()}/${result.job.id}/review`, {method:'POST', body:JSON.stringify({checksum:result.report.artifact_checksum, decision:$('decision').value, reason:$('reason').value})});
    result.job = reviewed;
    $('result-binding').textContent = `Zadanie #${task} · obraz #${reviewed.id} · odbiór: ${reviewed.review} · SHA-256: ${result.report.image_sha256}`;
    $('review').hidden = true; $('message').textContent = 'Zapisano odbiór obrazu. Nie zamknięto zadania i nie opublikowano klientowi.'; await history();
  }); };
  const id = new URLSearchParams(location.search).get('task');
  if (/^[1-9][0-9]*$/.test(id || '')) $('task-id').value = id;
  window.addEventListener('pagehide', () => { clearTimeout(timer); clearResult(); pending = null; });
})();
