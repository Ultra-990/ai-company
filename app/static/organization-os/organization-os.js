/* Persistent scene: one geometry pass per frame, no polling-driven DOM teardown. */
(() => {
  "use strict";
  const $ = (id) => document.getElementById(id);
  const workspace = $("workspace"), layer = $("windows-layer"), network = $("network"), lines = $("network-lines");
  const windows = new Map(), edges = new Map();
  let nodes = [], dependencies = [], alerts = [], nextMove = null;
  let frame = null, drag = null, fetching = false, refreshQueued = false;
  const mobile = window.matchMedia("(max-width: 720px)");
  const symbols = { compass:"◈", "code-2":"⌘", sparkles:"✦", blocks:"▦", palette:"◌", terminal:"›_", handshake:"↔", "shield-check":"◉", server:"▤", "chart-no-axes-combined":"↗", landmark:"▰", users:"◫" };
  const statusNames = { active:"Aktywny", planned:"Zaplanowany", blocked:"Zablokowany", completed:"Ukończony", paused:"Wstrzymany", at_risk:"Wymaga uwagi", archived:"Archiwalny" };
  const element = (tag, className, text) => {
    const el = document.createElement(tag); if (className) el.className = className;
    if (text !== undefined) el.textContent = text; return el;
  };
  const percent = (value) => `${Math.max(0, Math.min(100, Math.round(Number(value) || 0)))}%`;
  const progressLabel = node => node.measurement_state==='unmeasured'?'—':percent(node.progress);
  function button(label, className, symbol, action) {
    const el = element("button", className, symbol || label); el.type = "button";
    el.title = label; el.setAttribute("aria-label", label); el.addEventListener("click", action); return el;
  }
  function position(record, index) {
    record.el.style.left = index % 2 ? "68%" : "3%";
    record.el.style.top = `${28 + Math.floor(index / 2) * 250}px`;
    record.el.style.setProperty("--tilt", index % 2 ? "-7deg" : "7deg");
  }
  function focus(record, expanded = false) {
    windows.forEach((other) => {
      if (other !== record) { collapse(other); other.el.classList.remove("is-focused"); }
    });
    record.el.hidden = false;
    record.el.classList.remove("is-minimized");
    record.el.classList.add("is-focused");
    if (expanded) {
      rememberPosition(record);
      record.el.classList.remove("is-maximized");
      record.el.classList.add("is-open");
      if (!mobile.matches) {
        record.el.style.left = `${Math.max(12, (workspace.clientWidth - Math.min(650, workspace.clientWidth * .9)) / 2)}px`;
        // Bring the selected window to the visible part of the scene.
        record.el.style.top = `${Math.max(20, Math.min(workspace.clientHeight - 480, -workspace.getBoundingClientRect().top + 100))}px`;
      }
    }
    renderDock(); schedule();
  }
  function rememberPosition(record) {
    if (!record.home) record.home = {left:record.el.style.left, top:record.el.style.top};
  }
  function collapse(record) {
    record.el.classList.remove("is-open", "is-maximized");
    if (record.home) {
      record.el.style.left = record.home.left; record.el.style.top = record.home.top; record.home = null;
    }
  }
  function renderDock() {
    const dock = $("window-dock"); dock.replaceChildren();
    windows.forEach((record) => {
      if (record.el.hidden || record.el.classList.contains("is-minimized")) {
        dock.append(button(`Przywróć ${record.node.name}`, "", record.node.name, () => focus(record, true)));
      }
    });
  }
  function createWindow(node, index) {
    const record = { node, signature:"", el:element("article", "os-window") };
    const el = record.el; el.dataset.nodeKey = node.key; position(record, index);
    const bar = element("header", "window-bar");
    record.icon = element("span", "window-icon"); record.title = element("span", "window-title");
    const controls = element("div", "window-controls");
    controls.append(
      button("Powiadomienia działu", "window-control window-control--notification", "♧", () => showNotifications(record.node)),
      button("Minimalizuj", "window-control window-control--minimize", "−", () => {
        el.classList.toggle("is-minimized"); collapse(record); renderDock(); schedule();
      }),
      button("Maksymalizuj / przywróć", "window-control", "□", () => {
        const was = el.classList.contains("is-maximized"); focus(record);
        if (was) collapse(record);
        else { rememberPosition(record); el.classList.remove("is-open"); el.classList.add("is-maximized"); }
        schedule();
      }),
      button("Zamknij okno", "window-control window-control--close", "×", () => { el.hidden = true; renderDock(); schedule(); }),
    );
    // Code-native bell: no external icon font or raster asset.
    controls.firstChild.textContent = "🔔";
    bar.append(record.icon, record.title, controls);
    const content = element("div", "window-content");
    record.status = element("span", "window-index"); record.heading = element("h2");
    record.description = element("p", "window-summary");
    const progress = element("div", "window-progress"), track = element("div", "window-progress__bar");
    record.fill = element("i"); record.progress = element("span"); track.append(record.fill); progress.append(track, record.progress);
    record.details = element("div", "window-details");
    content.append(record.status, record.heading, record.description, progress,
      button("Otwórz szczegóły działu", "window-open", "Otwórz dział ↗", () => focus(record, true)), record.details);
    el.append(bar, content);
    el.addEventListener("pointerdown", (event) => {
      if (!event.target.closest("button")) {
        windows.forEach((other) => other.el.classList.toggle("is-focused", other === record)); schedule();
      }
    });
    bar.addEventListener("dblclick", (event) => { if (!event.target.closest("button")) focus(record, true); });
    bar.addEventListener("pointerdown", (event) => {
      if (event.button !== 0 || event.target.closest("button") || mobile.matches || el.classList.contains("is-maximized")) return;
      // Remove perspective before measuring; pointer offsets then use the same coordinate space.
      el.classList.add("is-dragging");
      const bounds = workspace.getBoundingClientRect(), rect = el.getBoundingClientRect();
      drag = { record, pointer:event.pointerId, bounds, dx:event.clientX - rect.left, dy:event.clientY - rect.top,
        width:rect.width, height:rect.height, x:rect.left-bounds.left, y:rect.top-bounds.top, dirty:false };
      bar.setPointerCapture(event.pointerId);
    });
    bar.addEventListener("pointermove", (event) => {
      if (!drag || drag.record !== record || event.pointerId !== drag.pointer) return;
      drag.x = Math.max(8, Math.min(workspace.clientWidth-drag.width-8, event.clientX-drag.bounds.left-drag.dx));
      drag.y = Math.max(8, Math.min(workspace.clientHeight-drag.height-8, event.clientY-drag.bounds.top-drag.dy));
      drag.dirty = true; schedule();
    });
    const end = () => {
      if (drag?.record === record) {
        applyDrag(); drag = null; el.classList.remove("is-dragging"); schedule();
      }
    };
    bar.addEventListener("pointerup", end); bar.addEventListener("pointercancel", end); bar.addEventListener("lostpointercapture", end);
    return record;
  }
  function updateWindow(record, node) {
    record.node = node;
    const signature = JSON.stringify(node);
    if (record.signature === signature) return false;
    record.signature = signature;
    record.el.style.setProperty("--node-color", /^#[0-9a-f]{6}$/i.test(node.color || "") ? node.color : "#72b6db");
    record.icon.textContent = symbols[node.icon] || "◈";
    record.title.textContent = record.heading.textContent = node.name;
    record.status.textContent = `${statusNames[node.status] || node.status} · waga ${node.weight}`;
    record.description.textContent = node.description || "Zakres działu rozwijamy przez projekty i mierzalne rezultaty.";
    record.fill.style.width = percent(node.progress);record.progress.textContent = progressLabel(node);
    record.progress.title=node.progress_note||'Postęp z przypisanych zadań';
    if(node.measurement_state==='unmeasured')record.status.textContent+=' · brak pomiaru';
    const details = [
      ["ZADANIA W CAŁEJ GAŁĘZI", `${node.subtree_task_count ?? node.task_count ?? 0} · blokady: ${node.subtree_blocked_task_count ?? node.blocked_task_count ?? 0}`],
      ["DO ODBIORU", String(node.awaiting_review_count || 0)], ["PROJEKTY", String(node.subtree_project_count ?? node.project_count ?? 0)],
      ["ODPOWIEDZIALNOŚĆ", node.manager_agent || "Nieprzypisany"],
      ["PODOBSZARY", (node.children || []).map((child) => `${child.name}: ${progressLabel(child)}`).join(" · ") || "Brak podobszarów."],
      ["ŹRÓDŁO POMIARU", node.progress_note||'Zadania przypisane przez projekt do działu.'],
    ];
    if(node.foundation){details.push(['ISTNIEJĄCE MATERIAŁY — DO ODBIORU',node.foundation.artifacts.map(a=>`${a.present?'Jest plik':'Brak pliku'}: ${a.reference}`).join('\n')],['CO ZBUDOWAĆ TERAZ',node.foundation.next_step],['KRYTERIA GOTOWOŚCI DZIAŁU',node.foundation.completion_criteria.join('\n')]);}
    record.details.replaceChildren(...details.map(([label, value]) => {
      const card = element("section", "detail-card"); card.append(element("small", "", label), element("p", "", value)); return card;
    }));
    return true;
  }
  function renderTree(tree) {
    nodes = (tree.nodes || []).find((node) => node.key === "ai-company")?.children || [];
    dependencies = tree.dependencies || [];
    const keep = new Set(nodes.map((node) => node.key));
    windows.forEach((record, key) => { if (!keep.has(key)) { record.el.remove(); windows.delete(key); } });
    nodes.forEach((node, index) => {
      let record = windows.get(node.key);
      if (!record) { record = createWindow(node, index); windows.set(node.key, record); layer.append(record.el); }
      updateWindow(record, node);
    });
    syncEdges(); renderDock(); schedule();
    $("brain-manager-count").textContent = `${nodes.length} działów`;
    $("brain-dependency-count").textContent = `${[...edges.keys()].filter((key) => key.startsWith("dependency:")).length} unikalnych zależności`;
  }
  function syncEdges() {
    const desired = new Map([["owner:brain", { from:$("owner-orb"), to:$("brain-orb"), kind:"owner-link" }]]);
    nodes.forEach((node) => desired.set(`manager:${node.key}`, { from:$("brain-orb"), to:windows.get(node.key).el, kind:"manager-link" }));
    dependencies.forEach((link) => {
      const from = windows.get(link.source_key)?.el, to = windows.get(link.target_key)?.el;
      if (from && to) desired.set(`dependency:${link.source_key}:${link.target_key}:${link.relation_type}`, { from, to, kind:"dependency-link" });
    });
    edges.forEach((edge, key) => { if (!desired.has(key)) { edge.line.remove(); edges.delete(key); } });
    desired.forEach((edge, key) => {
      if (edges.has(key)) return;
      const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
      line.setAttribute("class", edge.kind); lines.append(line); edges.set(key, { ...edge, line });
    });
  }
  function applyDrag() {
    if (!drag?.dirty) return;
    drag.record.el.style.left = `${drag.x}px`; drag.record.el.style.top = `${drag.y}px`; drag.dirty = false;
  }
  function schedule() {
    if (frame !== null || document.hidden) return;
    frame = requestAnimationFrame(() => { frame = null; applyDrag(); updateConnections(); });
  }
  function updateConnections() {
    if (mobile.matches) return;
    const bounds = workspace.getBoundingClientRect(), centers = new Map();
    // Batch ALL geometry reads before writing SVG attributes; each element read once.
    edges.forEach(({ from, to }) => [from, to].forEach((el) => {
      if (centers.has(el)) return;
      if (el.hidden) { centers.set(el, null); return; }
      const rect = el.getBoundingClientRect(); centers.set(el, { x:rect.left-bounds.left+rect.width/2, y:rect.top-bounds.top+rect.height/2 });
    }));
    network.setAttribute("viewBox", `0 0 ${bounds.width} ${bounds.height}`);
    edges.forEach(({ from, to, line }) => {
      const a = centers.get(from), b = centers.get(to);
      line.style.display = a && b ? "" : "none";
      if (a && b) {
        line.setAttribute("x1", a.x); line.setAttribute("y1", a.y); line.setAttribute("x2", b.x); line.setAttribute("y2", b.y);
      }
    });
  }
  function showNotifications(scope = null) {
    const dialog = element("dialog", "notification-drawer");
    dialog.setAttribute("aria-label", scope ? `Powiadomienia: ${scope.name}` : "Powiadomienia systemowe");
    dialog.append(button("Wróć do pulpitu", "panel-close", "← Pulpit", () => dialog.close()), element("h2", "", scope ? scope.name : "Powiadomienia"));
    const scoped = scope ? alerts.filter((alert) => alert.organization_unit_id === scope.id) : alerts;
    if (!scoped.length) dialog.append(element("p", "notification-empty", "Brak aktywnych powiadomień w tym zakresie."));
    scoped.forEach((alert) => {
      const item = element("article", `notification-item${["critical","blocker"].includes(alert.severity) ? " notification-item--critical" : ""}`);
      item.append(element("strong", "", alert.title), element("p", "", alert.message)); dialog.append(item);
    });
    document.body.append(dialog); dialog.addEventListener("close", () => dialog.remove()); dialog.showModal();
  }
  function overview(data) {
    $("scene-progress").textContent = percent(data.organization_progress);
    $("scene-review").textContent = String(data.awaiting_review_tasks || 0);
    $("owner-company-progress").textContent = `${percent(data.organization_progress)} z zadań · ${data.tracked_tasks || 0} w projektach · ${data.unassigned_tasks || 0} bez projektu. Nie jest to pełny audyt gotowości firmy.`;
    $("owner-alerts").textContent = `${data.active_alert_count || 0} aktywnych powiadomień`;
    $("notifications-count").textContent = String(data.active_alert_count || 0);
  }
  async function refresh() {
    if (document.hidden) return;
    if (fetching) { refreshQueued = true; return; }
    fetching = true;
    const abort = new AbortController(), timeout = setTimeout(() => abort.abort(), 10000);
    try {
      const results = await Promise.allSettled(["tree","overview","next-move","alerts?status=open"].map(async (route) => {
        const response = await fetch(`/api/organization-os/${route}`, { signal:abort.signal, cache:"no-store" });
        if (!response.ok) throw new Error("API unavailable"); return response.json();
      }));
      if (results[0].status === "fulfilled") renderTree(results[0].value);
      if (results[1].status === "fulfilled") overview(results[1].value);
      if (results[2].status === "fulfilled") { nextMove = results[2].value; $("owner-next-move").textContent = nextMove.title || "Brak pilnego ruchu"; }
      if (results[3].status === "fulfilled") alerts = results[3].value.alerts || [];
      const ok = results.every((result) => result.status === "fulfilled");
      $("system-health-label").textContent = ok ? "SYSTEM ONLINE" : "DANE NIEPEŁNE";
      $("last-sync").textContent = ok ? `Aktualizacja ${new Date().toLocaleTimeString("pl-PL")}` : "Błąd odświeżania · zachowano ostatni stan";
    } finally {
      clearTimeout(timeout); fetching = false;
      if (refreshQueued) { refreshQueued = false; refresh(); }
    }
  }
  for (const name of ["owner","brain"]) {
    const dialog = $(`${name}-menu`), orb = $(`${name}-orb`);
    // Native top layer plus reparenting removes the old sphere stacking-context bug.
    document.body.append(dialog);
    orb.addEventListener("click", () => { dialog.showModal(); orb.setAttribute("aria-expanded", "true"); });
    dialog.addEventListener("close", () => orb.setAttribute("aria-expanded", "false"));
  }
  document.querySelectorAll("[data-close-dialog]").forEach((el) => el.addEventListener("click", () => $(el.dataset.closeDialog).close()));
  document.querySelector('[data-owner-action="notifications"]').addEventListener("click", () => showNotifications());
  $("notifications-button").addEventListener("click", () => showNotifications());
  document.querySelector('[data-owner-action="overview"]').addEventListener("click", () => { $("owner-menu").close(); $("restore-layout").click(); });
  document.querySelector('[data-owner-action="next"]').addEventListener("click", () => {
    const task = nextMove?.target?.task_id;
    if (task) {
      $("open-delivery-center").click(); $("delivery-task").value = String(task);
    } else { $("owner-next-move").textContent = nextMove?.reason || "Brak zadania wymagającego działania."; }
  });
  $("open-delivery-center").addEventListener("click", () => $("owner-menu").close());
  $("owner-shortcut").addEventListener("click", () => $("owner-orb").click());
  $("restore-layout").addEventListener("click", () => {
    nodes.forEach((node, index) => { const r = windows.get(node.key); r.home = null; r.el.hidden = false; r.el.className = "os-window"; position(r, index); });
    renderDock(); schedule();
  });
  $("toggle-dependencies").addEventListener("click", (event) => {
    const hide = network.classList.toggle("hide-dependencies");
    event.currentTarget.setAttribute("aria-pressed", String(!hide)); event.currentTarget.textContent = `Zależności: ${hide ? "ukryte" : "widoczne"}`;
  });
  window.addEventListener("resize", schedule);
  window.addEventListener("scroll", () => { if (drag) { drag.bounds = workspace.getBoundingClientRect(); } }, { passive:true });
  document.addEventListener("organization-data-changed", refresh);
  document.addEventListener("visibilitychange", () => { if (!document.hidden) { refresh(); schedule(); } });
  setInterval(() => { if (!fetching) refresh(); }, 30000);
  refresh();
})();
