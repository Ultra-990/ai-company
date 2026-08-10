from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.config import Settings, load_settings
from app.core.safety import OperationType, SafetyGate


router = APIRouter(prefix="/api", tags=["system"])

_settings: Settings = load_settings()
_safety_gate = SafetyGate(_settings)


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
def check_operation(operation: str) -> SafetyCheckResponse:
    """
    Sprawdza operację bez jej wykonywania.

    Endpoint nie przyjmuje zatwierdzenia Właściciela, dlatego nie może
    służyć do obchodzenia bramki bezpieczeństwa.
    """

    try:
        operation_type = OperationType(operation)
    except ValueError as exc:
        allowed_values = ", ".join(item.value for item in OperationType)
        raise HTTPException(
            status_code=400,
            detail=(
                f"Nieznany typ operacji. Dozwolone wartości: "
                f"{allowed_values}"
            ),
        ) from exc

    result = _safety_gate.evaluate(
        operation_type,
        owner_approved=False,
    )

    return SafetyCheckResponse(
        operation=result.operation,
        decision=result.decision.value,
        allowed=result.allowed,
        reason=result.reason,
    )
