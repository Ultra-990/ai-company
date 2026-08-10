from __future__ import annotations

from datetime import datetime
from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from app.core.config import Settings, load_settings
from app.core.safety import OperationType, SafetyGate
from app.services.audit import AuditRepository


router = APIRouter(prefix="/api", tags=["system"])

_settings: Settings = load_settings()
_safety_gate = SafetyGate(_settings)


@lru_cache(maxsize=1)
def get_audit_repository() -> AuditRepository:
    """Tworzy główne repozytorium audytu dopiero przy pierwszym użyciu."""

    return AuditRepository(_settings.database.url)


class SystemStatusResponse(BaseModel):
    name: str
    version: str
    environment: str
    agents_enabled: bool
    emergency_stop: bool
    finance_mode: str
    external_actions_enabled: bool
    financial_actions_enabled: bool
    publishing_enabled: bool
    audit_logging_enabled: bool


class SafetyCheckResponse(BaseModel):
    operation: OperationType
    decision: str
    allowed: bool
    reason: str


class AuditEventResponse(BaseModel):
    id: int
    created_at: datetime
    event_type: str
    operation: str
    decision: str
    allowed: bool
    reason: str


def _record_audit_event(
    repository: AuditRepository,
    *,
    event_type: str,
    operation: str,
    decision: str,
    allowed: bool,
    reason: str,
) -> None:
    if not _settings.safety.audit_logging_enabled:
        return

    try:
        repository.record(
            event_type=event_type,
            operation=operation,
            decision=decision,
            allowed=allowed,
            reason=reason,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Nie można zapisać wymaganego zdarzenia audytowego.",
        ) from exc


@router.get(
    "/system/status",
    response_model=SystemStatusResponse,
)
def get_system_status() -> SystemStatusResponse:
    """Zwraca bezpieczny, niezawierający sekretów stan systemu."""

    return SystemStatusResponse(
        name=_settings.system.name,
        version=_settings.system.version,
        environment=_settings.system.environment,
        agents_enabled=_settings.agents.enabled,
        emergency_stop=_settings.safety.emergency_stop,
        finance_mode=_settings.finance.mode,
        external_actions_enabled=(
            _settings.safety.external_actions_enabled
        ),
        financial_actions_enabled=(
            _settings.safety.financial_actions_enabled
        ),
        publishing_enabled=_settings.safety.publishing_enabled,
        audit_logging_enabled=_settings.safety.audit_logging_enabled,
    )


@router.get(
    "/safety/check/{operation}",
    response_model=SafetyCheckResponse,
)
def check_operation(
    operation: str,
    audit_repository: AuditRepository = Depends(get_audit_repository),
) -> SafetyCheckResponse:
    """
    Sprawdza operację bez jej wykonywania i zapisuje wynik w audycie.

    Endpoint nie przyjmuje zatwierdzenia Właściciela, dlatego nie może
    służyć do obchodzenia bramki bezpieczeństwa.
    """

    try:
        operation_type = OperationType(operation)
    except ValueError as exc:
        allowed_values = ", ".join(item.value for item in OperationType)
        reason = (
            f"Nieznany typ operacji. Dozwolone wartości: "
            f"{allowed_values}"
        )

        _record_audit_event(
            audit_repository,
            event_type="safety_check",
            operation=operation[:64],
            decision="rejected",
            allowed=False,
            reason=reason,
        )

        raise HTTPException(
            status_code=400,
            detail=reason,
        ) from exc

    result = _safety_gate.evaluate(
        operation_type,
        owner_approved=False,
    )

    _record_audit_event(
        audit_repository,
        event_type="safety_check",
        operation=result.operation.value,
        decision=result.decision.value,
        allowed=result.allowed,
        reason=result.reason,
    )

    return SafetyCheckResponse(
        operation=result.operation,
        decision=result.decision.value,
        allowed=result.allowed,
        reason=result.reason,
    )


@router.get(
    "/audit/events",
    response_model=list[AuditEventResponse],
)
def list_audit_events(
    limit: int = Query(default=50, ge=1, le=100),
    audit_repository: AuditRepository = Depends(get_audit_repository),
) -> list[AuditEventResponse]:
    """Zwraca ograniczoną listę ostatnich zdarzeń audytowych."""

    try:
        events = audit_repository.list_recent(limit=limit)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Nie można odczytać dziennika audytowego.",
        ) from exc

    return [
        AuditEventResponse(
            id=event.id,
            created_at=event.created_at,
            event_type=event.event_type,
            operation=event.operation,
            decision=event.decision,
            allowed=event.allowed,
            reason=event.reason,
        )
        for event in events
    ]
