import pytest

from app.domain import ContractError, TaskContract, TaskStatus
from app.domain.adapters.orchestrator import (
    DomainRegistry,
    TaskContractAdapter,
)


def test_task_contract_adapter_exposes_domain_task():
    task = TaskContract("task-1", "Build")
    adapter = TaskContractAdapter(task)

    assert adapter.task is task
    assert adapter.task_id == "task-1"
    assert adapter.status == TaskStatus.PENDING


def test_task_contract_adapter_transitions_task():
    task = TaskContract("task-1", "Build")
    adapter = TaskContractAdapter(task)

    adapter.transition(TaskStatus.READY)
    adapter.transition(TaskStatus.RUNNING)

    assert task.status == TaskStatus.RUNNING
    assert adapter.status == TaskStatus.RUNNING


def test_task_contract_adapter_rejects_invalid_transition():
    task = TaskContract("task-1", "Build")
    adapter = TaskContractAdapter(task)

    with pytest.raises(ContractError):
        adapter.transition(TaskStatus.SUCCEEDED)


def test_domain_registry_registers_and_returns_task():
    registry = DomainRegistry()
    task = TaskContract("task-1", "Build")

    registry.register_task(task)

    assert registry.get_task("task-1") is task


def test_domain_registry_rejects_duplicate_task():
    registry = DomainRegistry()
    task = TaskContract("task-1", "Build")

    registry.register_task(task)

    with pytest.raises(ContractError):
        registry.register_task(TaskContract("task-1", "Other"))


def test_domain_registry_rejects_unknown_task():
    registry = DomainRegistry()

    with pytest.raises(ContractError):
        registry.get_task("missing")
