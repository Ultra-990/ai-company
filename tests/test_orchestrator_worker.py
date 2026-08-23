from pathlib import Path

from app.brain.orchestrator import Orchestrator
from app.models.task import TaskStatus
from app.services.audit import AuditRepository
from app.services.tasks import TaskRepository


def test_orchestrator_claims_and_registers_next_task(
    tmp_path: Path,
) -> None:
    database_url = f"sqlite:///{tmp_path / 'tasks.sqlite3'}"
    task_repository = TaskRepository(database_url)
    audit_repository = AuditRepository(database_url)

    try:
        created = task_repository.create(
            title="Zadanie dla orkiestratora",
        )
        task_repository.approve(created.id)

        orchestrator = Orchestrator(
            audit_repository=audit_repository,
        )

        claimed = orchestrator.claim_next_task(
            task_repository,
            worker_id="orchestrator-worker",
        )

        assert claimed is not None
        assert claimed.id == created.id
        assert claimed.status is TaskStatus.IN_PROGRESS
        assert len(orchestrator.context.tasks) == 1
        assert orchestrator.context.tasks[0].id == str(created.id)
    finally:
        audit_repository.close()
        task_repository.close()


def test_orchestrator_returns_none_for_empty_queue(
    tmp_path: Path,
) -> None:
    database_url = f"sqlite:///{tmp_path / 'tasks.sqlite3'}"
    task_repository = TaskRepository(database_url)
    audit_repository = AuditRepository(database_url)

    try:
        orchestrator = Orchestrator(
            audit_repository=audit_repository,
        )

        assert (
            orchestrator.claim_next_task(
                task_repository,
                worker_id="orchestrator-worker",
            )
            is None
        )
        assert orchestrator.context.tasks == []
    finally:
        audit_repository.close()
        task_repository.close()
