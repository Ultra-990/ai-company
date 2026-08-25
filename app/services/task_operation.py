from __future__ import annotations

from typing import Protocol

from app.models.task import Task


class TaskOperation(Protocol):
    """Operacja domenowa wykonywana dla zadania."""

    def __call__(self, task: Task) -> str:
        """Wykonuje operację i zwraca opis rezultatu."""
        ...
