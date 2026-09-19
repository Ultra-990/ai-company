/* Declarative examples only. Saving a plan never starts a model or container. */
(() => {
  'use strict';
  window.AcceptancePlans = {
    create({run, request, act, onStart}) {
      const node = (tag, text = '') => {
        const element = document.createElement(tag);
        element.textContent = text;
        return element;
      };
      const panel = node('section');
      panel.setAttribute('aria-label', 'Automatyczne przykłady odbioru');
      const open = node('button', 'Przygotuj automatyczne sprawdzanie wymagań');
      open.type = 'button';
      const content = node('div');
      content.setAttribute('aria-live', 'polite');
      const base = `/api/tasks/${run.task_id}/workspace-packages/${run.package_id}`;
      panel.append(open, content);

      async function load() {
        const matrix = await request(base + '/requirements');
        const listing = await request(base + '/acceptance-plans');
        content.replaceChildren(node('h4', 'Przykłady, których model nie może zmienić'),
          node('p', 'Zapisz 1–4 konkretne żądania GET i oczekiwane wyniki. Przykład: /api/estimate?hours=8&rate=322 → pole total = 2576. Dopasuj ścieżkę do faktycznej aplikacji.'),
          node('p', 'Każdy przykład działa w osobnym, czystym środowisku. Bez logowania, sesji, zapisów POST i zewnętrznych adresów. Zaliczony przykład nie potwierdza całego wymagania.'),
          node('p', 'Sam zapis to szkic. Wybór planu do cyklu czyni go warunkiem odbioru i wydania zadania. Cykl bez planu nie usuwa tego warunku; nowszy jawnie wybrany plan go zastępuje.'),
          node('p', listing.execution_enabled ? 'Wykonanie dostępne po osobnym uruchomieniu cyklu; zapis planu niczego nie uruchamia.' :
            'Możesz przygotować plan. Wykonywanie nowych kontroli HTTP jest wyłączone do bezpiecznego terminu i weryfikacji izolacji.'));
        for (const plan of listing.plans) {
          const details = node('details');
          details.append(node('summary', `Plan #${plan.id}${plan.invalid ? ' — nieaktualny lub niespójny' : ` · ${plan.cases.length} przykładów`}`));
          if (!plan.invalid) {
            details.append(node('pre', JSON.stringify(plan.cases, null, 2)),
              node('p', `SHA-256 planu: ${plan.checksum}. To zapis oczekiwań, nie wynik wykonania.`));
            if (listing.execution_enabled && onStart) {
              const start = node('button', 'Testuj i napraw z tym planem');
              start.type = 'button';
              start.addEventListener('click', () => onStart(plan));
              details.append(start);
            }
          }
          content.append(details);
        }
        if (!matrix.criteria.length) {
          content.append(node('p', 'Najpierw uzupełnij kryteria odbioru zlecenia.'));
          return;
        }
        const form = node('form');
        const field = (text, input) => {
          const label = node('label', text);
          label.append(input);
          form.append(label);
          return input;
        };
        const criterion = field('Wymaganie zlecenia', node('select'));
        for (const item of matrix.criteria) {
          const option = node('option', item.text);
          option.value = item.id;
          criterion.append(option);
        }
        const title = field('Nazwa przykładu', node('input'));
        title.required = true; title.minLength = 3; title.maxLength = 120;
        const path = field('Lokalna ścieżka GET (np. /api/estimate?hours=8&rate=322)', node('input'));
        path.required = true; path.maxLength = 850;
        const status = field('Oczekiwany status HTTP (200–499)', node('input'));
        status.type = 'number'; status.required = true; status.min = 200; status.max = 499; status.step = 1; status.value = '200';
        const jsonField = field('Pole JSON, np. total lub data.total (puste = tylko status HTTP)', node('input'));
        jsonField.maxLength = 120;
        const expected = field('Oczekiwana wartość JSON, np. 2576, true, null lub "tekst"', node('input'));
        expected.maxLength = 3100;
        const add = node('button', 'Dodaj przykład do szkicu');
        add.type = 'submit';
        const draft = node('ol');
        const notice = node('p');
        notice.setAttribute('role', 'status');
        const save = node('button', 'Zapisz niezmienny plan — bez uruchamiania');
        save.type = 'button'; save.hidden = true;
        const cases = [];
        let pending = null;
        const render = () => {
          draft.replaceChildren();
          cases.forEach((item, index) => {
            const row = node('li', `${item.title}: GET ${item.path} → HTTP ${item.status}${item.json_field ? `; ${item.json_field} = ${JSON.stringify(item.expected)}` : ''} `);
            const remove = node('button', 'Usuń ze szkicu');
            remove.type = 'button';
            remove.addEventListener('click', () => {
              if (pending) { notice.textContent = 'Ponów zapis bez zmian albo odśwież plany przed edycją.'; return; }
              cases.splice(index, 1); render();
            });
            row.append(remove); draft.append(row);
          });
          save.hidden = !cases.length;
        };
        form.addEventListener('submit', event => {
          event.preventDefault();
          if (!form.reportValidity()) return;
          if (pending) { notice.textContent = 'Ponów zapis bez zmian albo odśwież plany przed edycją.'; return; }
          if (cases.length >= 4) { notice.textContent = 'Maksymalnie 4 przykłady w jednym planie.'; return; }
          try {
            const key = jsonField.value.trim();
            const value = key ? JSON.parse(expected.value) : null;
            if (value !== null && !['string', 'number', 'boolean'].includes(typeof value)) throw Error('Wpisz pojedynczą wartość JSON, nie obiekt ani listę.');
            if (typeof value === 'number' && (!Number.isFinite(value) || Math.abs(value) > 2 ** 53)) throw Error('Liczba przekracza bezpieczny zakres.');
            cases.push({criterion_id: criterion.value, title: title.value.trim(), path: path.value.trim(),
              status: Number(status.value), json_field: key || null, expected: value});
            notice.textContent = 'Przykład dodany do szkicu. Jeszcze nie zapisano planu ani nie wykonano testu.';
            render();
          } catch (error) { notice.textContent = `Sprawdź oczekiwaną wartość: ${error.message}`; }
        });
        save.addEventListener('click', () => act(async () => {
          if (!cases.length) return;
          pending ||= {request_id: crypto.randomUUID(), source_checksum: matrix.source_checksum,
            scope_checksum: matrix.scope_checksum, cases: cases.map(item => ({...item}))};
          notice.textContent = 'Zapisuję plan. Po niepewnej odpowiedzi ponów bez zmian albo odśwież listę.';
          await request(base + '/acceptance-plans', {method: 'POST', body: JSON.stringify(pending)});
          await load();
        }));
        form.append(add);
        content.append(form, draft, notice, save);
      }
      open.addEventListener('click', () => act(load));
      return panel;
    },
  };
})();
