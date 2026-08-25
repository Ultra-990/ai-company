from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from app.core.config import load_settings
from app.services.project_progress import load_project_progress
from app.services.tasks import TaskRepository


router = APIRouter()



@router.get("/api/progress")
def get_progress() -> dict:
    """Zwraca aktualny postęp zadań zapisanych w lokalnej bazie SQLite."""
    repository = TaskRepository(load_settings().database.url)

    status_labels = {
        "pending": "Zaplanowany",
        "in_progress": "W trakcie",
        "completed": "Ukończony",
        "blocked": "Zablokowany",
        "cancelled": "Anulowany",
    }

    try:
        summary = repository.progress_summary()
        tasks = repository.list_recent(limit=100)

        serialized_tasks = [
            {
                "id": task.id,
                "title": task.title,
                "description": task.description,
                "status": task.status.value,
                "status_label": status_labels[task.status.value],
                "priority": task.priority.value,
                "assigned_agent": task.assigned_agent,
                "progress": task.progress,
                "updated_at": task.updated_at.isoformat(),
            }
            for task in tasks
        ]

        return {
            "total_progress": summary["total_progress"],
            "task_count": summary["task_count"],
            "counts": summary["counts"],
            "tasks": serialized_tasks,
            "tasks_source": "latest_100",
            "project_progress": load_project_progress(),
        }
    finally:
        repository.close()


@router.get("/progress", response_class=HTMLResponse)
def progress_page() -> str:
    return """
<!DOCTYPE html>
<html lang="pl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">

    <title>Mapa postępu — AI Company</title>

    <style>
        :root {
            --background: #07111f;
            --background-light: #0d1b2e;
            --panel: rgba(18, 35, 58, 0.86);
            --panel-hover: rgba(28, 51, 80, 0.96);
            --border: rgba(148, 163, 184, 0.20);
            --text: #edf5ff;
            --muted: #9cafc7;
            --green: #39df88;
            --blue: #4da3ff;
            --yellow: #ffd166;
            --red: #ff6678;
            --purple: #a78bfa;
            --shadow: 0 24px 70px rgba(0, 0, 0, 0.35);
        }

        * {
            box-sizing: border-box;
        }

        html {
            scroll-behavior: smooth;
        }

        body {
            min-height: 100vh;
            margin: 0;
            color: var(--text);
            font-family:
                Inter, ui-sans-serif, system-ui, -apple-system,
                BlinkMacSystemFont, "Segoe UI", sans-serif;

            background:
                radial-gradient(
                    circle at 10% 0%,
                    rgba(77, 163, 255, 0.22),
                    transparent 32%
                ),
                radial-gradient(
                    circle at 90% 15%,
                    rgba(167, 139, 250, 0.16),
                    transparent 30%
                ),
                linear-gradient(
                    135deg,
                    var(--background),
                    #0a1628 50%,
                    #101b31
                );
        }

        body::before {
            position: fixed;
            inset: 0;
            z-index: -1;
            pointer-events: none;
            content: "";
            opacity: 0.18;
            background-image:
                linear-gradient(
                    rgba(255,255,255,.03) 1px,
                    transparent 1px
                ),
                linear-gradient(
                    90deg,
                    rgba(255,255,255,.03) 1px,
                    transparent 1px
                );
            background-size: 42px 42px;
            mask-image: linear-gradient(to bottom, black, transparent);
        }

        .container {
            width: min(1180px, calc(100% - 32px));
            margin: 0 auto;
            padding: 48px 0 70px;
        }

        .hero {
            margin-bottom: 28px;
            animation: fadeUp 0.8s ease both;
        }

        .eyebrow {
            color: var(--blue);
            font-size: 0.78rem;
            font-weight: 800;
            letter-spacing: 0.18em;
            text-transform: uppercase;
        }

        h1 {
            margin: 10px 0 12px;
            font-size: clamp(2.2rem, 5vw, 4.4rem);
            line-height: 1;
            letter-spacing: -0.05em;
        }

        .subtitle {
            max-width: 760px;
            margin: 0;
            color: var(--muted);
            font-size: 1.08rem;
            line-height: 1.6;
        }

        .panel {
            padding: 25px;
            margin-bottom: 24px;
            border: 1px solid var(--border);
            border-radius: 24px;
            background: var(--panel);
            box-shadow: var(--shadow);
            backdrop-filter: blur(18px);
            animation: fadeUp 0.8s ease both;
        }

        .summary-top {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 20px;
            margin-bottom: 16px;
        }

        .summary-title {
            font-size: 1.15rem;
            font-weight: 800;
        }

        .summary-percent {
            color: var(--green);
            font-size: 1.45rem;
            font-weight: 900;
        }

        .progress-track {
            width: 100%;
            height: 14px;
            overflow: hidden;
            border-radius: 999px;
            background: rgba(148, 163, 184, 0.18);
        }

        .progress-fill {
            width: var(--progress);
            height: 100%;
            border-radius: inherit;
            background:
                linear-gradient(
                    90deg,
                    var(--green),
                    #80f2b0,
                    var(--blue)
                );
            box-shadow: 0 0 22px rgba(57, 223, 136, 0.55);
            transform-origin: left;
            animation: growProgress 1.4s cubic-bezier(.2,.8,.2,1) both;
        }

        .processes {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 18px;
        }

        .process {
            overflow: hidden;
            border: 1px solid var(--border);
            border-left: 4px solid var(--accent);
            border-radius: 18px;
            background: rgba(7, 17, 31, 0.62);
            transition:
                transform 0.3s ease,
                background 0.3s ease,
                box-shadow 0.3s ease;
            animation: fadeUp 0.7s ease both;
        }

        .process:hover {
            background: var(--panel-hover);
            box-shadow: 0 18px 42px rgba(0, 0, 0, 0.28);
            transform: translateY(-6px);
        }

        .process-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 15px;
            padding: 20px;
            cursor: pointer;
            user-select: none;
        }

        .process-name {
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .process-icon {
            display: grid;
            width: 43px;
            height: 43px;
            place-items: center;
            border-radius: 13px;
            background: rgba(255, 255, 255, 0.08);
            font-size: 1.35rem;
            transition: transform .3s ease;
        }

        .process:hover .process-icon {
            transform: rotate(-8deg) scale(1.1);
        }

        .process h2 {
            margin: 0 0 5px;
            font-size: 1.08rem;
        }

        .status {
            color: var(--accent);
            font-size: 0.78rem;
            font-weight: 800;
        }

        .status::before {
            display: inline-block;
            width: 8px;
            height: 8px;
            margin-right: 7px;
            content: "";
            border-radius: 50%;
            background: currentColor;
            box-shadow: 0 0 0 5px rgba(255, 255, 255, 0.05);
        }

        .process-percent {
            color: var(--accent);
            font-size: 1.05rem;
            font-weight: 900;
            white-space: nowrap;
        }

        .arrow {
            display: inline-block;
            margin-left: 7px;
            color: var(--muted);
            transition: transform .35s ease;
        }

        .process.open .arrow {
            transform: rotate(180deg);
        }

        .details-wrapper {
            display: grid;
            grid-template-rows: 0fr;
            transition: grid-template-rows .45s ease;
        }

        .process.open .details-wrapper {
            grid-template-rows: 1fr;
        }

        .details-hidden {
            min-height: 0;
            overflow: hidden;
        }

        .details {
            padding: 0 20px 21px;
        }

        .description {
            margin: 0 0 17px;
            color: var(--muted);
            font-size: 0.9rem;
            line-height: 1.55;
        }

        .small-progress {
            margin-bottom: 20px;
        }

        .small-progress-label {
            display: flex;
            justify-content: space-between;
            margin-bottom: 8px;
            color: var(--muted);
            font-size: 0.78rem;
        }

        .small-progress .progress-track {
            height: 8px;
        }

        .small-progress .progress-fill {
            background: var(--accent);
            box-shadow: 0 0 15px color-mix(
                in srgb,
                var(--accent) 60%,
                transparent
            );
        }

        .steps {
            display: grid;
            gap: 10px;
        }

        .step {
            padding: 13px;
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 12px;
            background: rgba(255, 255, 255, 0.045);
            animation: slideIn .45s ease both;
        }

        .step-line {
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .step-number {
            display: grid;
            width: 25px;
            height: 25px;
            flex: 0 0 25px;
            place-items: center;
            color: #07111f;
            border-radius: 50%;
            background: var(--step-color);
            font-size: 0.74rem;
            font-weight: 900;
        }

        .step-name {
            flex: 1;
            font-size: 0.88rem;
            font-weight: 750;
        }

        .step-status {
            color: var(--step-color);
            font-size: 0.72rem;
            font-weight: 850;
            text-align: right;
        }

        .step-description {
            margin: 8px 0 0 35px;
            color: var(--muted);
            font-size: 0.8rem;
            line-height: 1.45;
        }

        .legend {
            display: flex;
            flex-wrap: wrap;
            gap: 18px;
            color: var(--muted);
            font-size: 0.84rem;
        }

        .legend-item::before {
            display: inline-block;
            width: 10px;
            height: 10px;
            margin-right: 7px;
            content: "";
            border-radius: 50%;
            background: var(--legend-color);
        }

        @keyframes fadeUp {
            from {
                opacity: 0;
                transform: translateY(22px);
            }

            to {
                opacity: 1;
                transform: translateY(0);
            }
        }

        @keyframes slideIn {
            from {
                opacity: 0;
                transform: translateX(-12px);
            }

            to {
                opacity: 1;
                transform: translateX(0);
            }
        }

        @keyframes growProgress {
            from {
                transform: scaleX(0);
            }

            to {
                transform: scaleX(1);
            }
        }

        @media (max-width: 760px) {
            .container {
                width: min(100% - 20px, 600px);
                padding-top: 28px;
            }

            .panel {
                padding: 17px;
                border-radius: 18px;
            }

            .processes {
                grid-template-columns: 1fr;
            }

            .process-header {
                padding: 16px;
            }

            .details {
                padding: 0 16px 17px;
            }

            .process-percent {
                font-size: 0.85rem;
            }
        }

        @media (prefers-reduced-motion: reduce) {
            *,
            *::before,
            *::after {
                animation-duration: 0.01ms !important;
                transition-duration: 0.01ms !important;
            }
        }
    </style>
</head>

<body>
    <main class="container">
        <section class="hero">
            <div class="eyebrow">AI Company · Centrum dowodzenia</div>
            <h1>Mapa postępu systemu</h1>
            <p class="subtitle">
                Szczegółowy podgląd procesów, etapów działań i aktualnego
                statusu budowy organizacji.
            </p>
        </section>

        <section class="panel">
            <div class="summary-top">
                <span class="summary-title">Postęp zadań zapisanych w systemie</span>
                <span class="summary-percent" id="total-percent">0%</span>
            </div>

            <div class="progress-track">
                <div class="progress-fill" id="total-progress"
                     style="--progress: 0%">
                </div>
            </div>
        </section>

        <section class="panel">
            <div class="processes" id="processes"></div>
        </section>

        <section class="panel">
            <div class="legend">
                <span class="legend-item" style="--legend-color: var(--green)">
                    Ukończony
                </span>

                <span class="legend-item" style="--legend-color: var(--blue)">
                    W trakcie
                </span>

                <span class="legend-item" style="--legend-color: var(--yellow)">
                    Zaplanowany
                </span>

                <span class="legend-item" style="--legend-color: var(--red)">
                    Zablokowany
                </span>
            </div>
        </section>
    </main>

    <script>
        const processes = [
            {
                title: "Fundament FastAPI",
                icon: "⚙️",
                progress: 100,
                status: "Ukończony",
                color: "var(--green)",
                description:
                    "Podstawowa aplikacja, konfiguracja środowiska i endpoint zdrowia.",
                open: true,
                steps: [
                    [
                        "Struktura projektu",
                        "Ukończony",
                        "Utworzenie katalogów aplikacji i modułów."
                    ],
                    [
                        "Konfiguracja FastAPI",
                        "Ukończony",
                        "Uruchomienie głównej aplikacji API."
                    ],
                    [
                        "Baza SQLite",
                        "Ukończony",
                        "Przygotowanie lokalnej bazy danych."
                    ],
                    [
                        "Endpoint /health",
                        "Ukończony",
                        "Kontrola dostępności systemu."
                    ]
                ]
            },
            {
                title: "Task API",
                icon: "✅",
                progress: 65,
                status: "W trakcie",
                color: "var(--blue)",
                description:
                    "Tworzenie, odczytywanie i aktualizowanie zadań.",
                open: true,
                steps: [
                    [
                        "Model zadania",
                        "Ukończony",
                        "Definicja pól i statusów zadania."
                    ],
                    [
                        "Tworzenie zadań",
                        "Ukończony",
                        "Endpoint POST /tasks."
                    ],
                    [
                        "Lista zadań",
                        "W trakcie",
                        "Endpoint GET /tasks."
                    ],
                    [
                        "Aktualizacja zadania",
                        "W trakcie",
                        "Zmiana statusu i postępu."
                    ],
                    [
                        "Testy API",
                        "Zaplanowany",
                        "Testy integracyjne wszystkich operacji."
                    ]
                ]
            },
            {
                title: "Mózg systemu",
                icon: "🧠",
                progress: 10,
                status: "W trakcie",
                color: "var(--purple)",
                description:
                    "Główny agent odpowiedzialny za orkiestrację organizacji.",
                steps: [
                    [
                        "Projekt agenta głównego",
                        "Ukończony",
                        "Określenie odpowiedzialności głównego agenta."
                    ],
                    [
                        "Orkiestracja zadań",
                        "Zaplanowany",
                        "Przydzielanie pracy właściwym działom."
                    ],
                    [
                        "Kontrola rezultatów",
                        "Zaplanowany",
                        "Weryfikowanie efektów pracy agentów."
                    ]
                ]
            },
            {
                title: "Kierownicy działów",
                icon: "👔",
                progress: 0,
                status: "Zaplanowany",
                color: "var(--yellow)",
                description:
                    "Warstwa zarządzania wyspecjalizowanymi obszarami.",
                steps: [
                    [
                        "Definicja działów",
                        "Zaplanowany",
                        "Podział organizacji na obszary kompetencji."
                    ],
                    [
                        "Uprawnienia kierowników",
                        "Zaplanowany",
                        "Zakres decyzji i odpowiedzialności."
                    ],
                    [
                        "Przekazywanie zadań",
                        "Zaplanowany",
                        "Komunikacja między mózgiem a działami."
                    ]
                ]
            },
            {
                title: "Agenci wykonawczy",
                icon: "🤖",
                progress: 0,
                status: "Zaplanowany",
                color: "var(--yellow)",
                description:
                    "Programiści, graficy, analitycy i pozostali wykonawcy.",
                steps: [
                    [
                        "Profile kompetencji",
                        "Zaplanowany",
                        "Opis specjalizacji każdego agenta."
                    ],
                    [
                        "Wykonywanie zadań",
                        "Zaplanowany",
                        "Realizacja przydzielonych prac."
                    ],
                    [
                        "Raportowanie wyników",
                        "Zaplanowany",
                        "Przekazywanie rezultatów do kierownika."
                    ]
                ]
            },
            {
                title: "Bezpieczeństwo i audyt",
                icon: "🔐",
                progress: 0,
                status: "Zaplanowany",
                color: "var(--yellow)",
                description:
                    "Kontrola uprawnień, historia działań i procedury awaryjne.",
                steps: [
                    [
                        "Rejestr audytowy",
                        "Zaplanowany",
                        "Zapisywanie operacji wykonywanych przez system."
                    ],
                    [
                        "Kontrola uprawnień",
                        "Zaplanowany",
                        "Ograniczanie dostępu do zasobów."
                    ],
                    [
                        "Kopie zapasowe",
                        "Zaplanowany",
                        "Bezpieczne przechowywanie danych."
                    ]
                ]
            },
            {
                title: "Pamięć i baza wiedzy",
                icon: "📚",
                progress: 0,
                status: "Zaplanowany",
                color: "var(--yellow)",
                description:
                    "Historia projektów, wiedza i doświadczenia agentów.",
                steps: [
                    [
                        "Pamięć krótkoterminowa",
                        "Zaplanowany",
                        "Kontekst bieżących zadań."
                    ],
                    [
                        "Historia projektów",
                        "Zaplanowany",
                        "Przechowywanie wcześniejszych rezultatów."
                    ],
                    [
                        "Wyszukiwanie wiedzy",
                        "Zaplanowany",
                        "Odnajdywanie informacji przydatnych agentom."
                    ]
                ]
            },
            {
                title: "Moduły finansowe",
                icon: "💰",
                progress: 0,
                status: "Zaplanowany",
                color: "var(--yellow)",
                description:
                    "CRM, wyceny, koszty i symulacje płatności.",
                steps: [
                    [
                        "Rejestr klientów",
                        "Zaplanowany",
                        "Podstawowy moduł CRM."
                    ],
                    [
                        "Wycena projektów",
                        "Zaplanowany",
                        "Szacowanie kosztów i czasu."
                    ],
                    [
                        "Rejestr kosztów",
                        "Zaplanowany",
                        "Monitorowanie wydatków systemu."
                    ]
                ]
            }
        ];

        const baseProcesses = processes;
        let apiTotalProgress = null;

        const statusColors = {
            "Ukończony": "var(--green)",
            "W trakcie": "var(--blue)",
            "Zaplanowany": "var(--yellow)",
            "Zablokowany": "var(--red)"
        };

        function renderProcesses() {
            const container = document.getElementById("processes");

            container.innerHTML = processes.map((process, index) => {
                const steps = process.steps.map((step, stepIndex) => `
                    <div class="step"
                         style="
                            --step-color: ${
                                statusColors[step[1]] || "var(--muted)"
                            };
                            animation-delay: ${stepIndex * 70}ms;
                         ">
                        <div class="step-line">
                            <span class="step-number">${stepIndex + 1}</span>
                            <span class="step-name">${step[0]}</span>
                            <span class="step-status">${step[1]}</span>
                        </div>

                        <p class="step-description">${step[2]}</p>
                    </div>
                `).join("");

                return `
                    <article class="process ${process.open ? "open" : ""}"
                             style="--accent: ${process.color}">
                        <div class="process-header"
                             role="button"
                             tabindex="0"
                             aria-expanded="${process.open}">
                            <div class="process-name">
                                <span class="process-icon">${process.icon}</span>

                                <div>
                                    <h2>${process.title}</h2>
                                    <span class="status">${process.status}</span>
                                </div>
                            </div>

                            <div class="process-percent">
                                ${process.progress}%
                                <span class="arrow">⌄</span>
                            </div>
                        </div>

                        <div class="details-wrapper">
                            <div class="details-hidden">
                                <div class="details">
                                    <p class="description">
                                        ${process.description}
                                    </p>

                                    <div class="small-progress">
                                        <div class="small-progress-label">
                                            <span>Postęp procesu</span>
                                            <strong>${process.progress}%</strong>
                                        </div>

                                        <div class="progress-track">
                                            <div class="progress-fill"
                                                 style="
                                                    --progress: ${
                                                        process.progress
                                                    }%;
                                                 ">
                                            </div>
                                        </div>
                                    </div>

                                    <div class="steps">${steps}</div>
                                </div>
                            </div>
                        </div>
                    </article>
                `;
            }).join("");

            document.querySelectorAll(".process-header").forEach(header => {
                const toggle = () => {
                    const process = header.closest(".process");
                    const expanded = process.classList.toggle("open");

                    header.setAttribute(
                        "aria-expanded",
                        expanded ? "true" : "false"
                    );
                };

                header.addEventListener("click", toggle);

                header.addEventListener("keydown", event => {
                    if (event.key === "Enter" || event.key === " ") {
                        event.preventDefault();
                        toggle();
                    }
                });
            });
        }

        function renderTotalProgress() {
            const total = apiTotalProgress ?? Math.round(
                processes.reduce(
                    (sum, process) => sum + process.progress,
                    0
                ) / processes.length
            );

            document.getElementById("total-percent").textContent = `${total}%`;

            document.getElementById("total-progress").style.setProperty(
                "--progress",
                `${total}%`
            );
        }

        async function refreshProgressFromApi() {
            try {
                const response = await fetch("/api/progress", {
                    cache: "no-store"
                });

                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}`);
                }

                const data = await response.json();
                apiTotalProgress = data.total_progress;

                const liveTasksProcess = {
                    title: `Bieżące zadania systemowe (${data.task_count})`,
                    icon: "📋",
                    progress: data.total_progress,
                    status: data.task_count
                        ? "W trakcie"
                        : "Zaplanowany",
                    color: data.counts.blocked
                        ? "var(--red)"
                        : "var(--blue)",
                    description: data.task_count
                        ? "Dane pobierane automatycznie z lokalnej bazy SQLite."
                        : "Brak zapisanych zadań. Utwórz zadanie przez Task API.",
                    open: true,
                    steps: data.tasks.length
                        ? data.tasks.map(task => [
                            `#${task.id} · ${task.title}`,
                            task.status_label,
                            `${task.progress}% · Priorytet: ${task.priority}` +
                            (task.assigned_agent
                                ? ` · Agent: ${task.assigned_agent}`
                                : "")
                        ])
                        : [[
                            "Brak zadań",
                            "Zaplanowany",
                            "Nie utworzono jeszcze żadnego zadania."
                        ]]
                };

                processes = [...baseProcesses, liveTasksProcess];
                renderProcesses();
                renderTotalProgress();
            } catch (error) {
                console.error(
                    "Nie udało się pobrać danych postępu:",
                    error
                );
            }
        }

        renderProcesses();
        renderTotalProgress();
        refreshProgressFromApi();

        // Odświeżenie mapy co 10 sekund bez przeładowania strony.
        window.setInterval(refreshProgressFromApi, 10000);
    </script>
</body>
</html>
"""

