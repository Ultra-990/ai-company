from app.domain import TaskContract
from app.domain.adapters.orchestrator import (
    DomainRegistry,
    TaskContractAdapter,
)


def test_task_contract_flows_through_registry_and_adapter():
    task = TaskContract(
        id="integration-task-1",
        title="Integration test task",
    )

    registry = DomainRegistry()
    registry.register_task(task)

    registered = registry.get_task(task.id)
    adapter = TaskContractAdapter(registered)

    assert registered is task
    assert adapter.task_id == "integration-task-1"
    assert adapter.as_dict() == {
        "id": "integration-task-1",
        "title": "Integration test task",
        "status": "pending",
        "parent_id": None,
        "retry_count": 0,
        "max_retries": 0,
        "metadata": {},
    }
