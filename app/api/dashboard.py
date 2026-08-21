from collections import Counter
from typing import Any

from fastapi import APIRouter, Depends

from app.services.project_progress import load_project_progress
from app.api.tasks import get_repository
from app.models.task import ApprovalStatus
from app.services.tasks import TaskRepository


router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


def _approval_summary(
    repository: TaskRepository,
) -> dict[str, Any]:
    """Zwraca podsumowanie statusów akceptacji z repozytorium zadań."""
    tasks = repository.list_recent(limit=100)

    statuses = Counter(task.approval_status for task in tasks)

    return {
        "total": len(tasks),
        "pending": statuses.get(ApprovalStatus.PENDING, 0),
        "approved": statuses.get(ApprovalStatus.APPROVED, 0),
        "rejected": statuses.get(ApprovalStatus.REJECTED, 0),
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
        "approvals": _approval_summary(repository),
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
    approvals = _approval_summary(repository)

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
