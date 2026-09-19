// In-memory DOM only: no browser, model, containers or network.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

function setup() {
  class Element {
    constructor(tag) { this.tag = tag; this.children = []; this.listeners = {}; }
    setAttribute(k, v) { this[k] = v; }
    append(...children) { this.children.push(...children); }
    replaceChildren(...children) { this.children = children; }
    addEventListener(k, fn) { this.listeners[k] = fn; }
    click() { return this.listeners.click?.(); }
    set innerHTML(value) { throw Error('Unsafe HTML'); }
  }
  const window = {}, requests = [], errors = [];
  const pages = [{packages: [{artifact_id: 8, checksum: 'a'.repeat(64)}], next_cursor: 8},
    {packages: [{artifact_id: 2, checksum: 'b'.repeat(64)}], next_cursor: null}];
  const data = {base_id: 8, package_id: 12, base_checksum: 'a', package_checksum: 'b',
    counts: {added: 0, removed: 0, modified: 1, unchanged: 1},
    files: [{path: 'app.py', status: 'modified', before: {size_bytes: 1}, after: {size_bytes: 2}}],
    detail: {path: 'app.py', available: true, diff: '+<script>do_not_execute()</script>'}};
  let fail = false, busy = false, intercept;
  const request = async path => {
    requests.push(path);
    if (fail) throw Error('Denied');
    if (intercept) return intercept(path);
    return path.includes('/comparison?') ? data : pages.shift();
  };
  const act = async fn => { if (busy) return; busy = true;
    try { await fn(); } catch (e) { errors.push(e.message); } finally { busy = false; } };
  vm.runInNewContext(fs.readFileSync('app/static/organization-os/package-comparison.js', 'utf8'),
    {window, document: {createElement: tag => new Element(tag)}});
  const panel = window.PackageComparison.create({run: {task_id: 7, package_id: 12}, request, act});
  const all = (root = panel) => [root, ...root.children.flatMap(child => all(child))];
  const button = text => all().find(n => n.tag === 'button' && n.textContent === text);
  const select = () => all().find(n => n.tag === 'select');
  return {panel, requests, errors, data, pages, all, button, select,
    fail: () => { fail = true; }, intercept: fn => { intercept = fn; }};
}

test('explicit reads, older pagination and comparison use task-bound GET URLs', async () => {
  const ui = setup();
  assert.equal(ui.requests.length, 0);
  await ui.panel.children[0].click();
  assert.equal(ui.requests[0], '/api/tasks/7/workspace-packages?before=12&limit=20');
  await ui.button('Wczytaj starsze wersje').click();
  assert.equal(ui.requests[1], '/api/tasks/7/workspace-packages?before=8&limit=20');
  assert(ui.button('Wczytaj starsze wersje').hidden);
  ui.select().value = '8';
  await ui.button('Pokaż zmiany').click();
  assert.equal(ui.requests[2], '/api/tasks/7/workspace-packages/12/comparison?base_id=8');
  assert(!ui.all().some(n => n.tag === 'pre'));
  await ui.button('Pokaż różnice: app.py').click();
  assert.equal(ui.requests[3], ui.requests[2] + '&path=app.py');
  assert(ui.all().some(n => n.tag === 'pre' && n.textContent === ui.data.detail.diff));
});

test('empty history explains why there is no comparison', async () => {
  const ui = setup(); ui.pages[0] = {packages: [], next_cursor: null};
  await ui.panel.children[0].click();
  assert(ui.button('Pokaż zmiany').hidden);
  assert(ui.all().some(n => n.textContent === 'Brak wcześniejszych paczek tego zadania.'));
});

test('denied reads clear stale output and repeated clicks share busy guard', async () => {
  const ui = setup();
  await Promise.all([ui.panel.children[0].click(), ui.panel.children[0].click()]);
  assert.equal(ui.requests.length, 1);
  ui.select().value = '8'; await ui.button('Pokaż zmiany').click();
  await ui.button('Pokaż różnice: app.py').click();
  ui.fail(); await ui.button('Pokaż różnice: app.py').click();
  assert(!ui.all().some(n => n.tag === 'pre'));
  await ui.panel.children[0].click();
  assert.equal(ui.panel.children[1].children.length, 0);
  assert.equal(ui.errors.length, 2);
});

test('large files display reason instead of invented or partial diff', async () => {
  const ui = setup(); await ui.panel.children[0].click();
  ui.select().value = '8'; await ui.button('Pokaż zmiany').click();
  ui.data.detail = {path: 'app.py', available: false, reason: 'Limit 16 KiB'};
  await ui.button('Pokaż różnice: app.py').click();
  assert(ui.all().some(n => n.textContent === 'Limit 16 KiB'));
  assert(!ui.all().some(n => n.tag === 'pre'));
});

test('changing base during request discards late results', async () => {
  const ui = setup(); await ui.panel.children[0].click(); ui.select().value = '8';
  let resolve;
  ui.intercept(() => new Promise(r => { resolve = r; }));
  const pending = ui.button('Pokaż zmiany').click();
  ui.select().value = '2'; ui.select().listeners.change(); resolve(ui.data); await pending;
  assert(!ui.button('Pokaż różnice: app.py'));
});

test('helper is loaded before build and available without a completed test run', () => {
  const html = fs.readFileSync('app/templates/organization-os/build.html', 'utf8');
  assert(html.indexOf('package-comparison.js') < html.indexOf('/build.js'));
  assert(fs.readFileSync('app/static/organization-os/build.js', 'utf8')
    .includes('window.PackageComparison.create({run,request,act})'));
});
