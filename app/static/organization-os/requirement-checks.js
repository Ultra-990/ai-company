/* Owner observations of immutable source versions; no runner or model calls. */
(() => {
  'use strict';
  const labels = {not_checked: 'Nie sprawdzono', passed: 'Potwierdzone ręcznie',
    failed: 'Nie spełnia wymagania', stale: 'Zakres zmieniony — sprawdź ponownie',
    invalid: 'Niespójny zapis lub dowód — wymaga sprawdzenia'};
  window.RequirementChecks = {
    create({run, request, act}) {
      const node = (tag, text = '') => {
        const element = document.createElement(tag);
        element.textContent = text;
        return element;
      };
      const panel = node('section');
      panel.setAttribute('aria-label', 'Weryfikacja wymagań klienta');
      const open = node('button', 'Sprawdź wymagania klienta dla tej wersji');
      open.type = 'button';
      const content = node('div');
      content.setAttribute('aria-live', 'polite');
      const path = `/api/tasks/${run.task_id}/workspace-packages/${run.package_id}/requirements`;
      panel.append(open, content);

      async function load() {
        const data = await request(path);
        content.replaceChildren(node('h4', 'Wymagania a rzeczywisty wynik'),
          node('p', `${data.counts.passed}/${data.criteria.length} potwierdzono ręcznie; ${data.counts.failed} niespełnionych.`),
          node('p', data.note), node('p', `Źródła SHA-256: ${data.source_checksum}`));
        for (const criterion of data.criteria) {
          const details = node('details');
          details.append(node('summary', `${labels[criterion.state]} · ${criterion.text}`));
          const form = node('form');
          const stateLabel = node('label', 'Wynik sprawdzenia');
          const state = node('select');
          for (const key of ['not_checked', 'passed', 'failed']) {
            const option = node('option', labels[key]);
            option.value = key;
            state.append(option);
          }
          state.value = ['passed', 'failed'].includes(criterion.state) ? criterion.state : 'not_checked';
          stateLabel.append(state);
          const noteLabel = node('label', 'Co sprawdzono? Dane wejściowe, oczekiwany i rzeczywisty wynik');
          const note = node('textarea');
          note.required = true;
          note.minLength = 10;
          note.maxLength = 2000;
          note.rows = 4;
          note.value = criterion.observed_result;
          noteLabel.append(note);
          const evidenceLabel = node('label', 'Opcjonalny raport testów tej paczki (nie dowodzi pokrycia wymagania)');
          const evidence = node('select');
          const empty = node('option', 'Tylko opisana obserwacja właściciela');
          empty.value = '';
          evidence.append(empty);
          for (const report of data.available_reports) {
            const option = node('option', `Raport #${report.id} · test #${report.run_id} · ${report.state === 'passed' ? 'zaliczony' : 'niezaliczony'}`);
            option.value = String(report.id);
            evidence.append(option);
          }
          evidence.value = criterion.test_report ? String(criterion.test_report.id) : '';
          evidenceLabel.append(evidence);
          const confirmation = node('label', ' Zapisuję własną obserwację. Nie oznacza to wykonania nowych testów ani odbioru klienta.');
          const confirm = node('input');
          confirm.type = 'checkbox';
          confirm.required = true;
          confirmation.append(confirm);
          const save = node('button', 'Zapisz weryfikację wymagania');
          save.type = 'submit';
          form.append(stateLabel, noteLabel, evidenceLabel, confirmation, save);
          let pending = null;
          form.addEventListener('submit', event => {
            event.preventDefault();
            if (!confirm.checked || !form.reportValidity()) return;
            act(async () => {
              // Keep the exact body on an uncertain response. Reload to change
              // it after a failed request, rather than overwrite another tab.
              pending ||= {criterion_id: criterion.id, source_checksum: data.source_checksum,
                scope_checksum: data.scope_checksum, previous_id: criterion.assessment_id,
                state: state.value, observed_result: note.value.trim(),
                test_report_id: evidence.value ? Number(evidence.value) : null, confirm_observation: true};
              await request(path, {method: 'POST', body: JSON.stringify(pending)});
              await load();
            });
          });
          details.append(form, node('p', `Zapis: ${criterion.assessment_id || 'brak'}. Po niepewnym zapisie ponów bez zmian albo odśwież listę przed zmianą oceny.`));
          const historyButton = node('button', 'Historia ocen tego wymagania');
          historyButton.type = 'button';
          const history = node('div');
          let cursor = null;
          historyButton.addEventListener('click', () => act(async () => {
            const result = await request(`${path}/${criterion.id}/history${cursor ? `?before=${cursor}` : ''}`);
            if (cursor === null) history.replaceChildren(node('p', result.note));
            for (const entry of result.entries) {
              history.append(node('p', `#${entry.id} · ${entry.created_at} · ${labels[entry.state]}${entry.matches_current_scope ? '' : ' · niezgodne z obecnym zakresem'}`),
                node('pre', entry.observed_result));
            }
            if (!result.entries.length) history.append(node('p', 'Brak zapisanych ocen.'));
            cursor = result.next_cursor;
            historyButton.textContent = cursor ? 'Starsze oceny' : 'Odśwież historię ocen';
          }));
          details.append(historyButton, history);
          content.append(details);
        }
      }
      open.addEventListener('click', () => act(async () => {
        content.replaceChildren();
        await load();
      }));
      return panel;
    },
  };
})();
