from __future__ import annotations

from app.models.task import Task
from app.services.executor import ExecutionResult
from app.services.task_operation import TaskOperation


class ProductionTaskExecutor:
    """Executor delegujący wykonanie do wstrzykniętej operacji domenowej."""

    def __init__(self, operation: TaskOperation) -> None:
        self._operation = operation

    def execute(self, task: Task) -> ExecutionResult:
        """
        Wykonuje operację dla zadania.

        Wyjątki są celowo przepuszczane wyżej, aby istniejący mechanizm
        orkiestratora/API mógł zablokować zadanie i zwrócić odpowiedni błąd.
        """
        reason = self._operation(task)

        return ExecutionResult(
            success=True,
            reason=reason or "Zadanie wykonane pomyślnie",
        )
