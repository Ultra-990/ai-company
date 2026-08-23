from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel

from app.api.tasks import get_repository
from app.brain.orchestrator import Orchestrator
from app.models.task import TaskStatus
from app.services.executor import ExecutionResult, TaskExecutor
from app.services.tasks import TaskRepository
from app.services.worker import TaskWorker


router = APIRouter(prefix="/api/tasks", tags=["task-execution"])


class ExecutionResponse(BaseModel):
    success: bool
    reason: str
    task_id: int
    task_status: TaskStatus


class NotConfiguredExecutor:
    """Zastępczy wykonawca — wymaga podmiany na właściwą implementację."""

    def execute(self, task) -> ExecutionResult:
        return ExecutionResult(
            success=True,
            reason=f"Zadanie {task.id} wykonane przez wykonawcę domyślnego",
        )


def get_task_executor() -> TaskExecutor:
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
