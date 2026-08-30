import os
import secrets

from fastapi import APIRouter, Depends, Header, HTTPException

from app.api.tasks import TaskResponse, get_repository
from app.services.tasks import TaskNotFoundError, TaskRepository


router = APIRouter(prefix="/api/owner", tags=["owner"])


def require_owner(
    authorization: str | None = Header(default=None),
) -> None:
    expected = os.environ.get("OWNER_API_TOKEN")

    if not expected or not authorization:
        raise HTTPException(status_code=401, detail="Unauthorized")

    scheme, _, token = authorization.partition(" ")

    if (
        scheme.lower() != "bearer"
        or not token
        or not secrets.compare_digest(token, expected)
    ):
        raise HTTPException(status_code=401, detail="Unauthorized")



@router.get("/pending-approvals", response_model=list[TaskResponse])
def pending_approvals(
    repository: TaskRepository = Depends(get_repository),
    _: None = Depends(require_owner),
):
    return repository.list_recent(approval_status="pending")


@router.post("/tasks/{task_id}/approve", response_model=TaskResponse)
def approve_task(
    task_id: int,
    repository: TaskRepository = Depends(get_repository),
    _: None = Depends(require_owner),
):
    try:
        task = repository.approve(task_id)
    except TaskNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="Task not found",
        )

    if task is None:
        raise HTTPException(
            status_code=404,
            detail="Task not found",
        )

    return task


@router.post("/tasks/{task_id}/reject", response_model=TaskResponse)
def reject_task(
    task_id: int,
    repository: TaskRepository = Depends(get_repository),
    _: None = Depends(require_owner),
):
    try:
        task = repository.reject(task_id)
    except TaskNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="Task not found",
        )

    if task is None:
        raise HTTPException(
            status_code=404,
            detail="Task not found",
        )

    return task
