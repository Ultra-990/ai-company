import inspect

import pytest

from app.brain.orchestrator import Orchestrator
from app.domain import TaskContract
from app.domain.adapters.orchestrator import (
    DomainRegistry,
    TaskContractAdapter,
)


def test_task_contract_is_available_to_orchestrator():
    task = TaskContract(
        id="orchestrator-task-1",
        title="Orchestrator integration task",
    )

    registry = DomainRegistry()
    registry.register_task(task)

    registered = registry.get_task(task.id)
    adapter = TaskContractAdapter(registered)

    assert adapter.task_id == task.id
    assert adapter.status == "pending"
    assert registered is task
    assert Orchestrator is not None


def test_orchestrator_public_api_is_inspectable():
    public_methods = {
        name
        for name, member in inspect.getmembers(Orchestrator, inspect.isfunction)
        if not name.startswith("_")
    }

    assert public_methods
