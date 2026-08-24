from __future__ import annotations

from typing import cast

import pytest

from app.models.task import Task
from app.services.production_executor import ProductionTaskExecutor


def test_production_executor_delegates_task_to_operation() -> None:
    task = cast(Task, object())
    received: list[Task] = []

    def operation(input_task: Task) -> str:
        received.append(input_task)
        return "Operacja zakończona pomyślnie"

    executor = ProductionTaskExecutor(operation)

    result = executor.execute(task)

    assert received == [task]
    assert result.success is True
    assert result.reason == "Operacja zakończona pomyślnie"


def test_production_executor_uses_default_reason_for_empty_result() -> None:
    task = cast(Task, object())

    executor = ProductionTaskExecutor(lambda _: "")

    result = executor.execute(task)

    assert result.success is True
    assert result.reason == "Zadanie wykonane pomyślnie"


def test_production_executor_propagates_operation_exception() -> None:
    task = cast(Task, object())

    def operation(_: Task) -> str:
        raise RuntimeError("błąd operacji")

    executor = ProductionTaskExecutor(operation)

    with pytest.raises(RuntimeError, match="błąd operacji"):
        executor.execute(task)
