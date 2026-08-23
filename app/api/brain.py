from __future__ import annotations

from typing import Any, Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field

from app.api.system import get_audit_repository
from app.api.tasks import get_repository
from app.brain.orchestrator import Orchestrator
from app.models.task import RiskLevel, ResourceClass, TaskPriority
from app.services.audit import AuditRepository
from app.services.tasks import TaskRepository


router = APIRouter(prefix="/api/brain", tags=["brain"])


def get_orchestrator(
    audit_repository: Annotated[
        AuditRepository,
        Depends(get_audit_repository),
    ],
) -> Orchestrator:
    return Orchestrator(audit_repository=audit_repository)


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


class PlanResponse(BaseModel):
    steps: list[Any]


class SafetyCheckRequest(BaseModel):
    action_type: str = Field(..., min_length=1, max_length=100)
    requires_approval: bool = False


class SafetyCheckResponse(BaseModel):
    allowed: bool
    reason: str


@router.get("/tasks", response_model=list[TaskResponse])
def list_brain_tasks(
    limit: int = Query(default=50, ge=1, le=100),
    task_repository: TaskRepository = Depends(get_repository),
) -> list[TaskResponse]:
    tasks = task_repository.list_recent(limit=limit)
    return [TaskResponse.model_validate(task) for task in tasks]


@router.post(
    "/tasks",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_brain_task(
    payload: TaskCreateRequest,
    task_repository: TaskRepository = Depends(get_repository),
    orchestrator: Orchestrator = Depends(get_orchestrator),
) -> TaskResponse:
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


@router.post("/plan", response_model=PlanResponse)
def create_plan(
    task_repository: TaskRepository = Depends(get_repository),
    orchestrator: Orchestrator = Depends(get_orchestrator),
) -> PlanResponse:
    orchestrator.load_tasks(task_repository)
    result = orchestrator.plan()

    if result is None:
        return PlanResponse(steps=[])

    if isinstance(result, list):
        return PlanResponse(steps=result)

    if isinstance(result, tuple):
        return PlanResponse(steps=list(result))

    if hasattr(result, "steps"):
        return PlanResponse(steps=list(result.steps))

    return PlanResponse(steps=[result])


@router.get("/report")
def get_report(
    task_repository: TaskRepository = Depends(get_repository),
    orchestrator: Orchestrator = Depends(get_orchestrator),
) -> dict[str, Any]:
    orchestrator.load_tasks(task_repository)
    report = orchestrator.report()

    if isinstance(report, dict):
        return report

    if hasattr(report, "model_dump"):
        return report.model_dump()

    if hasattr(report, "__dict__"):
        return dict(report.__dict__)

    return {"report": report}


@router.post("/safety-check", response_model=SafetyCheckResponse)
def safety_check(
    payload: SafetyCheckRequest,
    orchestrator: Orchestrator = Depends(get_orchestrator),
) -> SafetyCheckResponse:
    result = orchestrator.run_safety_check(
        action_type=payload.action_type,
        requires_approval=payload.requires_approval,
    )

    if hasattr(result, "allowed") and hasattr(result, "reason"):
        return SafetyCheckResponse(
            allowed=bool(result.allowed),
            reason=str(result.reason),
        )

    if isinstance(result, dict):
        return SafetyCheckResponse.model_validate(result)

    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Safety check returned an invalid result",
    )
