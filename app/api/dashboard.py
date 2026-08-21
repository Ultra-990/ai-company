from collections import Counter
from typing import Any

from fastapi import APIRouter

from app.services.project_progress import load_project_progress
from app.api.owner import APPROVALS


router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


def _approval_summary() -> dict[str, Any]:
    """Zwraca podsumowanie elementów znajdujących się w kolejce akceptacji."""
    statuses = Counter(
        item.get("status", "UNKNOWN")
        for item in APPROVALS.values()
    )

    return {
        "total": len(APPROVALS),
        "pending": statuses.get("PENDING", 0),
        "approved": statuses.get("APPROVED", 0),
        "rejected": statuses.get("REJECTED", 0),
    }


def _project_summary() -> dict[str, Any]:
    """Wczytuje i zwraca aktualny postęp projektu."""
    progress = load_project_progress()

    return {
        "name": progress["project"],
        "total_progress": progress["total_progress"],
        "stages": progress["stages"],
    }


@router.get("")
def dashboard_home() -> dict[str, Any]:
    """Zwraca bieżący snapshot dashboardu."""
    return {
        "status": "ok",
        "project": _project_summary(),
        "tasks": {
            "total": 0,
            "pending": 0,
            "approved": 0,
            "rejected": 0,
            "source": "not_available",
        },
        "approvals": _approval_summary(),
        "system": {
            "status": "ok",
        },
    }


@router.get("/summary")
def dashboard_summary() -> dict[str, Any]:
    """Zwraca skrócone podsumowanie dashboardu."""
    project = _project_summary()
    approvals = _approval_summary()

    return {
        "status": "ok",
        "project": project["name"],
        "progress": project["total_progress"],
        "approvals": approvals,
        "tasks": {
            "total": 0,
            "source": "not_available",
        },
    }
