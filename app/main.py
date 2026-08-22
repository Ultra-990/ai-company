from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from app.core.config import load_settings
from app.core.database import Base, create_database_engine
from app.models.organization import OrganizationUnit
from app.db.migrations import migrate_task_queue_schema
from app.api.system import router as system_router
from app.api.tasks import router as tasks_router
from app.api.progress import router as progress_router
from app.api.owner import router as owner_router
from app.api.dashboard import router as dashboard_router
from app.api.brain import router as brain_router




settings = load_settings()
engine = create_database_engine(settings.database.url)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Tworzy aktualny schemat bazy i stosuje bezpieczne migracje."""
    Base.metadata.create_all(bind=engine)
    migrate_task_queue_schema(engine)
    yield


app = FastAPI(
    title="AI Company",
    description="Lokalny system zarządzania firmą agentów AI",
    version="0.1.0",
    lifespan=lifespan,
)

@app.get("/health")
def health_check() -> dict:
    return {
        "status": "ok",
        "system": "AI Company",
        "version": "0.1.0",
        "llm_enabled": False,
    }


@app.get("/", response_class=HTMLResponse)
def dashboard() -> str:
    return """
    <!DOCTYPE html>
    <html lang="pl">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>AI Company — Dashboard</title>
        <style>
            * {
                box-sizing: border-box;
            }

            body {
                margin: 0;
                font-family: Arial, sans-serif;
                background: #0f172a;
                color: #e2e8f0;
            }

            main {
                width: min(1100px, 92%);
                margin: 40px auto;
            }

            h1 {
                margin-bottom: 8px;
            }

            .subtitle {
                color: #94a3b8;
                margin-bottom: 28px;
            }

            .grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
                gap: 16px;
                margin: 20px 0;
            }

            .card {
                padding: 22px;
                border: 1px solid #334155;
                border-radius: 14px;
                background: #1e293b;
            }

            .card h2 {
                margin-top: 0;
                font-size: 18px;
            }

            .metric {
                font-size: 34px;
                font-weight: bold;
                margin-top: 12px;
            }

            .pending {
                color: #facc15;
            }

            .approved {
                color: #4ade80;
            }

            .rejected {
                color: #f87171;
            }

            .progress-container {
                height: 18px;
                background: #334155;
                border-radius: 9px;
                overflow: hidden;
            }

            .progress-bar {
                height: 100%;
                width: 0%;
                background: #38bdf8;
                transition: width 0.4s ease;
            }

            #message {
                color: #94a3b8;
            }

            .error {
                color: #f87171 !important;
            }

            button {
                padding: 10px 16px;
                border: 0;
                border-radius: 8px;
                background: #2563eb;
                color: white;
                cursor: pointer;
            }

            button:hover {
                background: #1d4ed8;
            }
        </style>
    </head>
    <body>
        <main>
            <h1>AI Company — Dashboard</h1>
            <p id="message" class="subtitle">Ładowanie danych...</p>

            <section class="card">
                <h2>Projekt: <span id="project-name">—</span></h2>
                <p>Postęp projektu: <strong id="progress-value">—</strong>%</p>
                <div class="progress-container">
                    <div id="progress-bar" class="progress-bar"></div>
                </div>
            </section>

            <section class="grid">
                <div class="card">
                    <h2>Wszystkie akceptacje</h2>
                    <div id="total" class="metric">—</div>
                </div>

                <div class="card">
                    <h2>Oczekujące</h2>
                    <div id="pending" class="metric pending">—</div>
                </div>

                <div class="card">
                    <h2>Zatwierdzone</h2>
                    <div id="approved" class="metric approved">—</div>
                </div>

                <div class="card">
                    <h2>Odrzucone</h2>
                    <div id="rejected" class="metric rejected">—</div>
                </div>
            </section>

            <button id="refresh-button">Odśwież dane</button>
        </main>

        <script>
            async function loadDashboard() {
                const message = document.getElementById("message");

                try {
                    message.textContent = "Ładowanie danych...";
                    message.classList.remove("error");

                    const response = await fetch("/api/dashboard/summary");

                    if (!response.ok) {
                        throw new Error(`Błąd HTTP: ${response.status}`);
                    }

                    const data = await response.json();
                    const approvals = data.approvals || {};

                    const progress = Number(data.progress) || 0;

                    document.getElementById("project-name").textContent =
                        data.project || "Brak nazwy";

                    document.getElementById("progress-value").textContent = progress;
                    document.getElementById("progress-bar").style.width =
                        `${Math.min(Math.max(progress, 0), 100)}%`;

                    document.getElementById("total").textContent =
                        approvals.total ?? 0;

                    document.getElementById("pending").textContent =
                        approvals.pending ?? 0;

                    document.getElementById("approved").textContent =
                        approvals.approved ?? 0;

                    document.getElementById("rejected").textContent =
                        approvals.rejected ?? 0;

                    message.textContent =
                        `Status systemu: ${data.status || "nieznany"}`;
                } catch (error) {
                    console.error(error);
                    message.textContent =
                        "Nie udało się pobrać danych dashboardu.";
                    message.classList.add("error");
                }
            }

            document
                .getElementById("refresh-button")
                .addEventListener("click", loadDashboard);

            loadDashboard();
        </script>
    </body>
    </html>
    """

app.include_router(system_router)
app.include_router(tasks_router)
app.include_router(progress_router)
app.include_router(owner_router)
app.include_router(dashboard_router)

app.include_router(brain_router)
