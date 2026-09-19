/* Offline fixture diagnostics only. No external requests, source execution or model. */
(() => {
  'use strict';
  window.ApiContractProbe = {create({request}) {
    const node = (tag, text = '') => {const e = document.createElement(tag); e.textContent = text; return e;};
    const panel = node('section'); panel.className = 'panel';
    panel.append(node('h2', 'Diagnostyka odpowiedzi API — bez sieci'),
      node('p', 'Sprawdź powiązania pól przed integracją. Wklej wyłącznie zanonimizowaną próbkę JSON, bez tokenów, haseł i danych klienta. Nie łączymy się z API i niczego nie naprawiamy na koncie klienta.'));
    const responseLabel = node('label', 'Próbka odpowiedzi JSON (maks. 32 KiB)');
    const response = node('textarea'); response.rows = 6; response.maxLength = 32768; responseLabel.append(response);
    const observedLabel = node('label', 'Odczytany przez Ciebie status HTTP');
    const observed = node('input'); observed.type = 'number'; observed.min = 100; observed.max = 599; observed.value = '200'; observedLabel.append(observed);
    const expectedLabel = node('label', 'Oczekiwany status HTTP');
    const expected = node('input'); expected.type = 'number'; expected.min = 100; expected.max = 599; expected.value = '200'; expectedLabel.append(expected);
    const bindingsLabel = node('label', 'Powiązania jako JSON: nazwa, JSON Pointer, oczekiwany typ');
    const bindings = node('textarea'); bindings.rows = 5; bindings.maxLength = 16000; bindingsLabel.append(bindings);
    const sample = node('button', 'Wstaw przykład syntetyczny'); sample.type = 'button';
    const check = node('button', 'Sprawdź próbkę i powiązania'); check.type = 'button';
    const clear = node('button', 'Wyczyść próbkę i wynik'); clear.type = 'button';
    const output = node('div'); output.setAttribute('aria-live', 'polite');
    panel.append(responseLabel, observedLabel, expectedLabel, bindingsLabel,
      node('p', 'Np. /data/items/0/name wskazuje pole name pierwszego elementu. Typy: string, number, integer, boolean, object, array, null. required=false dopuszcza brak; nonempty=true wymaga niepustej wartości. To nie jest JSONPath ani kod.'),
      sample, check, clear, output);
    let busy = false, epoch = 0, controller;
    const invalidate = () => {epoch++; output.replaceChildren(); controller?.abort();};
    for (const input of [response, bindings, observed, expected]) input.addEventListener('input', invalidate);
    const reset = () => {invalidate(); response.value = ''; bindings.value = ''; observed.value = expected.value = '200';};
    clear.addEventListener('click', reset);
    sample.addEventListener('click', () => {
      invalidate();
      response.value = JSON.stringify({data: {items: [{name: 'Example', total: 2576}]}}, null, 2);
      bindings.value = JSON.stringify([{name: 'label', pointer: '/data/items/0/name', expected_type: 'string', required: true, nonempty: true},
        {name: 'total', pointer: '/data/items/0/total', expected_type: 'number', required: true}], null, 2);
      observed.value = expected.value = '200';
    });
    check.addEventListener('click', async () => {
      if (busy) return;
      invalidate(); const ticket = epoch; busy = true; check.disabled = true;
      controller = new AbortController();
      try {
        if (new TextEncoder().encode(response.value).length > 32768) throw Error('Próbka przekracza 32 KiB.');
        let mapping;
        try {mapping = JSON.parse(bindings.value);} catch {throw Error('Popraw JSON w polu powiązań.');}
        const result = await request({response_text: response.value, observed_status: Number(observed.value),
          expected_status: Number(expected.value), bindings: mapping}, controller.signal);
        if (ticket !== epoch) return;
        const labels = {passed: 'Próbka pasuje do zadeklarowanego kontraktu', warning: 'Próbka wymaga uwagi', failed: 'Wykryto niespójność próbki'};
        output.append(node('h3', labels[result.outcome] || 'Odczytano wynik'), node('p', result.limitation));
        for (const c of result.checks) output.append(node('p', `${c.name}: ${c.code} · ${c.outcome}${c.pointer !== undefined ? ' · ' + c.pointer : ''} — ${c.hint}`));
        output.append(node('p', 'Nie zapisano wyniku jako dowodu wydania ani wykonania zlecenia.'));
      } catch (e) {
        if (ticket === epoch) output.replaceChildren(node('p', e.message));
      } finally {busy = false; check.disabled = false;}
    });
    window.addEventListener('pagehide', reset);
    return panel;
  }};
  const host = document.getElementById('contract-probe');
  if (host) host.append(window.ApiContractProbe.create({request: async (payload, signal) => {
    if (!window.OwnerSession?.active) throw Error('Zaloguj właściciela.');
    const r = await window.OwnerSession.fetch('/api/upwork-orders/contract-probe', {
      method: 'POST', headers: {'Content-Type': 'application/json'}, cache: 'no-store', redirect: 'error',
      body: JSON.stringify(payload), signal});
    if (!window.OwnerSession?.active) throw Error('Sesja zakończona.');
    const data = await r.json();
    if (!r.ok) throw Error(typeof data.detail === 'string' ? data.detail : 'Nie można sprawdzić próbki.');
    return data;
  }}));
})();
