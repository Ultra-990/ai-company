"""Separate ASGI surface for future client deployment. Not started automatically.

Do not expose app.main publicly: it retains legacy internal read endpoints.
TLS, gateway rate limits and network configuration remain deployment work.
"""
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, RedirectResponse

from app.api.client_portal import client_router
from app.api.client_feedback import client_router as client_feedback_router
from app.api.help_center import client_router as help_router

app = FastAPI(title="AI Company Client Space", docs_url=None, redoc_url=None, openapi_url=None)
app.include_router(client_router)
app.include_router(client_feedback_router)
app.include_router(help_router)
ROOT = Path(__file__).resolve().parent
ASSETS = {"theme.js", "theme.css", "organization-os.css", "client.js", "client.css", "help.js", "help.css"}


@app.middleware("http")
async def client_headers(request, call_next):
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'"
    return response


@app.get("/")
def home():
    return RedirectResponse("/client")


@app.get("/client")
def portal():
    return FileResponse(ROOT / "templates/organization-os/client.html")


@app.get("/static/organization-os/{name}")
def asset(name: str):
    if name not in ASSETS:
        raise HTTPException(404, "Nie znaleziono zasobu.")
    return FileResponse(ROOT / "static/organization-os" / name)
