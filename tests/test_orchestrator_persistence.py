from app.brain.orchestrator import Orchestrator
from app.models.task import TaskPriority
from app.services.audit import AuditRepository
from app.services.tasks import TaskRepository


def test_orchestrator_loads_persistent_task(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'orchestrator.db'}"

    task_repository = TaskRepository(database_url)
    audit_repository = AuditRepository(database_url)

    try:
        persistent_task = task_repository.create(
            title="Zadanie trwałe",
        )

        orchestrator = Orchestrator(
            audit_repository=audit_repository,
        )

        loaded = orchestrator.register_persistent_task(
            persistent_task,
        )

        assert loaded.id == str(persistent_task.id)
        assert loaded.title == "Zadanie trwałe"
        assert len(orchestrator.context.tasks) == 1

        events = audit_repository.list_recent(limit=10)

        assert any(
            event.event_type == "task_loaded"
            for event in events
        )
    finally:
        task_repository.close()
        audit_repository.close()


def test_orchestrator_plan_uses_persistent_tasks(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'plan.db'}"

    task_repository = TaskRepository(database_url)
    audit_repository = AuditRepository(database_url)

    try:
        task_repository.create(
            title="Zadanie niskiego priorytetu",
            priority=TaskPriority.LOW,
        )
        task_repository.create(
            title="Zadanie wysokiego priorytetu",
            priority=TaskPriority.HIGH,
        )

        orchestrator = Orchestrator(
            audit_repository=audit_repository,
        )

        orchestrator.load_tasks(task_repository)
        plan = orchestrator.plan()

        assert len(plan) == 2
        assert plan[0]["title"] == "Zadanie wysokiego priorytetu"
    finally:
        task_repository.close()
        audit_repository.close()
