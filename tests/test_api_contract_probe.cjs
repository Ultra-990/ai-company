// Tiny DOM harness; no browser, HTTP connections or local models.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
function setup() {
  class Element {
    constructor(tag) {this.tag = tag; this.children = []; this.listeners = {}; this.value = '';}
    append(...items) {this.children.push(...items);}
    setAttribute(k, v) {this[k] = v;}
    replaceChildren(...items) {this.children = items;}
    addEventListener(k, v) {this.listeners[k] = v;}
    click() {return this.listeners.click?.();}
    set innerHTML(value) {throw Error('Unsafe rendering');}
  }
  const events = {}, window = {addEventListener: (k, v) => {events[k] = v;}}, calls = [];
  let fail = false, intercept;
  const result = {outcome: 'failed', limitation: 'Nie uruchomiono aplikacji.',
    checks: [{name: 'label', code: 'type_mismatch', outcome: 'failed', pointer: '/data/name', hint: '<script>inert</script>'}]};
  vm.runInNewContext(fs.readFileSync('app/static/organization-os/api-contract-probe.js', 'utf8'),
    {window, document: {createElement: tag => new Element(tag), getElementById: () => null}, TextEncoder, AbortController});
  const panel = window.ApiContractProbe.create({request: async (payload, signal) => {
    calls.push({payload, signal}); if (fail) throw Error('Sesja zakończona');
    if (intercept) return intercept(); return result;
  }});
  const all = (root = panel) => [root, ...root.children.flatMap(x => all(x))];
  const button = text => all().find(x => x.tag === 'button' && x.textContent === text);
  return {all, button, calls, result, events, fail: () => {fail = true;}, intercept: fn => {intercept = fn;}};
}
test('explicit sample check sends fixture only and displays inert hints', async () => {
  const ui = setup(); assert.equal(ui.calls.length, 0);
  await ui.button('Wstaw przykład syntetyczny').click();
  assert.equal(ui.calls.length, 0);
  await ui.button('Sprawdź próbkę i powiązania').click();
  assert.equal(ui.calls.length, 1);
  assert.equal(JSON.parse(ui.calls[0].payload.response_text).data.items[0].total, 2576);
  assert(ui.all().some(x => x.textContent?.includes('<script>inert</script>')));
});
test('input changes clear outdated result and invalid binding JSON makes no request', async () => {
  const ui = setup(); await ui.button('Wstaw przykład syntetyczny').click();
  await ui.button('Sprawdź próbkę i powiązania').click();
  const inputs = ui.all().filter(x => x.tag === 'textarea');
  inputs[1].value = '{'; inputs[1].listeners.input();
  assert(!ui.all().some(x => x.textContent?.includes('<script>')));
  await ui.button('Sprawdź próbkę i powiązania').click();
  assert.equal(ui.calls.length, 1);
  assert(ui.all().some(x => x.textContent === 'Popraw JSON w polu powiązań.'));
});
test('duplicate clicks share one request and clearing discards late results', async () => {
  const ui = setup(); await ui.button('Wstaw przykład syntetyczny').click();
  let resolve; ui.intercept(() => new Promise(r => {resolve = r;}));
  const pending = ui.button('Sprawdź próbkę i powiązania').click();
  await ui.button('Sprawdź próbkę i powiązania').click();
  assert.equal(ui.calls.length, 1);
  await ui.button('Wyczyść próbkę i wynik').click();
  assert(ui.calls[0].signal.aborted); resolve(ui.result); await pending;
  assert(!ui.all().some(x => x.tag === 'h3'));
  assert(ui.all().filter(x => x.tag === 'textarea').every(x => x.value === ''));
});
test('page hide removes entered samples and rejection is not shown as success', async () => {
  const ui = setup(); await ui.button('Wstaw przykład syntetyczny').click(); ui.fail();
  await ui.button('Sprawdź próbkę i powiązania').click();
  assert(ui.all().some(x => x.textContent === 'Sesja zakończona'));
  ui.events.pagehide();
  assert(ui.all().filter(x => x.tag === 'textarea').every(x => x.value === ''));
});
