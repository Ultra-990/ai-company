import os

from fastapi import APIRouter, HTTPException

from app.api.tasks import TaskResponse
from app.services.tasks import TaskRepository


router = APIRouter(prefix="/api/owner", tags=["owner"])


def _repository() -> TaskRepository:
    database_url = os.getenv("DATABASE_URL", "sqlite:///./app.db")
    return TaskRepository(database_url=database_url)


@router.get("/pending-approvals", response_model=list[TaskResponse])
def pending_approvals():
    repository = _repository()
    return repository.list_recent(approval_status="pending")


@router.post("/tasks/{task_id}/approve", response_model=TaskResponse)
def approve_task(task_id: int):
    repository = _repository()
    task = repository.approve(task_id)

    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    return task


@router.post("/tasks/{task_id}/reject", response_model=TaskResponse)
def reject_task(task_id: int):
    repository = _repository()
    task = repository.reject(task_id)

    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    return task
