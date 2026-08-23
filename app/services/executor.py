from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.models.task import Task


@dataclass(frozen=True)
class ExecutionResult:
    """Wynik wykonania zadania przez wykonawcę."""

    success: bool
    reason: str

    def __post_init__(self) -> None:
        if not self.reason.strip():
            raise ValueError("Powód wyniku wykonania nie może być pusty")


class TaskExecutor(Protocol):
    """Kontrakt komponentu wykonującego zadania."""

    def execute(self, task: Task) -> ExecutionResult:
        """Wykonuje zadanie i zwraca wynik operacji."""
        ...
