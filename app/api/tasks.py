from collections.abc import Generator
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import load_settings
from app.models.task import (
    ApprovalStatus,
    ResourceClass,
    RiskLevel,
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
    approval_status: ApprovalStatus
    priority: TaskPriority
    resource_class: ResourceClass
    risk_level: RiskLevel
    assigned_agent: str | None
    progress: int
    stages: list[dict]
    created_at: datetime
    updated_at: datetime
    queued_at: datetime | None
    started_at: datetime | None
    completed_at: datetime | None


class TaskCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    priority: TaskPriority = TaskPriority.NORMAL
    resource_class: ResourceClass = ResourceClass.LIGHT
    risk_level: RiskLevel = RiskLevel.LOW
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


RepositoryDependency = Annotated[
    TaskRepository,
    Depends(get_repository),
]


@router.get("", response_model=list[TaskResponse])
def list_tasks(
    repository: RepositoryDependency,
    limit: int = Query(default=50, ge=1, le=100),
    status: TaskStatus | None = Query(default=None),
    priority: TaskPriority | None = Query(default=None),
    resource_class: ResourceClass | None = Query(default=None),
    risk_level: RiskLevel | None = Query(default=None),
    assigned_agent: str | None = Query(default=None),
) -> list[Task]:
    try:
        return repository.list_recent(
            limit=limit,
            status=status,
            priority=priority,
            resource_class=resource_class,
            risk_level=risk_level,
            assigned_agent=assigned_agent,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=503,
            detail="Repozytorium zadań jest niedostępne",
        ) from exc


@router.get("/{task_id}", response_model=TaskResponse)
def get_task(
    repository: RepositoryDependency,
    task_id: int = Path(ge=1),
) -> Task:
    try:
        return repository.get_required(task_id)
    except TaskNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=503,
            detail="Repozytorium zadań jest niedostępne",
        ) from exc


@router.post("", response_model=TaskResponse, status_code=201)
def create_task(
    payload: TaskCreateRequest,
    repository: RepositoryDependency,
) -> Task:
    try:
        return repository.create(
            title=payload.title,
            description=payload.description,
            priority=payload.priority,
            resource_class=payload.resource_class,
            risk_level=payload.risk_level,
            assigned_agent=payload.assigned_agent,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=503,
            detail="Repozytorium zadań jest niedostępne",
        ) from exc


@router.patch(
    "/{task_id}/status",
    response_model=TaskResponse,
)
def update_status(
    payload: StatusUpdateRequest,
    repository: RepositoryDependency,
    task_id: int = Path(ge=1),
) -> Task:
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


@router.patch(
    "/{task_id}/assignment",
    response_model=TaskResponse,
)
def update_assignment(
    payload: AssignmentRequest,
    repository: RepositoryDependency,
    task_id: int = Path(ge=1),
) -> Task:
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
