from __future__ import annotations

from collections.abc import Generator
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from pydantic import BaseModel, ConfigDict, Field

from app.api.owner import require_owner
from app.core.config import load_settings
from app.models.approval import ApprovalRequestStatus
from app.services.approved_tool_execution import (
    ApprovedToolExecutionService,
    PendingToolExecutionStore,
)
from app.services.approvals import (
    ApprovalExecutionDeniedError,
    ApprovalExecutionInProgressError,
    ApprovalRepository,
    ApprovalRequestNotFoundError,
    ApprovalStateConflictError,
)


router = APIRouter(
    prefix="/api/approvals",
    tags=["approvals"],
    dependencies=[Depends(require_owner)],
)


class ApprovalResponse(BaseModel):
    """
    Publiczna reprezentacja wniosku.

    Celowo nie zawiera arguments_json ani treści pliku.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    task_id: int
    operation_type: str
    description: str
    status: ApprovalRequestStatus
    tool_name: str | None
    arguments_digest: str | None
    created_at: datetime
    resolved_at: datetime | None
    executed_at: datetime | None
    reason: str | None


class ResolutionRequest(BaseModel):
    reason: str = Field(
        default="Decyzja właściciela",
        min_length=1,
        max_length=500,
    )


def get_approval_repository() -> Generator[ApprovalRepository, None, None]:
    repository = ApprovalRepository(load_settings().database.url)
    try:
        yield repository
    finally:
        repository.close()


def get_execution_service() -> Generator[
    ApprovedToolExecutionService,
    None,
    None,
]:
    database_url = load_settings().database.url
    approval_repository = ApprovalRepository(database_url)
    pending_store = PendingToolExecutionStore(database_url)

    try:
        yield ApprovedToolExecutionService(
            approval_repository,
            pending_store,
        )
    finally:
        pending_store.close()
        approval_repository.close()


ApprovalRepositoryDependency = Annotated[
    ApprovalRepository,
    Depends(get_approval_repository),
]

ExecutionServiceDependency = Annotated[
    ApprovedToolExecutionService,
    Depends(get_execution_service),
]


@router.get("/pending", response_model=list[ApprovalResponse])
def list_pending(
    repository: ApprovalRepositoryDependency,
    limit: int = Query(default=50, ge=1, le=100),
) -> list:
    return repository.list_pending(limit=limit)


@router.get("/{approval_request_id}", response_model=ApprovalResponse)
def get_approval(
    approval_request_id: int = Path(ge=1),
    repository: ApprovalRepositoryDependency = None,
):
    try:
        return repository.get_required(approval_request_id)
    except ApprovalRequestNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post(
    "/{approval_request_id}/approve",
    response_model=ApprovalResponse,
)
def approve(
    payload: ResolutionRequest,
    approval_request_id: int = Path(ge=1),
    repository: ApprovalRepositoryDependency = None,
):
    try:
        return repository.approve(
            approval_request_id,
            reason=payload.reason,
        )
    except ApprovalRequestNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ApprovalStateConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post(
    "/{approval_request_id}/reject",
    response_model=ApprovalResponse,
)
def reject(
    payload: ResolutionRequest,
    approval_request_id: int = Path(ge=1),
    repository: ApprovalRepositoryDependency = None,
):
    try:
        return repository.reject(
            approval_request_id,
            reason=payload.reason,
        )
    except ApprovalRequestNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ApprovalStateConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/{approval_request_id}/execute")
def execute(
    approval_request_id: int = Path(ge=1),
    service: ExecutionServiceDependency = None,
) -> dict[str, object]:
    """
    Wykonuje zatwierdzone narzędzie bez argumentów w request body.

    Wartości path, content i inne argumenty są pobierane wyłącznie
    z PendingToolExecutionStore.
    """
    try:
        service.execute(approval_request_id)
    except ApprovalRequestNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ApprovalExecutionInProgressError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ApprovalExecutionDeniedError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Wykonanie zatwierdzonego narzędzia nie powiodło się.",
        ) from exc

    return {
        "approval_request_id": approval_request_id,
        "status": "executed",
    }
