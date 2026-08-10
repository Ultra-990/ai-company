from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Final

from app.core.config import Settings


class OperationType(str, Enum):
    READ_ONLY = "read_only"
    INTERNAL_WRITE = "internal_write"
    EXTERNAL_ACTION = "external_action"
    FINANCIAL_ACTION = "financial_action"
    PUBLISHING = "publishing"
    SYSTEM_CHANGE = "system_change"
    MEMORY_PERMANENT_CHANGE = "memory_permanent_change"


class SafetyDecision(str, Enum):
    ALLOWED = "allowed"
    APPROVAL_REQUIRED = "approval_required"
    BLOCKED = "blocked"


@dataclass(frozen=True)
class SafetyResult:
    decision: SafetyDecision
    reason: str
    operation: OperationType

    @property
    def allowed(self) -> bool:
        return self.decision == SafetyDecision.ALLOWED


ALWAYS_REQUIRE_APPROVAL: Final[frozenset[OperationType]] = frozenset(
    {
        OperationType.SYSTEM_CHANGE,
        OperationType.MEMORY_PERMANENT_CHANGE,
    }
)


class SafetyGate:
    """Centralna bramka bezpieczeństwa dla operacji systemowych."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def evaluate(
        self,
        operation: OperationType,
        *,
        owner_approved: bool = False,
    ) -> SafetyResult:
        if not isinstance(operation, OperationType):
            raise TypeError("operation musi być wartością OperationType")

        if self._settings.safety.emergency_stop:
            return SafetyResult(
                decision=SafetyDecision.BLOCKED,
                reason="Emergency Stop jest aktywny.",
                operation=operation,
            )

        if operation == OperationType.READ_ONLY:
            return SafetyResult(
                decision=SafetyDecision.ALLOWED,
                reason="Operacja tylko do odczytu jest dozwolona.",
                operation=operation,
            )

        if operation == OperationType.INTERNAL_WRITE:
            if self._settings.agents.require_owner_approval and not owner_approved:
                return SafetyResult(
                    decision=SafetyDecision.APPROVAL_REQUIRED,
                    reason="Zapis wewnętrzny wymaga zgody Właściciela.",
                    operation=operation,
                )

            return SafetyResult(
                decision=SafetyDecision.ALLOWED,
                reason="Zapis wewnętrzny został zatwierdzony.",
                operation=operation,
            )

        if operation in ALWAYS_REQUIRE_APPROVAL:
            if not owner_approved:
                return SafetyResult(
                    decision=SafetyDecision.APPROVAL_REQUIRED,
                    reason="Operacja krytyczna wymaga zgody Właściciela.",
                    operation=operation,
                )

            return SafetyResult(
                decision=SafetyDecision.ALLOWED,
                reason="Operacja krytyczna została zatwierdzona.",
                operation=operation,
            )

        feature_enabled = {
            OperationType.EXTERNAL_ACTION:
                self._settings.safety.external_actions_enabled,
            OperationType.FINANCIAL_ACTION:
                self._settings.safety.financial_actions_enabled,
            OperationType.PUBLISHING:
                self._settings.safety.publishing_enabled,
        }.get(operation)

        if feature_enabled is False:
            return SafetyResult(
                decision=SafetyDecision.BLOCKED,
                reason="Ten typ operacji jest wyłączony w konfiguracji.",
                operation=operation,
            )

        if not owner_approved:
            return SafetyResult(
                decision=SafetyDecision.APPROVAL_REQUIRED,
                reason="Operacja wymaga zgody Właściciela.",
                operation=operation,
            )

        return SafetyResult(
            decision=SafetyDecision.ALLOWED,
            reason="Operacja została zatwierdzona przez Właściciela.",
            operation=operation,
        )
