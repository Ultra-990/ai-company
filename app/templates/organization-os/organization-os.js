(() => {
  "use strict";

  const departments = [
    { id: "01", icon: "◈", title: "Strategia i zarządzanie", progress: 35, x: 5, y: 20, summary: "Wizja, cele, decyzje właściciela i model operacyjny." },
    { id: "02", icon: "▣", title: "Platforma techniczna", progress: 42, x: 68, y: 13, summary: "Backend, API, baza danych, architektura i integracje." },
    { id: "03", icon: "◉", title: "AI i automatyzacja", progress: 23, x: 74, y: 42, summary: "Orkiestrator, agenci, automatyzacje oraz rekomendacje." },
    { id: "04", icon: "▦", title: "Produkty webowe", progress: 31, x: 4, y: 58, summary: "Własne aplikacje, platformy oraz doświadczenia użytkownika." },
    { id: "05", icon: "⌁", title: "UX i marka", progress: 16, x: 13, y: 75, summary: "Projektowanie interfejsów, identyfikacja i język produktu." },
    { id: "06", icon: "◌", title: "Systemy i R&D", progress: 7, x: 74, y: 71, summary: "Badania, prototypy i strategiczne linie rozwoju." },
    { id: "07", icon: "↗", title: "Usługi dla klientów", progress: 12, x: 39, y: 81, summary: "Usługi backendowe, AI, automatyzacje i projekty komercyjne." },
    { id: "08", icon: "⬡", title: "Jakość i bezpieczeństwo", progress: 28, x: 76, y: 27, summary: "Testy, jakość, bezpieczeństwo oraz niezależna weryfikacja." },
    { id: "09", icon: "◫", title: "Operacje i infrastruktura", progress: 38, x: 55, y: 7, summary: "Środowiska, wdrożenia, monitoring i niezawodność." },
    { id: "10", icon: "⌁", title: "Biznes i sprzedaż", progress: 9, x: 6, y: 40, summary: "Klienci, sprzedaż, partnerstwa i kanały przychodów." },
    { id: "11", icon: "¤", title: "Finanse i prawo", progress: 5, x: 49, y: 75, summary: "Przychody, koszty, formalności oraz zgodność prawna." },
    { id: "12", icon: "▤", title: "Wiedza i ludzie", progress: 18, x: 43, y: 16, summary: "Dokumentacja, procedury, kompetencje i pamięć firmy." }
  ];

  const state = {
    activeId: null,
    wheelIndex: 0,
    nextMove: "Zainicjuj fundament drzewa strukturalnego."
  };

  const workspace = document.getElementById("workspace");
  const layer = document.getElementById("windows-layer");
  const orbWrap = document.getElementById("ai-orb-wrap");
  const orb = document.getElementById("ai-orb");
  const ownerMenu = document.getElementById("owner-menu");
  const ownerNextMove = document.getElementById("owner-next-move");
  const networkLines = document.getElementById("network-lines");

  function escapeHtml(value) {
    return String(value)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;");
  }

  function renderWindows() {
    layer.innerHTML = departments.map((department) => `
      <article
        class="os-window"
        id="department-${department.id}"
        data-id="${department.id}"
        style="left:${department.x}%; top:${department.y}%"
      >
        <div class="window-bar">
          <span class="window-icon">${department.icon}</span>
          <span class="window-title">${department.id} / ${department.title.toUpperCase()}</span>

          <div class="window-controls">
            <button class="window-control" data-action="minimize" title="Minimalizuj" aria-label="Minimalizuj">−</button>
            <button class="window-control" data-action="maximize" title="Maksymalizuj" aria-label="Maksymalizuj">□</button>
            <button class="window-control window-control--close" data-action="close" title="Zamknij podgląd" aria-label="Zamknij">×</button>
          </div>
        </div>

        <div class="window-content">
          <span class="window-index">DZIAŁ ${department.id}</span>
          <h2>${department.title}</h2>
          <p class="window-summary">${department.summary}</p>

          <div class="window-progress">
            <div class="window-progress__bar"><i style="width:${department.progress}%"></i></div>
            <span>${department.progress}%</span>
          </div>

          <div class="window-details">
            <div class="detail-card">
              <small>STATUS STRUKTURALNY</small>
              <strong>${department.progress < 15 ? "Inicjalizacja" : "W realizacji"}</strong>
            </div>

            <div class="detail-card">
              <small>NASTĘPNY RUCH</small>
              <p>${department.id === "02" ? escapeHtml(state.nextMove) : "Wybierz węzeł w drzewie i przypisz kryteria odbioru."}</p>
            </div>

            <div class="detail-card">
              <small>MODEL POSTĘPU</small>
              <p>Ważona agregacja statusów dzieci oraz dowodów wykonania.</p>
            </div>

            <div class="detail-card">
              <small>DANE</small>
              <p>Widok gotowy do połączenia z API drzewa organizacyjnego.</p>
            </div>
          </div>
        </div>
      </article>
    `).join("");

    drawNetwork();
    bindWindowEvents();
  }

  function drawNetwork() {
    const centerX = 500;
    const centerY = 350;

    networkLines.innerHTML = departments.map((department) => {
      const x = department.x * 10 + 120;
      const y = department.y * 7 + 70;
      return `<line data-line-id="${department.id}" x1="${centerX}" y1="${centerY}" x2="${x}" y2="${y}"></line>`;
    }).join("");
  }

  function bindWindowEvents() {
    document.querySelectorAll(".os-window").forEach((windowElement) => {
      windowElement.addEventListener("mouseenter", () => {
        if (!windowElement.classList.contains("is-open")) {
          windowElement.classList.add("is-preview");
        }
      });

      windowElement.addEventListener("mouseleave", () => {
        if (!windowElement.classList.contains("is-open")) {
          windowElement.classList.remove("is-preview");
        }
      });

      windowElement.addEventListener("click", (event) => {
        const action = event.target.closest("[data-action]")?.dataset.action;

        if (action) {
          event.stopPropagation();
          handleWindowAction(windowElement, action);
          return;
        }

        if (!windowElement.classList.contains("is-open")) {
          openWindow(windowElement.dataset.id);
        }
      });

      enableDragging(windowElement);
    });
  }

  function handleWindowAction(windowElement, action) {
    const id = windowElement.dataset.id;

    if (action === "maximize") {
      openWindow(id);
      windowElement.classList.toggle("is-maximized");
      positionOrbForWindow(windowElement);
      return;
    }

    if (action === "minimize" || action === "close") {
      closeWindow(id);
    }
  }

  function openWindow(id) {
    document.querySelectorAll(".os-window").forEach((item) => {
      if (item.dataset.id !== id) {
        item.classList.remove("is-open", "is-maximized", "is-preview");
      }
    });

    state.activeId = id;

    const selected = document.getElementById(`department-${id}`);
    selected.classList.add("is-open");
    selected.classList.remove("is-preview");

    document.querySelectorAll("[data-line-id]").forEach((line) => {
      line.classList.toggle("is-active", line.dataset.lineId === id);
    });

    positionOrbForWindow(selected);
  }

  function closeWindow(id) {
    const selected = document.getElementById(`department-${id}`);
    selected.classList.remove("is-open", "is-maximized", "is-preview");

    state.activeId = null;
    orbWrap.style.left = "50%";
    orbWrap.style.top = "50%";

    document.querySelectorAll("[data-line-id]").forEach((line) => {
      line.classList.remove("is-active");
    });
  }

  function positionOrbForWindow(windowElement) {
    const rect = windowElement.getBoundingClientRect();
    const width = window.innerWidth;
    const height = window.innerHeight;

    const windowCenterX = rect.left + rect.width / 2;
    const windowCenterY = rect.top + rect.height / 2;

    const left = windowCenterX > width / 2 ? "18%" : "82%";
    const top = windowCenterY > height / 2 ? "22%" : "78%";

    orbWrap.style.left = left;
    orbWrap.style.top = top;
  }

  function enableDragging(element) {
    let dragging = false;
    let startX = 0;
    let startY = 0;
    let initialLeft = 0;
    let initialTop = 0;

    element.addEventListener("pointerdown", (event) => {
      if (!element.classList.contains("is-open")) return;
      if (event.target.closest("button")) return;

      dragging = true;
      startX = event.clientX;
      startY = event.clientY;

      const rect = element.getBoundingClientRect();
      initialLeft = rect.left;
      initialTop = rect.top;

      element.setPointerCapture(event.pointerId);
      element.style.transition = "none";
    });

    element.addEventListener("pointermove", (event) => {
      if (!dragging) return;

      const maxLeft = window.innerWidth - element.offsetWidth - 12;
      const maxTop = window.innerHeight - element.offsetHeight - 20;

      const left = Math.max(12, Math.min(maxLeft, initialLeft + event.clientX - startX));
      const top = Math.max(55, Math.min(maxTop, initialTop + event.clientY - startY));

      element.style.left = `${left}px`;
      element.style.top = `${top}px`;
      positionOrbForWindow(element);
    });

    element.addEventListener("pointerup", () => {
      if (!dragging) return;
      dragging = false;
      element.style.transition = "";
    });
  }

  function activateByWheel(direction) {
    state.wheelIndex =
      (state.wheelIndex + direction + departments.length) % departments.length;

    const department = departments[state.wheelIndex];
    openWindow(department.id);
  }

  let wheelLocked = false;

  workspace.addEventListener("wheel", (event) => {
    event.preventDefault();

    if (wheelLocked) return;
    wheelLocked = true;

    activateByWheel(event.deltaY > 0 ? 1 : -1);

    window.setTimeout(() => {
      wheelLocked = false;
    }, 550);
  }, { passive: false });

  orb.addEventListener("click", () => {
    const visible = ownerMenu.classList.toggle("is-visible");
    ownerMenu.setAttribute("aria-hidden", String(!visible));
    orb.setAttribute("aria-expanded", String(visible));
  });

  document.addEventListener("click", (event) => {
    if (!event.target.closest(".ai-orb-wrap")) {
      ownerMenu.classList.remove("is-visible");
      ownerMenu.setAttribute("aria-hidden", "true");
      orb.setAttribute("aria-expanded", "false");
    }
  });

  document.querySelectorAll("[data-owner-action]").forEach((button) => {
    button.addEventListener("click", () => {
      const action = button.dataset.ownerAction;

      if (action === "overview") {
        document.querySelectorAll(".os-window").forEach((item) => {
          item.classList.remove("is-open", "is-maximized");
        });

        state.activeId = null;
        orbWrap.style.left = "50%";
        orbWrap.style.top = "50%";
        ownerMenu.classList.remove("is-visible");
      }

      if (action === "next") {
        openWindow("02");
        ownerMenu.classList.remove("is-visible");
      }
    });
  });

  async function loadNextMove() {
    try {
      const response = await fetch("/api/next-move");
      if (!response.ok) return;

      const data = await response.json();

      state.nextMove =
        data.title ||
        data.task_title ||
        data.next_move?.title ||
        data.message ||
        state.nextMove;

      ownerNextMove.textContent = state.nextMove;

      const technologyWindow = document.getElementById("department-02");
      if (technologyWindow) {
        const nextMoveElement = technologyWindow.querySelector(
          ".detail-card:nth-child(2) p"
        );

        if (nextMoveElement) {
          nextMoveElement.textContent = state.nextMove;
        }
      }
    } catch {
      ownerNextMove.textContent = state.nextMove;
    }
  }

  renderWindows();
  ownerNextMove.textContent = state.nextMove;
  loadNextMove();

  window.addEventListener("resize", () => {
    drawNetwork();

    if (state.activeId) {
      const active = document.getElementById(`department-${state.activeId}`);
      if (active) positionOrbForWindow(active);
    }
  });
})();
