from __future__ import annotations

from typing import Annotated

from app.services.agent_task_operation import AgentTaskOperation
from app.services.llm_task_operation import LLMTaskOperation
from app.services.tool_calling_task_operation import (
    ToolCallingLLMTaskOperation,
)

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel

from app.api.tasks import get_repository
from app.brain.orchestrator import Orchestrator
from app.models.task import TaskStatus
from app.services.executor import ExecutionResult, TaskExecutor
from app.services.agent_factory import get_agent_client, get_llm_client
from app.services.production_executor import ProductionTaskExecutor
from app.services.tasks import TaskRepository
from app.core.config import load_settings


router = APIRouter(prefix="/api/tasks", tags=["task-execution"])


class ExecutionResponse(BaseModel):
    success: bool
    reason: str
    task_id: int
    task_status: TaskStatus


class NotConfiguredExecutor:
    """Executor używany, gdy nie skonfigurowano właściwej implementacji."""

    def execute(self, task) -> ExecutionResult:
        raise RuntimeError(
            f"Brak skonfigurowanego wykonawcy dla zadania {task.id}"
        )


def get_task_executor() -> TaskExecutor:
    settings = load_settings()

    llm_client = get_llm_client(settings)
    if llm_client is not None:
        if getattr(settings, "tool_calling_enabled", False):
            operation = ToolCallingLLMTaskOperation(llm_client)
        else:
            operation = LLMTaskOperation(llm_client)

        return ProductionTaskExecutor(operation)

    if settings.agents.enabled:
        client = get_agent_client(settings)
        operation = AgentTaskOperation(client)
        return ProductionTaskExecutor(operation)

    return NotConfiguredExecutor()


def get_orchestrator() -> Orchestrator:
    return Orchestrator()


RepositoryDependency = Annotated[
    TaskRepository,
    Depends(get_repository),
]

OrchestratorDependency = Annotated[
    Orchestrator,
    Depends(get_orchestrator),
]

ExecutorDependency = Annotated[
    TaskExecutor,
    Depends(get_task_executor),
]


@router.post(
    "/execute-next",
    response_model=ExecutionResponse,
    status_code=status.HTTP_200_OK,
)
def execute_next_task(
    repository: RepositoryDependency,
    orchestrator: OrchestratorDependency,
    executor: ExecutorDependency,
    response: Response,
    worker_id: str = Query(
        default="api-worker",
        min_length=1,
        max_length=100,
    ),
) -> ExecutionResponse | Response:
    try:
        task = orchestrator.claim_next_task(
            repository,
            worker_id=worker_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    if task is None:
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    try:
        result = executor.execute(task)
    except Exception as exc:
        reason = f"Nieobsłużony wyjątek wykonawcy: {exc}"

        try:
            repository.block(task.id, reason=reason)
        except Exception as block_exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Nie można zablokować zadania po błędzie wykonawcy",
            ) from block_exc

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=reason,
        ) from exc

    try:
        if result.success:
            finalized_task = repository.complete(
                task.id,
                reason=result.reason,
            )
        else:
            finalized_task = repository.block(
                task.id,
                reason=result.reason,
            )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Nie można sfinalizować zadania",
        ) from exc

    return ExecutionResponse(
        success=result.success,
        reason=result.reason,
        task_id=finalized_task.id,
        task_status=finalized_task.status,
    )
