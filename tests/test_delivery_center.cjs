// Lightweight controller tests: mocked DOM/fetch, no browser, GPU or server.
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const html = fs.readFileSync("app/templates/organization-os/index.html", "utf8");
const source = fs.readFileSync("app/static/organization-os/delivery-center.js", "utf8");
const pending = { id: 8, worker_id: "builder", result_checksum: "a".repeat(64), result_content: "<script>never execute</script>" };
const tick = async () => { for (let i = 0; i < 8; i++) await new Promise(setImmediate); };

function setup(responder = () => undefined) {
  const nodes = new Map();
  class Element {
    constructor(tag, id = "") {
      this.tag = tag; this.id = id; this.value = ""; this.checked = false;
      this.children = []; this.listeners = {}; this.hidden = false; this.disabled = false;
      this.classList = { toggle() {} }; this.files = []; this.textContent = "";
    }
    addEventListener(name, fn) { (this.listeners[name] ||= []).push(fn); }
    emit(name, extra = {}) { for (const fn of this.listeners[name] || []) fn({ preventDefault() {}, ...extra }); }
    append(...items) { this.children.push(...items); }
    replaceChildren(...items) { this.children = items; }
    focus() {}
    click() { this.emit("click"); }
    remove() {}
    showModal() { this.open = true; }
    close() { this.open = false; this.emit("close"); }
    querySelectorAll() { return [...nodes.values()].filter((n) => ["input", "textarea", "button"].includes(n.tag)); }
    reset() {
      const groups = {
        "delivery-load": ["token", "task"], "delivery-upload": ["purpose", "file"],
        "delivery-review": ["reason", "evidence", "confirm"],
      };
      for (const key of groups[this.id] || []) {
        const input = nodes.get(`delivery-${key}`);
        input.value = ""; input.checked = false; input.files = [];
      }
    }
  }
  for (const match of html.matchAll(/<(\w+)[^>]*\bid="([^"]+)"/g)) nodes.set(match[2], new Element(match[1], match[2]));
  const calls = [];
  const document = new Element("document");
  document.body = new Element("body");
  document.getElementById = (id) => nodes.get(id);
  document.createElement = (tag) => new Element(tag);
  document.dispatchEvent = (event) => document.emit(event.type);
  const window = new Element("window");
  const fetch = async (url, options) => {
    calls.push({ url, options });
    const custom = await responder(url, options);
    const status = custom?.status ?? 200;
    const data = custom?.data ?? (url.endsWith("/review") ? pending : { packages: [], next_cursor: null });
    return { ok: status < 400, status, json: async () => data, blob: async () => new Blob(["zip"]) };
  };
  vm.runInNewContext(source, { document, window, fetch, AbortController, DOMException,
    Event, Blob, URL, setTimeout, clearTimeout });
  const get = (id) => nodes.get(`delivery-${id}`);
  function open() { nodes.get("open-delivery-center").click(); }
  function load(task = "5") {
    get("token").value = "owner-secret";
    get("task").value = task;
    get("load").emit("submit");
  }
  function decide(value = "accept") {
    get("reason").value = "Sprawdzono kryteria";
    get("evidence").value = "tests/report.txt\nPrzegląd ręczny";
    get("confirm").checked = true;
    get("review").emit("submit", { submitter: { value } });
  }
  return { get, calls, open, load, decide, document };
}

test("selected plan gate explains refusal literally instead of a generic conflict", async () => {
  const ui = setup((url, options) => options.method === 'POST' ? {
    status: 409, data: {detail: 'Plan HTTP #21 wymaga kontroli. <script>nie wykonuj</script>'},
  } : undefined);
  ui.open(); ui.load(); await tick(); ui.decide(); await tick();
  assert.equal(ui.get('status').textContent, 'Plan HTTP #21 wymaga kontroli. <script>nie wykonuj</script>');
  assert.equal(ui.get('review').hidden, true);
  assert.equal(ui.calls.filter(c => c.options.method === 'POST').length, 1);
});

test("loads a specific result as text and submits exact attempt/checksum once", async () => {
  const ui = setup(); ui.open(); ui.load(); await tick();
  assert.equal(ui.get("body").hidden, false);
  assert.equal(ui.get("result").textContent, pending.result_content);
  assert.equal(ui.get("review").hidden, false);
  ui.decide(); ui.decide(); await tick();
  const writes = ui.calls.filter((c) => c.options.method === "POST");
  assert.equal(writes.length, 1);
  assert.equal(writes[0].url, "/api/tasks/5/review");
  const body = JSON.parse(writes[0].options.body);
  assert.equal(body.attempt_id, 8); assert.equal(body.result_checksum, pending.result_checksum);
  assert.equal(body.accepted, true); assert.equal(body.evidence.length, 2);
  assert.equal(ui.get("review").hidden, true);
  assert.equal(writes[0].options.headers.Authorization, "Bearer owner-secret");
  assert.equal(writes[0].options.redirect, "error");
});

test("closing dialog clears credentials, results, files and aborts pending requests", async () => {
  let release;
  const ui = setup(() => new Promise((resolve) => { release = resolve; }));
  ui.open(); ui.load(); await tick();
  ui.get("close").click();
  assert.equal(ui.get("token").value, "");
  assert.equal(ui.calls[0].options.signal.aborted, true);
  release(); await tick();
  assert.equal(ui.get("body").hidden, true);
  assert.equal(ui.get("result").textContent, "");
});

test("unauthorized response forgets token and hides private data", async () => {
  const ui = setup(() => ({ status: 401 })); ui.open(); ui.load(); await tick();
  assert.equal(ui.get("token").value, "");
  assert.equal(ui.get("body").hidden, true);
  assert.match(ui.get("status").textContent, /token/);
});

test("missing pending review allows package management but not acceptance", async () => {
  const ui = setup((url) => url.endsWith("/review") ? { status: 409 } : undefined);
  ui.open(); ui.load(); await tick();
  assert.equal(ui.get("body").hidden, false);
  assert.equal(ui.get("review").hidden, true);
  ui.decide(); await tick();
  assert.equal(ui.calls.filter((c) => c.options.method === "POST").length, 0);
});

test("stale decision requires explicit reload, never automatically retried", async () => {
  const ui = setup((url, options) => options.method === "POST" ? { status: 409 } : undefined);
  ui.open(); ui.load(); await tick(); ui.decide(); await tick();
  assert.equal(ui.get("review").hidden, true);
  assert.match(ui.get("status").textContent, /ponownie/);
  ui.decide(); await tick();
  assert.equal(ui.calls.filter((c) => c.options.method === "POST").length, 1);
});

test("changing task clears previous review and packages before another request", async () => {
  const ui = setup(); ui.open(); ui.load(); await tick();
  ui.get("task").value = "99"; ui.get("task").emit("input");
  assert.equal(ui.get("body").hidden, true);
  assert.equal(ui.get("result").textContent, "");
  ui.decide(); await tick();
  assert.equal(ui.calls.filter((c) => c.options.method === "POST").length, 0);
});

test("upload stores only files and purpose, never sends execution commands", async () => {
  const ui = setup((url, options) => options.method === "POST" ? { data: { artifact_id: 17 } } : undefined);
  ui.open(); ui.load(); await tick();
  ui.get("purpose").value = "Wersja strony";
  ui.get("file").files = [{ size: 100, text: async () => JSON.stringify({ files: { "index.html": "<h1>Hi</h1>" }, run: "rm -rf" }) }];
  ui.get("upload").emit("submit"); await tick();
  const writes = ui.calls.filter((c) => c.options.method === "POST");
  assert.equal(writes.length, 1);
  assert.deepEqual(JSON.parse(writes[0].options.body), { purpose: "Wersja strony", files: { "index.html": "<h1>Hi</h1>" } });
  assert.match(ui.get("status").textContent, /#17/);
  assert.equal(ui.get("file").files.length, 0);
});

test("malformed file does not write anything", async () => {
  const ui = setup(); ui.open(); ui.load(); await tick();
  ui.get("purpose").value = "Test";
  ui.get("file").files = [{ size: 4, text: async () => "bad!" }];
  ui.get("upload").emit("submit"); await tick();
  assert.match(ui.get("status").textContent, /JSON/);
  assert.equal(ui.calls.filter((c) => c.options.method === "POST").length, 0);
});
