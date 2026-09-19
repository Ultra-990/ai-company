// Small in-memory DOM only. No browser, network, model or container.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

class Element {
  constructor(tag) { this.tag = tag; this.children = []; this.listeners = {}; this.value = ''; this.textContent = ''; }
  append(...nodes) { this.children.push(...nodes); }
  replaceChildren(...nodes) { this.children = nodes; }
  setAttribute(k, v) { this[k] = v; }
  addEventListener(name, fn) { this.listeners[name] = fn; }
  reportValidity() { return true; }
  set innerHTML(v) { throw Error('HTML injection forbidden'); }
}

function setup(enabled = false) {
  const calls = [], errors = [], starts = [], window = {};
  const matrix = {source_checksum: 'a'.repeat(64), scope_checksum: 'b'.repeat(64),
    criteria: [{id: 'c'.repeat(64), text: '<img src=x> Requirement'}]};
  const plans = [];
  let failing = false, pending;
  const request = async (url, options = {}) => {
    calls.push({url, options});
    if (options.method === 'POST') {
      if (failing) throw Error('Uncertain reply');
      const plan = {id: 21, checksum: 'd'.repeat(64), ...JSON.parse(options.body), execution_enabled: enabled};
      if (!plans.length) plans.push(plan);
      return plan;
    }
    return url.endsWith('/requirements') ? matrix : {plans, execution_enabled: enabled};
  };
  const act = fn => pending = Promise.resolve().then(fn).catch(e => errors.push(e.message));
  vm.runInNewContext(fs.readFileSync('app/static/organization-os/acceptance-plans.js', 'utf8'), {
    window, document: {createElement: tag => new Element(tag)}, crypto: {randomUUID: () => 'stable-uuid'},
  });
  const panel = window.AcceptancePlans.create({run: {task_id: 3, package_id: 7}, request, act, onStart: plan => starts.push(plan)});
  const all = (root = panel) => [root, ...root.children.flatMap(child => all(child))];
  const get = text => all().find(n => n.textContent === text);
  const load = () => panel.children[0].listeners.click();
  function add(value = '2576', field = 'total') {
    const inputs = all().filter(n => n.tag === 'input');
    [inputs[0].value, inputs[1].value, inputs[2].value, inputs[3].value, inputs[4].value] =
      ['<script>literal example</script>', '/api/estimate?hours=8&rate=322', '200', field, value];
    all().find(n => n.tag === 'select').value = matrix.criteria[0].id;
    all().find(n => n.tag === 'form').listeners.submit({preventDefault() {}});
  }
  const save = () => get('Zapisz niezmienny plan — bez uruchamiania').listeners.click();
  return {panel, calls, errors, starts, matrix, plans, all, get, load, add, save, setFail(v) { failing = v; }};
}

test('plans load on demand, render text and never offer execution while disabled', async () => {
  const ui = setup();
  assert.equal(ui.calls.length, 0);
  await ui.load();
  assert.equal(ui.calls.length, 2);
  assert(ui.get('<img src=x> Requirement'));
  ui.add();
  assert.equal(ui.calls.length, 2);
  await ui.save();
  assert.equal(ui.starts.length, 0);
  assert.equal(ui.plans.length, 1);
  assert.equal(ui.plans[0].source_checksum, ui.matrix.source_checksum);
  assert.equal(ui.plans[0].cases[0].expected, 2576);
  assert(ui.all().some(n => n.textContent.includes('<script>literal example</script>')));
  assert(!ui.get('Testuj i napraw z tym planem'));
  assert(ui.calls.every(c => !c.url.includes('application-quality') && !c.url.includes('package-runs')));
});

test('uncertain plan save retries exact immutable request, no edited expectation', async () => {
  const ui = setup(); await ui.load(); ui.add();
  ui.setFail(true); await ui.save();
  ui.add('330'); // editing cannot alter pending request
  ui.setFail(false); await ui.save();
  const writes = ui.calls.filter(c => c.options.method === 'POST');
  assert.equal(writes.length, 2);
  assert.equal(writes[0].options.body, writes[1].options.body);
  assert.equal(ui.plans[0].cases.length, 1);
  assert.equal(ui.errors.length, 1);
});

test('scalar validation, four-case bound and explicit delegation of selected plan', async () => {
  const ui = setup(true); await ui.load();
  ui.add('{"no":"objects"}');
  assert(ui.get('Zapisz niezmienny plan — bez uruchamiania').hidden);
  ui.add('1e999');
  assert(ui.get('Zapisz niezmienny plan — bez uruchamiania').hidden);
  for (let i = 0; i < 5; i++) ui.add(String(i));
  await ui.save();
  assert.equal(ui.plans[0].cases.length, 4);
  assert.equal(ui.starts.length, 0);
  ui.get('Testuj i napraw z tym planem').listeners.click();
  assert.equal(ui.starts[0].id, 21);
});

test('selected plan binds quality request and acceptance outcomes are distinct from unit tests', async () => {
  const ids = new Map(), calls = [], window = {confirm: () => true};
  const el = id => { if (!ids.has(id)) ids.set(id, new Element('div')); return ids.get(id); };
  const cycle = {id: 5, task_id: 3, state: 'passed', message: 'Examples checked', steps: [
    {kind: 'acceptance', id: 9, state: 'passed', package_id: 7, cases: [
      {title: '<script>test</script>', path: '/api/estimate', passed: true, json_field: 'total', expected: 2576, observed: 2576, reason: 'value_matches'}]}]};
  const request = async (url, options = {}) => {
    calls.push({url, options});
    return url === '/api/application-quality' && !options.method ? {cycles: [cycle]} : cycle;
  };
  let pending;
  vm.runInNewContext(fs.readFileSync('app/static/organization-os/application-quality.js', 'utf8'), {
    window, document: {getElementById: el, createElement: tag => new Element(tag)}, crypto: {randomUUID: () => 'stable-uuid'},
  });
  const ui = window.createApplicationQuality({request, act: fn => pending = fn(), message() {}, refresh: async () => {}});
  const binding = {task_id: 3, package_id: 7, package_checksum: 'a'.repeat(64)};
  const plan = {id: 21, checksum: 'b'.repeat(64), cases: [{}], execution_enabled: false};
  ui.start(binding, plan);
  assert.equal(calls.length, 0);
  ui.start(binding, {...plan, execution_enabled: true}); await pending;
  const body = JSON.parse(calls[0].options.body);
  assert.equal(body.acceptance_plan_id, 21);
  assert.equal(body.acceptance_plan_checksum, plan.checksum);
  const all = root => [root, ...root.children.flatMap(all)];
  assert(all(el('quality-history')).some(n => n.textContent.includes('Przykłady wymagań HTTP')));
  assert(all(el('quality-history')).some(n => n.textContent.includes('<script>test</script>')));
});

test('plan controls are integrated for selected packages without executing anything', () => {
  const html = fs.readFileSync('app/templates/organization-os/build.html', 'utf8');
  assert(html.indexOf('acceptance-plans.js') < html.indexOf('/build.js'));
  const source = fs.readFileSync('app/static/organization-os/build.js', 'utf8');
  assert(source.includes('window.AcceptancePlans.create({run,request,act,onStart:plan=>quality.start(run,plan)})'));
  assert(source.includes('package_checksum:p.checksum'));
});
