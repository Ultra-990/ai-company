from collections.abc import Generator

from fastapi import APIRouter, HTTPException, Path, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import load_settings
from app.models.task import (
    Task,
    TaskPriority,
    TaskStatus,
    TaskTransitionError,
)
from app.services.tasks import TaskNotFoundError, TaskRepository


router = APIRouter(prefix="/api/tasks", tags=["tasks"])


class TaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str | None
    status: TaskStatus
    priority: TaskPriority
    assigned_agent: str | None
    created_at: object
    updated_at: object

class TaskCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    priority: TaskPriority = TaskPriority.NORMAL
    assigned_agent: str | None = Field(default=None, max_length=100)

class StatusUpdateRequest(BaseModel):
    status: TaskStatus




class AssignmentRequest(BaseModel):
    assigned_agent: str | None = Field(default=None, max_length=100)


def get_repository() -> Generator[TaskRepository, None, None]:
    repository = TaskRepository(load_settings().database.url)

    try:
        yield repository
    finally:
        repository.close()


@router.get("", response_model=list[TaskResponse])
def list_tasks(
    limit: int = Query(default=50, ge=1, le=100),
    status: TaskStatus | None = Query(default=None),
    priority: TaskPriority | None = Query(default=None),
    assigned_agent: str | None = Query(default=None),
) -> list[Task]:
    repository = TaskRepository(load_settings().database.url)

    try:
        return repository.list_recent(
            limit=limit,
            status=status,
            priority=priority,
            assigned_agent=assigned_agent,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=503,
            detail="Repozytorium zadań jest niedostępne",
        ) from exc
    finally:
        repository.close()

@router.post("", response_model=TaskResponse, status_code=201)
def create_task(payload: TaskCreateRequest) -> Task:
    repository = TaskRepository(load_settings().database.url)

    try:
        return repository.create(
            title=payload.title,
            description=payload.description,
            priority=payload.priority,
            assigned_agent=payload.assigned_agent,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=503,
            detail="Repozytorium zadań jest niedostępne",
        ) from exc
    finally:
        repository.close()


@router.patch(
    "/{task_id}/status",
    response_model=TaskResponse,
)
def update_status(
    payload: StatusUpdateRequest,
    task_id: int = Path(ge=1),
) -> Task:
    repository = TaskRepository(load_settings().database.url)

    try:
        return repository.transition(task_id, payload.status)
    except TaskNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except TaskTransitionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=503,
            detail="Repozytorium zadań jest niedostępne",
        ) from exc
    finally:
        repository.close()


@router.patch(
    "/{task_id}/assignment",
    response_model=TaskResponse,
)
def update_assignment(
    payload: AssignmentRequest,
    task_id: int = Path(ge=1),
) -> Task:
    repository = TaskRepository(load_settings().database.url)

    try:
        return repository.assign(task_id, payload.assigned_agent)
    except TaskNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=503,
            detail="Repozytorium zadań jest niedostępne",
        ) from exc
    finally:
        repository.close()
