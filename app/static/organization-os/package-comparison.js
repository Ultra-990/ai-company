/* Owner-only comparison: render sources as inert text, never execute them. */
(() => {
  'use strict';
  window.PackageComparison = {create({run, request, act}) {
    const node = (tag, text = '') => { const el = document.createElement(tag); el.textContent = text; return el; };
    const panel = node('section');
    panel.setAttribute('aria-label', 'Porównanie wersji źródeł');
    const load = node('button', 'Porównaj pliki z wcześniejszą wersją'); load.type = 'button';
    const content = node('div'); content.setAttribute('aria-live', 'polite');
    panel.append(load, content);
    const root = `/api/tasks/${run.task_id}/workspace-packages`;
    load.addEventListener('click', () => act(async () => {
      content.replaceChildren();
      const label = node('label', 'Wersja bazowa (starsza paczka tego zadania)');
      const select = node('select'); label.append(select);
      const more = node('button', 'Wczytaj starsze wersje'); more.type = 'button';
      const compare = node('button', 'Pokaż zmiany'); compare.type = 'button';
      const result = node('div');
      const detail = node('div');
      let cursor = run.package_id;
      async function page() {
        const data = await request(`${root}?before=${cursor}&limit=20`);
        for (const p of data.packages) {
          const option = node('option', `Paczka #${p.artifact_id} · ${p.checksum.slice(0, 12)}`);
          option.value = String(p.artifact_id); select.append(option);
        }
        cursor = data.next_cursor;
        more.hidden = cursor === null;
        compare.hidden = !select.children.length;
        if (!select.children.length) result.replaceChildren(node('p', 'Brak wcześniejszych paczek tego zadania.'));
      }
      await page();
      content.append(node('p', `Porównywana wersja: paczka #${run.package_id}. Porównanie nie uruchamia kodu i nie potwierdza poprawności.`),
        label, more, compare, result, detail);
      more.addEventListener('click', () => act(async () => { if (cursor !== null) await page(); }));
      select.addEventListener('change', () => { result.replaceChildren(); detail.replaceChildren(); });
      compare.addEventListener('click', () => act(async () => {
        result.replaceChildren(); detail.replaceChildren();
        const base = select.value;
        if (!/^[1-9][0-9]*$/.test(base)) throw Error('Wybierz wersję bazową.');
        const url = `${root}/${run.package_id}/comparison?base_id=${base}`;
        const data = await request(url);
        if (select.value !== base) return;
        result.append(node('p', `Baza #${data.base_id}: ${data.base_checksum}`),
          node('p', `Wersja #${data.package_id}: ${data.package_checksum}`),
          node('p', `Dodane: ${data.counts.added} · zmienione: ${data.counts.modified} · usunięte: ${data.counts.removed} · bez zmian: ${data.counts.unchanged}`));
        const statuses = {added: 'dodany', modified: 'zmieniony', removed: 'usunięty', unchanged: 'bez zmian'};
        for (const file of data.files) {
          const row = node('p', `${file.path} — ${statuses[file.status]} · ${file.before?.size_bytes ?? 0} → ${file.after?.size_bytes ?? 0} B `);
          if (file.status !== 'unchanged') {
            const show = node('button', 'Pokaż różnice: ' + file.path); show.type = 'button';
            show.addEventListener('click', () => act(async () => {
              detail.replaceChildren();
              const fresh = await request(`${url}&path=${encodeURIComponent(file.path)}`);
              if (select.value !== base) return;
              if (fresh.base_checksum !== data.base_checksum || fresh.package_checksum !== data.package_checksum)
                throw Error('Wersje uległy zmianie. Odczytaj porównanie ponownie.');
              const d = fresh.detail;
              detail.append(node('h4', d.path));
              if (!d.available) detail.append(node('p', d.reason));
              else if (d.line_endings_or_final_newline_only) detail.append(node('p', 'Zmieniły się wyłącznie zakończenia wierszy lub końcowy znak nowej linii.'));
              else detail.append(node('pre', d.diff || 'Brak różnic tekstowych.'));
            }));
            row.append(show);
          }
          result.append(row);
        }
      }));
    }));
    return panel;
  }};
})();
