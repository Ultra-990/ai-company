// In-memory DOM/API only: no browser, model, server or containers.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('app/static/organization-os/requirement-checks.js', 'utf8');

function setup() {
  class Element {
    constructor(tag) { this.tag = tag; this.children = []; this.listeners = {}; }
    append(...items) { this.children.push(...items); }
    replaceChildren(...items) { this.children = items; }
    setAttribute(k, v) { this[k] = v; }
    addEventListener(name, fn) { this.listeners[name] = fn; }
    reportValidity() { return true; }
    set innerHTML(value) { throw Error('No HTML insertion'); }
  }
  const data = {source_checksum: 'a'.repeat(64), scope_checksum: 'b'.repeat(64),
    counts: {passed: 0, failed: 0}, note: 'Ręczna ocena, nie test.', available_reports: [{id: 8, run_id: 4, state: 'passed'}],
    criteria: [{id: 'c'.repeat(64), text: '<img src=x onerror=bad()> wymaganie', state: 'not_checked',
      observed_result: '', assessment_id: null, test_report: null}]};
  const window = {}, calls = [], errors = [];
  let busy = false, failing = false;
  const request = async (url, options = {}) => {
    calls.push({url, options});
    if (failing && options.method === 'POST') throw Error('Niepewne połączenie');
    if (url.includes('/history')) return {note: 'Historia deklaracji', next_cursor: null,
      entries: [{id: 12, created_at: '2026-09-14T00:00:00', state: 'passed',
        observed_result: '<script>literal history</script>', matches_current_scope: true}]};
    return options.method === 'POST' ? {assessment_id: 12} : data;
  };
  let pending;
  const act = fn => {
    if (busy) return;
    busy = true;
    pending = (async () => {
      try { await fn(); } catch (error) { errors.push(error.message); }
      finally { busy = false; }
    })();
    return pending;
  };
  vm.runInNewContext(source, {window, document: {createElement: tag => new Element(tag)}});
  const panel = window.RequirementChecks.create({run: {task_id: 3, package_id: 7}, request, act});
  const all = (root = panel) => [root, ...root.children.flatMap(child => all(child))];
  const get = tag => all().find(item => item.tag === tag);
  const load = () => panel.children[0].listeners.click();
  async function save() {
    get('form').listeners.submit({preventDefault() {}});
    await pending;
  }
  return {panel, all, get, calls, data, errors, load, save, setFail: value => { failing = value; }};
}

test('explicit load shows literal criteria and no automatic pass', async () => {
  const ui = setup();
  assert.equal(ui.calls.length, 0);
  await ui.load();
  assert.equal(ui.calls.length, 1);
  assert.equal(ui.calls[0].url, '/api/tasks/3/workspace-packages/7/requirements');
  assert(ui.get('summary').textContent.includes('<img src=x onerror=bad()>'));
  assert.equal(ui.get('select').value, 'not_checked');
  assert.equal(ui.get('input').checked, undefined);
});

test('confirmation binds observation to source, scope and previous assessment', async () => {
  const ui = setup();
  await ui.load();
  await ui.save();
  assert.equal(ui.calls.filter(c => c.options.method === 'POST').length, 0);
  ui.get('input').checked = true;
  ui.get('textarea').value = 'Sprawdzono klawiaturę: wszystkie przyciski osiągalne.';
  ui.get('select').value = 'passed';
  await ui.save();
  const writes = ui.calls.filter(c => c.options.method === 'POST');
  assert.equal(writes.length, 1);
  const body = JSON.parse(writes[0].options.body);
  assert.equal(body.source_checksum, ui.data.source_checksum);
  assert.equal(body.scope_checksum, ui.data.scope_checksum);
  assert.equal(body.criterion_id, ui.data.criteria[0].id);
  assert.equal(body.previous_id, null);
  assert.equal(body.test_report_id, null);
  assert.equal(body.state, 'passed');
  assert.equal(ui.calls.length, 3); // GET, POST, refresh GET
});

test('uncertain writes keep the exact replay body until an explicit reload', async () => {
  const ui = setup();
  await ui.load();
  ui.get('input').checked = true;
  ui.get('textarea').value = 'Pierwsza szczegółowa obserwacja wyniku.';
  ui.setFail(true);
  await ui.save();
  ui.get('textarea').value = 'Nowa treść nie może nadpisać niepewnej decyzji.';
  ui.setFail(false);
  await ui.save();
  const writes = ui.calls.filter(c => c.options.method === 'POST');
  assert.equal(writes.length, 2);
  assert.equal(writes[0].options.body, writes[1].options.body);
  assert.equal(ui.errors.length, 1);
});

test('available in build without executing a selected package', () => {
  const html = fs.readFileSync('app/templates/organization-os/build.html', 'utf8');
  assert(html.indexOf('requirement-checks.js') < html.indexOf('/build.js'));
  const code = fs.readFileSync('app/static/organization-os/build.js', 'utf8');
  assert(code.includes('checks.id=\'package-requirements\''));
  assert(code.includes('window.RequirementChecks.create({run,request,act})'));
});

test('history is a read and renders archived observations as text', async () => {
  const ui = setup();
  await ui.load();
  const button = ui.all().find(item => item.textContent === 'Historia ocen tego wymagania');
  await button.listeners.click();
  assert(ui.calls[1].url.endsWith(`/${ui.data.criteria[0].id}/history`));
  assert.equal(ui.get('pre').textContent, '<script>literal history</script>');
  assert.equal(ui.calls.filter(call => call.options.method === 'POST').length, 0);
});
