from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.models.task import Task


@dataclass(frozen=True)
class ExecutionResult:
    """Wynik operacji wykonawcy; success nie oznacza odbioru zadania."""

    success: bool
    reason: str
    result_content: str | None = None

    def __post_init__(self) -> None:
        if not self.reason.strip():
            raise ValueError("Powód wyniku wykonania nie może być pusty")

        if self.result_content is not None and not self.result_content.strip():
            raise ValueError("Treść wyniku wykonania nie może być pusta")


class TaskExecutor(Protocol):
    """Kontrakt komponentu wykonującego zadania."""

    def execute(self, task: Task) -> ExecutionResult:
        """Wykonuje zadanie i zwraca wynik operacji."""
        ...
