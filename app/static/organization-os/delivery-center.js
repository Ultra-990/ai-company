/* Owner credentials live only in this dialog. No source HTML is interpreted. */
(() => {
  "use strict";
  const $ = (id) => document.getElementById(id);
  const dialog = $("delivery-center");
  let epoch = 0;
  let controller = new AbortController();
  let token = "";
  let taskId = null;
  let review = null;
  let cursor = null;
  let busy = false;

  function message(text, error = false) {
    $("delivery-status").textContent = text;
    $("delivery-status").classList.toggle("is-error", error);
  }

  function reset(clearCredentials = false) {
    epoch += 1;
    controller.abort();
    controller = new AbortController();
    token = "";
    taskId = null;
    review = null;
    cursor = null;
    busy = false;
    dialog.querySelectorAll("input, textarea, button").forEach((el) => { el.disabled = false; });
    $("delivery-body").hidden = true;
    $("delivery-review").hidden = true;
    $("delivery-more").hidden = true;
    $("delivery-packages").replaceChildren();
    $("delivery-result").textContent = "";
    $("delivery-review-state").textContent = "";
    $("delivery-upload").reset();
    $("delivery-review").reset();
    if (clearCredentials) $("delivery-load").reset();
  }

  function checkpoint(ticket) {
    if (ticket !== epoch || !dialog.open) throw new DOMException("Panel zamknięty", "AbortError");
  }

  async function request(path, options = {}, blob = false) {
    const ticket = epoch;
    const local = new AbortController();
    const parent = controller.signal;
    const abort = () => local.abort();
    parent.addEventListener("abort", abort, { once: true });
    const timeout = setTimeout(abort, 15000);
    try {
      const response = await (window.OwnerSession?.fetch||fetch)(path, {
        ...options, cache: "no-store", credentials: "omit", redirect: "error",
        headers: { Authorization: `Bearer ${token}`, ...(options.body ? { "Content-Type": "application/json" } : {}) },
        signal: local.signal,
      });
      checkpoint(ticket);
      if (!response.ok) {
        const messages = {
          401: "Brak lub nieprawidłowy token właściciela.",
          403: "Ta operacja wymaga roli właściciela.",
          404: "Nie znaleziono zadania lub paczki.",
          409: "Stan zmienił się lub naruszono integralność. Wczytaj zadanie ponownie.",
          413: "Plik JSON przekracza limit 8 MiB.",
          422: "Nieprawidłowe dane. Sprawdź ścieżki, rozmiary i wymagane pola.",
        };
        let detail;
        if (response.status === 409) {
          try { detail = (await response.json()).detail; } catch {}
          checkpoint(ticket);
        }
        const error = new Error(typeof detail === 'string' && detail.trim()
          ? detail.slice(0, 800)
          : messages[response.status] || `Operacja niedostępna (HTTP ${response.status}).`);
        error.status = response.status;
        throw error;
      }
      const data = blob ? await response.blob() : await response.json();
      checkpoint(ticket);
      return data;
    } finally {
      clearTimeout(timeout);
      parent.removeEventListener("abort", abort);
    }
  }

  async function act(action) {
    if (busy) return;
    busy = true;
    const ticket = epoch;
    const controls = [...dialog.querySelectorAll("input, textarea, button")].filter((el) => el.id !== "delivery-close");
    controls.forEach((el) => { el.disabled = true; });
    message("Łączenie z API…");
    try {
      await action(ticket);
    } catch (error) {
      if (ticket !== epoch) return;
      if ([401, 403].includes(error.status)) reset(true);
      message(error.name === "AbortError"
        ? "Upłynął czas oczekiwania. Przed ponowieniem zapisu sprawdź aktualny stan zadania."
        : error.message, true);
    } finally {
      if (ticket === epoch) {
        busy = false;
        controls.forEach((el) => { el.disabled = false; });
      }
    }
  }

  function element(tag, text, className) {
    const el = document.createElement(tag);
    if (text !== undefined) el.textContent = text;
    if (className) el.className = className;
    return el;
  }

  function showPackages(data, append = false) {
    const list = $("delivery-packages");
    if (!append) list.replaceChildren();
    if (!data.packages.length && !append) list.append(element("p", "To zadanie nie ma jeszcze paczek.", "delivery-note"));
    data.packages.forEach((pkg) => {
      const card = element("article", undefined, "delivery-package");
      card.append(element("h4", `Wersja #${pkg.artifact_id} · ${pkg.file_count} plików`));
      card.append(element("p", pkg.purpose));
      card.append(element("small", `${new Date(pkg.created_at).toLocaleString("pl-PL")} · ${pkg.total_bytes} B · nieuruchomiona`));
      const detail = element("details");
      detail.append(element("summary", "Pliki i suma kontrolna"));
      detail.append(element("code", pkg.checksum));
      const files = element("ul");
      pkg.files.forEach((file) => files.append(element("li", `${file.path} · ${file.size_bytes} B`)));
      detail.append(files);
      card.append(detail);
      const download = element("button", "↓ Pobierz ZIP");
      download.type = "button";
      download.addEventListener("click", () => act(async () => {
        const blob = await request(`/api/tasks/${taskId}/workspace-packages/${pkg.artifact_id}/download`, {}, true);
        const url = URL.createObjectURL(blob);
        const anchor = element("a");
        anchor.href = url;
        anchor.download = `task-${taskId}-package-${pkg.artifact_id}.zip`;
        anchor.hidden = true;
        document.body.append(anchor);
        anchor.click();
        anchor.remove();
        setTimeout(() => URL.revokeObjectURL(url), 1000);
        message("Pobrano ZIP. Nie uruchamiaj niesprawdzonego kodu na hoście wynajmu.");
      }));
      card.append(download);
      list.append(card);
    });
    cursor = data.next_cursor;
    $("delivery-more").hidden = cursor === null;
  }

  function showReview(data) {
    review = data;
    $("delivery-review").reset();
    $("delivery-review").hidden = !data;
    $("delivery-result").textContent = data?.result_content || "";
    $("delivery-review-state").textContent = data
      ? `Próba #${data.id} · wykonawca: ${data.worker_id}\nSHA-256: ${data.result_checksum}`
      : "To zadanie nie ma wyniku oczekującego na odbiór.";
  }

  $("open-delivery-center").addEventListener("click", () => {
    reset(true);
    message(window.OwnerSession?.active?"Wybierz ID zadania. Korzystasz ze wspólnej sesji właściciela.":"Podaj ID zadania i token lub zaloguj właściciela w górnym pasku.");
    dialog.showModal();
    $(window.OwnerSession?.active?"delivery-task":"delivery-token").focus();
  });
  $("delivery-close").addEventListener("click", () => dialog.close());
  dialog.addEventListener("close", () => reset(true));
  dialog.addEventListener("cancel", () => reset(true));
  window.addEventListener("pagehide", () => { reset(true); dialog.close(); });
  for (const id of ["delivery-token", "delivery-task"]) {
    $(id).addEventListener("input", () => { reset(); message("Wczytaj zadanie z nowymi danymi dostępu."); });
  }

  $("delivery-load").addEventListener("submit", (event) => {
    event.preventDefault();
    if (busy) return;
    const id = Number($("delivery-task").value);
    if (!Number.isSafeInteger(id) || id < 1) { message("Podaj poprawne ID zadania.", true); return; }
    reset();
    token = $("delivery-token").value.trim();
    taskId = id;
    act(async () => {
      const packages = await request(`/api/tasks/${id}/workspace-packages`);
      let pending;
      try { pending = await request(`/api/tasks/${id}/review`); }
      catch (error) { if (error.status !== 409) throw error; }
      showPackages(packages);
      showReview(pending);
      $("delivery-body").hidden = false;
      message(`Zadanie #${id} wczytane. Dane odświeżysz przyciskiem „Wczytaj zadanie”.`);
    });
  });

  $("delivery-more").addEventListener("click", () => act(async () => {
    showPackages(await request(`/api/tasks/${taskId}/workspace-packages?before=${cursor}`), true);
    message("Wczytano starsze paczki.");
  }));

  $("delivery-upload").addEventListener("submit", (event) => {
    event.preventDefault();
    if (!taskId || busy) return;
    const file = $("delivery-file").files[0];
    const purpose = $("delivery-purpose").value.trim();
    if (!file || !purpose) return;
    act(async (ticket) => {
      if (file.size > 8 * 1024 * 1024) throw new Error("Plik JSON przekracza 8 MiB.");
      const text = await file.text();
      checkpoint(ticket);
      let payload;
      try { payload = JSON.parse(text); }
      catch { throw new Error("Plik nie jest poprawnym JSON-em."); }
      if (!payload || typeof payload.files !== "object" || Array.isArray(payload.files) || payload.files === null) {
        throw new Error("JSON musi zawierać mapę files: ścieżka → treść tekstowa.");
      }
      const saved = await request(`/api/tasks/${taskId}/workspace-packages`, {
        method: "POST", body: JSON.stringify({ purpose, files: payload.files }),
      });
      $("delivery-upload").reset();
      try { showPackages(await request(`/api/tasks/${taskId}/workspace-packages`)); }
      catch (error) {
        checkpoint(ticket);
        if ([401, 403].includes(error.status)) throw error;
        message(`Paczka #${saved.artifact_id} zapisana, ale lista nie została odświeżona. Wczytaj zadanie, nie zapisuj ponownie.`, true);
        return;
      }
      message(`Zapisano paczkę #${saved.artifact_id}. Kod nie został uruchomiony ani odebrany.`);
    });
  });

  $("delivery-review").addEventListener("submit", (event) => {
    event.preventDefault();
    if (!review || !taskId || busy || !$("delivery-confirm").checked) return;
    const accepted = event.submitter?.value === "accept";
    if (!["accept", "reject"].includes(event.submitter?.value)) return;
    const reason = $("delivery-reason").value.trim();
    const evidence = $("delivery-evidence").value.split(/\r?\n/).map((line) => line.trim()).filter(Boolean);
    if (!reason || !evidence.length || evidence.length > 50 || evidence.some((line) => line.length > 4000)) {
      message("Podaj uzasadnienie i 1–50 dowodów, do 4000 znaków każdy.", true); return;
    }
    const decision = { attempt_id: review.id, result_checksum: review.result_checksum, accepted, reason, evidence };
    act(async (ticket) => {
      try {
        await request(`/api/tasks/${taskId}/review`, { method: "POST", body: JSON.stringify(decision) });
      } catch (error) {
        checkpoint(ticket);
        // Never re-submit an uncertain/stale decision without reloading the attempt.
        review = null;
        $("delivery-review").hidden = true;
        throw error;
      }
      showReview(null);
      message(accepted ? "Wynik odebrany. Zadanie ukończone." : "Wynik odrzucony. Zadanie zablokowane do poprawy; niczego automatycznie nie uruchomiono.");
      document.dispatchEvent(new Event("organization-data-changed"));
    });
  });
})();
