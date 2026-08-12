from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from app.api.system import router as system_router
from app.api.tasks import router as tasks_router
from app.api.progress import router as progress_router


app = FastAPI(
    title="AI Company",
    description="Lokalny system zarządzania firmą agentów AI",
    version="0.1.0",
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
        <title>AI Company</title>
        <style>
            body {
                margin: 0;
                font-family: Arial, sans-serif;
                background: #0f172a;
                color: #e2e8f0;
            }

            main {
                width: min(900px, 90%);
                margin: 70px auto;
            }

            .card {
                padding: 28px;
                border: 1px solid #334155;
                border-radius: 14px;
                background: #1e293b;
            }

            .status {
                color: #4ade80;
                font-weight: bold;
            }

            code {
                color: #93c5fd;
            }
        </style>
    </head>
    <body>
        <main>
            <h1>AI Company</h1>

            <div class="card">
                <h2>Panel właściciela</h2>
                <p class="status">● System lokalny działa</p>
                <p>Wersja: <code>0.1.0</code></p>
                <p>Agenci AI są jeszcze wyłączeni.</p>
                <p>Następny etap: konstytucja i struktura agentów.</p>
            </div>
        </main>
    </body>
    </html>
    """

app.include_router(system_router)
app.include_router(tasks_router)
app.include_router(progress_router)
