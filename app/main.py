from contextlib import asynccontextmanager
from pathlib import Path
from app.api.application_revisions import router as application_revisions_router
from app.api.application_quality import router as application_quality_router
from app.api.help_center import owner_router as owner_help_router, client_router as client_help_router
from app.api.owner_session import router as owner_session_router

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.responses import HTMLResponse

from app.core.config import load_settings
from app.core.database import Base, create_database_engine
from app.models.organization import OrganizationUnit
from app.models.approval import ApprovalRequest
from app.models.pending_tool_execution import PendingToolExecution
from app.models.project import Project
from app.models.plan import Plan
from app.models.roadmap import RoadmapItemState
from app.models.artifact import Artifact
from app.models.organization_os import Agent, Alert, WorkspacePreference
from app.db.migrations import (
    migrate_artifact_schema,
    migrate_media_generation_schema,
    migrate_legacy_organization_os_enum_values,
    migrate_legacy_organization_os_taxonomy,
    migrate_approval_request_schema,
    migrate_pending_tool_execution_schema,
    migrate_project_schema,
    migrate_plan_schema,
    migrate_roadmap_item_state_schema,
    migrate_task_project_plan_schema,
    migrate_task_attempt_schema,
    migrate_task_queue_schema,
    migrate_task_roadmap_item_schema,
    migrate_organization_os_schema,
    seed_organization_os,
)
from app.api.approvals import router as approvals_router
from app.api.system import router as system_router
from app.api.tasks import router as tasks_router
from app.api.progress import router as progress_router
from app.api.owner import router as owner_router
from app.api.dashboard import router as dashboard_router
from app.api.brain import router as brain_router
from app.api.execution import router as execution_router
from app.api.organization_os import router as organization_os_router
from app.api.workspace_packages import router as workspace_packages_router
from app.api.client_portal import router as client_portal_router
from app.api.client_portal import client_router
from app.api.client_feedback import client_router as client_feedback_router, owner_router as owner_client_feedback_router
from app.api.work_orders import router as work_orders_router
from app.api.upwork_orders import router as upwork_orders_router
from app.api.agent_teams import router as agent_teams_router
from app.api.agent_packets import router as agent_packets_router
from app.api.local_model_queue import router as local_model_queue_router
from app.api.local_inference import router as local_inference_router
from app.api.media_generation import router as media_generation_router
from app.api.package_runner import router as package_runner_router
from app.api.requirement_checks import router as requirement_checks_router
from app.api.acceptance_cases import router as acceptance_cases_router
from app.api.package_checks import router as package_checks_router
from app.api.package_previews import router as package_previews_router
from app.api.workspace_exports import router as workspace_exports_router




settings = load_settings()
engine = create_database_engine(settings.database.url)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Tworzy aktualny schemat bazy i stosuje bezpieczne migracje."""
    Base.metadata.create_all(bind=engine)
    migrate_task_queue_schema(engine)
    migrate_task_roadmap_item_schema(engine)
    migrate_approval_request_schema(engine)
    migrate_pending_tool_execution_schema(engine)
    migrate_task_attempt_schema(engine)
    migrate_project_schema(engine)
    migrate_plan_schema(engine)
    migrate_roadmap_item_state_schema(engine)
    migrate_task_project_plan_schema(engine)
    migrate_artifact_schema(engine)
    migrate_media_generation_schema(engine)
    migrate_legacy_organization_os_enum_values(engine)
    migrate_organization_os_schema(engine)
    migrate_legacy_organization_os_taxonomy(engine)
    seed_organization_os(engine)
    yield





app = FastAPI(
    title="AI Company",
    description="Lokalny system zarządzania firmą agentów AI",
    version="0.1.0",
    lifespan=lifespan,
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

COMMAND_PAGE_HEADERS = {
    "Cache-Control": "no-store", "Referrer-Policy": "no-referrer",
    "X-Content-Type-Options": "nosniff",
    "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'",
}


@app.get("/os", response_class=HTMLResponse)
def organization_os() -> FileResponse:
    """Primary, task-oriented company command centre."""
    return FileResponse("app/templates/organization-os/command.html", headers=COMMAND_PAGE_HEADERS)


@app.get("/os/media", response_class=HTMLResponse)
def organization_media_page() -> FileResponse:
    headers = dict(COMMAND_PAGE_HEADERS)
    headers['Content-Security-Policy'] += "; img-src 'self' blob:"
    return FileResponse("app/templates/organization-os/media.html", headers=headers)


@app.get("/os/legacy", response_class=HTMLResponse)
def legacy_organization_os() -> FileResponse:
    """Preserved previous window-based desktop, with working legacy tools."""
    return FileResponse("app/templates/organization-os/index.html", headers={"Cache-Control": "no-store"})


@app.get("/os/publishing", response_class=HTMLResponse)
def organization_publishing() -> FileResponse:
    """Dedicated owner publication tool; mutations retain owner authorization."""
    return FileResponse("app/templates/organization-os/publishing.html", headers=COMMAND_PAGE_HEADERS)


@app.get("/os/review", response_class=HTMLResponse)
def organization_review() -> FileResponse:
    """Owner task review and packages, independent of the archived scene."""
    return FileResponse("app/templates/organization-os/review.html", headers=COMMAND_PAGE_HEADERS)


@app.get('/os/build',response_class=HTMLResponse)
def isolated_build_page() -> FileResponse:
    headers=COMMAND_PAGE_HEADERS | {'Content-Security-Policy':COMMAND_PAGE_HEADERS['Content-Security-Policy']+"; frame-src 'self'"}
    return FileResponse('app/templates/organization-os/build.html',headers=headers)


@app.get('/os/application-frame',response_class=HTMLResponse)
def application_frame() -> HTMLResponse:
    # No application sources or credentials are embedded in the HTTP response.
    script=(Path(__file__).resolve().parent/'static/organization-os/application-frame.js').read_text()
    return HTMLResponse('<!doctype html><html lang="pl"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Podgląd aplikacji</title><body><p>Przygotowuję podgląd…</p><script>'+script+'</script></body></html>',headers={
        'Cache-Control':'no-store','Referrer-Policy':'no-referrer','X-Content-Type-Options':'nosniff',
        'Content-Security-Policy':"sandbox allow-scripts allow-forms; default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src data:; connect-src 'none'; object-src 'none'; base-uri 'none'; form-action 'none'; frame-src 'none'; frame-ancestors 'self'",
        'Permissions-Policy':'camera=(), microphone=(), geolocation=(), payment=(), usb=()'})


@app.get("/os/spatial", response_class=HTMLResponse)
def spatial_os_page() -> FileResponse:
    """Opt-in spatial prototype; existing OS and production data are unchanged."""
    return FileResponse("app/templates/organization-os/spatial.html", headers={
        "Cache-Control": "no-store", "Referrer-Policy": "no-referrer",
    })


@app.get("/client", response_class=HTMLResponse)
def client_portal_page() -> HTMLResponse:
    """Local client portal shell; no project data embedded in HTML."""
    source = (Path(__file__).resolve().parent / "templates/organization-os/client.html").read_text(encoding="utf-8")
    # Internal preview can return to the company. The separate client app keeps
    # its own /client home and does not expose internal pages or owner controls.
    source = source.replace('href="/client" data-back', 'href="/os" data-back').replace(
        'href="/client" data-home>Panel klienta', 'href="/os" data-home>Pulpit')
    source = source.replace('<form id="client-login"', '<p class="client-card">Jesteś właścicielem? <a href="/os/client-preview">Otwórz podgląd właściciela</a>. Poniższe wejście wymaga osobnego kodu projektu, nie tokena właściciela.</p><form id="client-login"')
    return HTMLResponse(source, headers={
        "Cache-Control": "no-store", "Referrer-Policy": "no-referrer",
        "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'",
    })


@app.get("/os/upwork", response_class=HTMLResponse)
def upwork_page() -> FileResponse:
    return FileResponse("app/templates/organization-os/upwork.html", headers={
        "Cache-Control": "no-store", "Referrer-Policy": "no-referrer",
        "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'",
    })


@app.get("/os/work", response_class=HTMLResponse)
def workbench_page() -> FileResponse:
    return FileResponse("app/templates/organization-os/work.html", headers={
        "Cache-Control": "no-store", "Referrer-Policy": "no-referrer",
        "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'",
    })


@app.get("/os/clients", response_class=HTMLResponse)
def client_history_page() -> FileResponse:
    return FileResponse("app/templates/organization-os/client-history.html", headers={
        "Cache-Control": "no-store", "Referrer-Policy": "no-referrer",
        "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'",
    })


@app.get("/os/client-preview", response_class=HTMLResponse)
def owner_client_preview() -> HTMLResponse:
    source = (Path(__file__).resolve().parent / "templates/organization-os/client.html").read_text(encoding="utf-8")
    source = source.replace('</head>', '<link rel="stylesheet" href="/static/organization-os/owner-session.css?v=20260920-local"><script src="/static/organization-os/owner-session.js?v=20260920-local" defer></script></head>')
    source = source.replace('<body>', '<body data-owner-preview="true">').replace('href="/client" data-back', 'href="/os/clients" data-back').replace('href="/client" data-home>Panel klienta', 'href="/os" data-home>Pulpit')
    return HTMLResponse(source, headers={"Cache-Control":"no-store", "Referrer-Policy":"no-referrer",
        "Content-Security-Policy":"default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'"})


@app.middleware("http")
async def audit_successful_api_mutations(request, call_next):
    """
    Rejestruje tylko zakończone sukcesem mutacje wykonane po RBAC.

    Rola i repozytorium są ustawiane przez require_owner/require_worker.
    Token ani nagłówek Authorization nie są tu odczytywane lub zapisywane.
    """
    response = await call_next(request)

    role = getattr(request.state, "authenticated_role", None)
    repository = getattr(request.state, "audit_repository", None)
    is_mutation = request.method in {"POST", "PUT", "PATCH", "DELETE"}
    is_success = 200 <= response.status_code < 300

    if role and repository and is_mutation and is_success:
        operation = f"{request.method} {request.url.path}"[:64]

        try:
            repository.record(
                event_type="api_mutation",
                operation=operation,
                decision="completed",
                allowed=True,
                reason=role,
            )
        except Exception:
            # Sam audyt nie może unieważniać poprawnie wykonanej operacji.
            pass

    return response


app.include_router(system_router)
app.include_router(execution_router)
app.include_router(organization_os_router)
app.include_router(workspace_packages_router)
app.include_router(package_checks_router)
app.include_router(package_previews_router)
app.include_router(workspace_exports_router)
app.include_router(work_orders_router)
app.include_router(upwork_orders_router)
app.include_router(agent_teams_router)
app.include_router(agent_packets_router)
app.include_router(local_model_queue_router)
app.include_router(local_inference_router)
app.include_router(media_generation_router)
app.include_router(package_runner_router)
app.include_router(requirement_checks_router)
app.include_router(acceptance_cases_router)
app.include_router(application_revisions_router)
app.include_router(application_quality_router)
app.include_router(owner_help_router)
app.include_router(owner_session_router)
app.include_router(client_help_router)
app.include_router(client_portal_router)
app.include_router(client_router)
app.include_router(client_feedback_router)
app.include_router(owner_client_feedback_router)
app.include_router(tasks_router)
app.include_router(progress_router)
app.include_router(owner_router)
app.include_router(approvals_router)
app.include_router(dashboard_router)
app.include_router(brain_router)


@app.get("/health")
def health_check() -> dict:
    return {
        "status": "ok",
        "system": "AI Company",
        "version": "0.1.0",
        "llm_enabled": settings.llm.enabled,
        "llm_model": settings.llm.model if settings.llm.enabled else None,
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
        <script src="/static/organization-os/theme.js?v=4"></script>
        <link rel="stylesheet" href="/static/organization-os/theme.css?v=2">
    </head>
    <body class="legacy-page">
        <nav class="app-navigation" aria-label="Nawigacja aplikacji"><a href="/os" data-back>← Wstecz</a><a href="/os" data-home>Pulpit</a></nav>
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

                    const [summaryResponse, progressResponse] = await Promise.all([
                        fetch("/api/dashboard/summary"),
                        fetch("/api/progress")
                    ]);

                    if (!summaryResponse.ok || !progressResponse.ok) {
                        throw new Error(
                            `Błąd HTTP: dashboard=${summaryResponse.status}, progress=${progressResponse.status}`
                        );
                    }

                    const data = await summaryResponse.json();
                    const progressData = await progressResponse.json();
                    const approvals = data.approvals || {};

                    // Faktyczny postęp obliczany z aktualnego stanu zadań w SQLite.
                    const progress = Number(progressData.total_progress) || 0;

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

            // Automatyczna aktualizacja danych dashboardu co 15 sekund.
            setInterval(loadDashboard, 15000);
        </script>
    </body>
    </html>
    """
