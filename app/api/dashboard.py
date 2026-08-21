from typing import Any

from fastapi import APIRouter, Depends

from app.api.tasks import get_repository
from app.services.project_progress import load_project_progress
from app.services.tasks import TaskRepository


router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


def _task_summary(
    repository: TaskRepository,
) -> dict[str, Any]:
    """Zwraca pełne podsumowanie zadań z repozytorium."""
    return {
        **repository.summary(),
        "source": "task_repository",
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
def dashboard_home(
    repository: TaskRepository = Depends(get_repository),
) -> dict[str, Any]:
    """Zwraca bieżący snapshot dashboardu."""
    tasks = _task_summary(repository)

    return {
        "status": "ok",
        "project": _project_summary(),
        "tasks": tasks,
        "approvals": {
            "total": tasks["total"],
            "pending": tasks["pending"],
            "approved": tasks["approved"],
            "rejected": tasks["rejected"],
        },
        "system": {
            "status": "ok",
        },
    }


@router.get("/summary")
def dashboard_summary(
    repository: TaskRepository = Depends(get_repository),
) -> dict[str, Any]:
    """Zwraca skrócone podsumowanie dashboardu."""
    project = _project_summary()
    tasks = _task_summary(repository)

    return {
        "status": "ok",
        "project": project["name"],
        "progress": project["total_progress"],
        "approvals": {
            "total": tasks["total"],
            "pending": tasks["pending"],
            "approved": tasks["approved"],
            "rejected": tasks["rejected"],
        },
        "tasks": {
            "total": tasks["total"],
            "source": tasks["source"],
        },
    }
