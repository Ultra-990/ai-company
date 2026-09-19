// Controller checks only: no browser, HTTP server, GPU or model.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('app/static/organization-os/delivery-handoff.js', 'utf8');

function setup() {
  class Element {
    constructor(tag) { this.tag = tag; this.children = []; this.listeners = {}; }
    setAttribute(k, v) { this[k] = v; }
    append(...children) { this.children.push(...children); }
    replaceChildren(...children) { this.children = children; }
    addEventListener(name, fn) { this.listeners[name] = fn; }
    click() { if (this.tag === 'a') links.push(this); return this.listeners.click?.(); }
    remove() { this.removed = true; }
    set innerHTML(value) { throw Error('HTML insertion forbidden'); }
  }
  const links = [], requests = [], errors = [], blobs = [], revoked = [];
  const document = {createElement: tag => new Element(tag), body: new Element('body')};
  const window = {};
  let fail = false, busy = false;
  const data = {source_checksum: 'a'.repeat(64), owner_checklist: ['Check scope'],
    message_en: '<img src=x onerror=bad()> literal text', guides: {
      'CLIENT-START-HERE.md': '# English guide', 'CLIENT-START-HERE.pl.md': '# Polska instrukcja'}};
  const request = async path => {
    requests.push(path);
    if (fail) throw Error('Wydanie nie jest już aktualne.');
    return data;
  };
  const act = async fn => {
    if (busy) return;
    busy = true;
    try { await fn(); } catch (error) { errors.push(error.message); }
    finally { busy = false; }
  };
  vm.runInNewContext(source, {window, document, Blob,
    URL: {createObjectURL: blob => { blobs.push(blob); return 'blob:test'; },
          revokeObjectURL: url => revoked.push(url)},
    setTimeout: fn => fn()});
  const panel = window.DeliveryHandoff.create({run: {id: 17}, request, act});
  const all = (root = panel) => [root, ...root.children.flatMap(child => all(child))];
  const button = text => all().find(node => node.tag === 'button' && node.textContent === text);
  return {panel, all, button, data, requests, errors, blobs, links, revoked, fail: () => { fail = true; }};
}

test('explicit read renders inert text and does not submit a release or send a message', async () => {
  const ui = setup();
  assert.equal(ui.requests.length, 0);
  await ui.panel.children[0].click();
  assert.deepEqual(ui.requests, ['/api/package-runs/17/handoff']);
  const area = ui.all().find(node => node.tag === 'textarea');
  assert.equal(area.value, ui.data.message_en);
  assert.equal(area.readOnly, true);
  assert.equal(ui.all().filter(node => node.tag === 'pre').length, 2);
  assert.equal(ui.links.length, 0);
});

test('download revalidates current release and cleans up blob URLs', async () => {
  const ui = setup();
  await ui.panel.children[0].click();
  await ui.button('Pobierz: Instrukcja PL').click();
  assert.equal(ui.requests.length, 2);
  assert.equal(ui.links[0].download, 'CLIENT-START-HERE.pl.md');
  assert.equal(await ui.blobs[0].text(), ui.data.guides['CLIENT-START-HERE.pl.md']);
  assert.equal(ui.links[0].removed, true);
  assert.deepEqual(ui.revoked, ['blob:test']);
  await ui.button('Pobierz szkic wiadomości (.txt)').click();
  assert.equal(ui.links[1].download, 'message-release-17.txt');
  assert.equal(await ui.blobs[1].text(), ui.data.message_en);
});

test('denied download creates no file and denied reload clears stale controls', async () => {
  const ui = setup();
  await ui.panel.children[0].click();
  ui.fail();
  await ui.button('Pobierz: Instrukcja EN').click();
  assert.equal(ui.links.length, 0);
  assert.equal(ui.errors.length, 1);
  await ui.panel.children[0].click();
  assert.equal(ui.panel.children[1].children.length, 0);
});

test('repeated clicks share the workbench busy guard', async () => {
  const ui = setup();
  await Promise.all([ui.panel.children[0].click(), ui.panel.children[0].click()]);
  assert.equal(ui.requests.length, 1);
});

test('helper loads before the build controller', () => {
  const html = fs.readFileSync('app/templates/organization-os/build.html', 'utf8');
  assert(html.indexOf('delivery-handoff.js') < html.indexOf('/build.js'));
  const controller = fs.readFileSync('app/static/organization-os/build.js', 'utf8');
  assert(controller.includes('window.DeliveryHandoff.create({run,request,act})'));
});

test('version-two summaries are displayed literally and revalidated for download', async () => {
  const ui = setup();
  ui.data.delivery_summary = {file_count: 4, source_bytes: 99, profile: 'python-web-v1', verified_http_examples: 1};
  ui.data.guides['DELIVERY-SUMMARY.md'] = '# <script>literal summary</script>';
  ui.data.guides['DELIVERY-SUMMARY.pl.md'] = '# Metryka wydania';
  await ui.panel.children[0].click();
  assert(ui.all().some(n => n.textContent?.includes('1 wybranych przykładów HTTP')));
  assert(ui.all().some(n => n.textContent === ui.data.guides['DELIVERY-SUMMARY.md']));
  await ui.button('Pobierz: Metryka wydania EN').click();
  assert.equal(ui.requests.length, 2);
  assert.equal(ui.links[0].download, 'DELIVERY-SUMMARY.md');
  assert.equal(await ui.blobs[0].text(), ui.data.guides['DELIVERY-SUMMARY.md']);
  ui.fail();
  await ui.button('Pobierz: Metryka wydania PL').click();
  assert.equal(ui.links.length, 1);
});

test('no selected examples is not shown as zero tests or full coverage', async () => {
  const ui = setup();
  ui.data.delivery_summary = {file_count: 4, source_bytes: 99, profile: 'python-web-v1', verified_http_examples: null};
  await ui.panel.children[0].click();
  assert(ui.all().some(n => n.textContent?.startsWith('Bez osobnego planu przykładów HTTP')));
});
