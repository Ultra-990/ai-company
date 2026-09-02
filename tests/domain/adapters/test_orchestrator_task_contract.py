from app.brain.orchestrator import Orchestrator
from app.domain import TaskContract
from app.domain.adapters.orchestrator import (
    DomainRegistry,
    TaskContractAdapter,
)


def test_orchestrator_registers_task_contract_and_returns_adapter():
    registry = DomainRegistry()
    orchestrator = Orchestrator(domain_registry=registry)

    task = TaskContract(
        id="orchestrator-contract-1",
        title="Contract integration task",
    )

    adapter = orchestrator.register_task_contract(task)

    assert isinstance(adapter, TaskContractAdapter)
    assert adapter.task_id == task.id
    assert adapter.status == "pending"
    assert registry.get_task(task.id) is task
