from collections.abc import Generator
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.exc import SQLAlchemyError

from app.api.auth import require_owner
from app.core.config import load_settings
from app.models.task import (
    ApprovalStatus,
    ResourceClass,
    RiskLevel,
    Task,
    TaskAttempt,
    TaskPriority,
    TaskStatus,
    TaskTransitionError,
)
from app.services.roadmap_progress import ProjectProgressService
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
    roadmap_item_id: str | None
    progress: int
    stages: list[dict]
    created_at: datetime
    updated_at: datetime
    queued_at: datetime | None
    started_at: datetime | None
    completed_at: datetime | None


class VerificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    task_id: int
    verification_status: str
    verification_reason: str | None
    verified_at: datetime | None


class VerifyAttemptRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    result_content: str = Field(min_length=1)
    verifier_id: str = Field(min_length=1, max_length=100)
    reason: str = Field(
        default="Wynik wykonania został zweryfikowany",
        min_length=1,
    )


class TaskCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    priority: TaskPriority = TaskPriority.NORMAL
    resource_class: ResourceClass = ResourceClass.LIGHT
    risk_level: RiskLevel = RiskLevel.LOW
    assigned_agent: str | None = Field(default=None, max_length=100)
    roadmap_item_id: str | None = Field(default=None, max_length=200)


class StatusUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: TaskStatus


class AssignmentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    assigned_agent: str | None = Field(default=None, max_length=100)


class RoadmapItemAssignmentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    roadmap_item_id: str | None = Field(default=None, max_length=200)


def validate_roadmap_item_id(roadmap_item_id: str | None) -> str | None:
    """Waliduje identyfikator względem aktualnej definicji roadmapy YAML."""
    if roadmap_item_id is None:
        return None

    normalized_item_id = roadmap_item_id.strip()

    if not normalized_item_id:
        raise ValueError(
            "Identyfikator punktu roadmapy nie może być pusty"
        )

    service = ProjectProgressService(load_settings().database.url)

    try:
        if not service.has_item(normalized_item_id):
            raise ValueError(
                f"Nie znaleziono punktu roadmapy: {normalized_item_id}"
            )
    finally:
        service.close()

    return normalized_item_id


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
    roadmap_item_id: str | None = Query(default=None),
) -> list[Task]:
    try:
        return repository.list_recent(
            limit=limit,
            status=status,
            priority=priority,
            resource_class=resource_class,
            risk_level=risk_level,
            assigned_agent=assigned_agent,
            roadmap_item_id=roadmap_item_id,
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
    _: None = Depends(require_owner),
) -> Task:
    try:
        roadmap_item_id = validate_roadmap_item_id(
            payload.roadmap_item_id
        )

        return repository.create(
            title=payload.title,
            description=payload.description,
            priority=payload.priority,
            resource_class=payload.resource_class,
            risk_level=payload.risk_level,
            assigned_agent=payload.assigned_agent,
            roadmap_item_id=roadmap_item_id,
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
    _: None = Depends(require_owner),
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
    _: None = Depends(require_owner),
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


@router.patch(
    "/{task_id}/roadmap-item",
    response_model=TaskResponse,
)
def update_roadmap_item_assignment(
    payload: RoadmapItemAssignmentRequest,
    repository: RepositoryDependency,
    task_id: int = Path(ge=1),
    _: None = Depends(require_owner),
) -> Task:
    """Przypisuje zadanie do punktu roadmapy albo usuwa przypisanie."""
    try:
        roadmap_item_id = validate_roadmap_item_id(
            payload.roadmap_item_id
        )

        return repository.assign_roadmap_item(
            task_id,
            roadmap_item_id,
        )
    except TaskNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=503,
            detail="Repozytorium zadań jest niedostępne",
        ) from exc


@router.post(
    "/{task_id}/verify",
    response_model=VerificationResponse,
)
def verify_task_attempt(
    payload: VerifyAttemptRequest,
    repository: RepositoryDependency,
    task_id: int = Path(ge=1),
    _: None = Depends(require_owner),
) -> TaskAttempt:
    """Weryfikuje trwały rezultat ostatniej ukończonej próby zadania."""
    try:
        return repository.verify_attempt(
            task_id,
            result_content=payload.result_content,
            verifier_id=payload.verifier_id,
            reason=payload.reason,
        )
    except TaskNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (ValueError, TaskTransitionError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=503,
            detail="Repozytorium zadań jest niedostępne",
        ) from exc
