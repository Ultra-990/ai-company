/* Client documents are plain text, loaded only by the owner's explicit action. */
(() => {
  'use strict';
  window.DeliveryHandoff = {
    create({run, request, act}) {
      const node = (tag, text = '') => {
        const item = document.createElement(tag);
        item.textContent = text;
        return item;
      };
      const panel = node('section');
      panel.setAttribute('aria-label', 'Przekazanie klientowi');
      const load = node('button', 'Instrukcja klienta i wiadomość do Upwork');
      load.type = 'button';
      const content = node('div');
      content.setAttribute('aria-live', 'polite');
      panel.append(load, content);

      function download(name, text) {
        const url = URL.createObjectURL(new Blob([text], {type: 'text/plain;charset=utf-8'}));
        const link = node('a');
        link.href = url;
        link.download = name;
        document.body.append(link);
        link.click();
        link.remove();
        setTimeout(() => URL.revokeObjectURL(url), 1000);
      }

      load.addEventListener('click', () => act(async () => {
        // Discard old controls before a fresh request: a revoked release must
        // not leave stale download buttons after the server denies this read.
        content.replaceChildren();
        const data = await request(`/api/package-runs/${run.id}/handoff`);
        content.append(node('h4', 'Materiały do ręcznego przekazania'),
          node('p', `Źródła SHA-256: ${data.source_checksum}`),
          node('p', 'Nic nie zostało wysłane. Sprawdź szkic przed przekazaniem klientowi.'));
        if (data.delivery_summary) {
          const summary = data.delivery_summary;
          content.append(node('p', `${summary.file_count} plików · ${summary.source_bytes} B źródeł · profil ${summary.profile}`),
            node('p', summary.verified_http_examples === null ? 'Bez osobnego planu przykładów HTTP — nie jest to pełne potwierdzenie zakresu.' :
              `${summary.verified_http_examples} wybranych przykładów HTTP zaliczono dla tej wersji. Nie oznacza to pełnego pokrycia wymagań.`));
        }
        const checklist = node('ol');
        for (const text of data.owner_checklist) checklist.append(node('li', text));
        const label = node('label', 'Wiadomość do klienta (EN) — szkic do skopiowania');
        const message = node('textarea');
        message.readOnly = true;
        message.rows = 12;
        message.value = data.message_en;
        label.append(message);
        content.append(checklist, label);
        const saveMessage = node('button', 'Pobierz szkic wiadomości (.txt)');
        saveMessage.type = 'button';
        saveMessage.addEventListener('click', () => act(async () => {
          const fresh = await request(`/api/package-runs/${run.id}/handoff`);
          download(`message-release-${run.id}.txt`, fresh.message_en);
        }));
        content.append(saveMessage);
        for (const [name, title] of [['CLIENT-START-HERE.md', 'Instrukcja EN'],
                                    ['CLIENT-START-HERE.pl.md', 'Instrukcja PL'],
                                    ['DELIVERY-SUMMARY.md', 'Metryka wydania EN'],
                                    ['DELIVERY-SUMMARY.pl.md', 'Metryka wydania PL']]) {
          if (typeof data.guides[name] !== 'string') continue;
          const details = node('details');
          details.append(node('summary', title), node('pre', data.guides[name]));
          const save = node('button', `Pobierz: ${title}`);
          save.type = 'button';
          save.addEventListener('click', () => act(async () => {
            const fresh = await request(`/api/package-runs/${run.id}/handoff`);
            download(name, fresh.guides[name]);
          }));
          content.append(details, save);
        }
      }));
      return panel;
    },
  };
})();
