from __future__ import annotations

from enum import Enum

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field

from app.brain.orchestrator import Orchestrator
from app.core.config import load_settings
from app.models.task import (
    RiskLevel,
    ResourceClass,
    TaskPriority,
)
from app.services.audit import AuditRepository
from app.services.tasks import TaskRepository


router = APIRouter(prefix="/api/brain", tags=["brain"])

settings = load_settings()

task_repository = TaskRepository(settings.database.url)
audit_repository = AuditRepository(settings.database.url)
orchestrator = Orchestrator(audit_repository=audit_repository)


class TaskCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    priority: TaskPriority = TaskPriority.NORMAL
    resource_class: ResourceClass = ResourceClass.LIGHT
    risk_level: RiskLevel = RiskLevel.LOW
    assigned_agent: str | None = Field(default=None, max_length=100)


class TaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

    id: int
    title: str
    description: str | None
    status: str
    approval_status: str
    priority: str
    resource_class: str
    risk_level: str
    assigned_agent: str | None
    progress: int


@router.get("/tasks", response_model=list[TaskResponse])
def list_brain_tasks(
    limit: int = Query(default=50, ge=1, le=100),
) -> list[TaskResponse]:
    tasks = task_repository.list_recent(limit=limit)
    return [TaskResponse.model_validate(task) for task in tasks]


@router.post(
    "/tasks",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_brain_task(payload: TaskCreateRequest) -> TaskResponse:
    try:
        task = task_repository.create(
            title=payload.title,
            description=payload.description,
            priority=payload.priority,
            resource_class=payload.resource_class,
            risk_level=payload.risk_level,
            assigned_agent=payload.assigned_agent,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    orchestrator.register_persistent_task(task)

    return TaskResponse.model_validate(task)
