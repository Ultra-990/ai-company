from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any, Dict, List

from app.brain.audit_logger import AuditLogger
from app.brain.context_manager import (
    ContextManager,
    Task as ContextTask,
)
from app.brain.persistent_audit import PersistentAuditLogger
from app.brain.planner import Planner
from app.brain.reporter import Reporter
from app.brain.safety_gate import SafetyGate
from app.models.task import Task as PersistentTask
from app.services.audit import AuditRepository
from app.services.executor import ExecutionResult, TaskExecutor
from app.services.tasks import TaskRepository
from app.services.worker import TaskWorker


class Orchestrator:
    def __init__(
        self,
        context: ContextManager | None = None,
        planner: Planner | None = None,
        safety_gate: SafetyGate | None = None,
        audit_logger: AuditLogger | None = None,
        reporter: Reporter | None = None,
        audit_repository: AuditRepository | None = None,
    ):
        self.context = context or ContextManager()
        self.planner = planner or Planner()
        self.safety_gate = safety_gate or SafetyGate()
        self.reporter = reporter or Reporter()

        local_logger = audit_logger or AuditLogger()

        if audit_repository is not None:
            self.audit_logger = PersistentAuditLogger(
                repository=audit_repository,
                fallback=local_logger,
            )
        else:
            self.audit_logger = local_logger

    def register_task(self, task: ContextTask) -> ContextTask:
        self.context.add_task(task)
        self.audit_logger.log(
            event_type="task_registered",
            message=f"Registered task: {task.title}",
            payload={
                "task_id": task.id,
                "title": task.title,
                "priority": task.priority,
                "resource_class": task.resource_class,
                "risk_level": task.risk_level,
            },
        )
        return task

    def register_persistent_task(
        self,
        task: PersistentTask,
    ) -> ContextTask:
        context_task = ContextTask(
            id=str(task.id),
            title=task.title,
            description=task.description or "",
            status=task.status.value,
            priority=task.priority.value,
            resource_class=task.resource_class.value,
            risk_level=task.risk_level.value,
            assigned_agent=task.assigned_agent,
            queued_at=(
                task.queued_at.isoformat()
                if task.queued_at is not None
                else None
            ),
            started_at=(
                task.started_at.isoformat()
                if task.started_at is not None
                else None
            ),
            completed_at=(
                task.completed_at.isoformat()
                if task.completed_at is not None
                else None
            ),
            created_at=(
                task.created_at.isoformat()
                if task.created_at is not None
                else None
            ),
            updated_at=(
                task.updated_at.isoformat()
                if task.updated_at is not None
                else None
            ),
        )

        self.context.add_task(context_task)

        self.audit_logger.log(
            event_type="task_loaded",
            message=f"Loaded persistent task: {task.title}",
            payload={
                "task_id": task.id,
                "title": task.title,
            },
        )

        return context_task

    def load_tasks(
        self,
        repository: Any,
        *,
        limit: int = 100,
    ) -> list[ContextTask]:
        persistent_tasks = repository.list_recent(limit=limit)
        self.context.clear_tasks()

        return [
            self.register_persistent_task(task)
            for task in reversed(persistent_tasks)
        ]

    def claim_next_task(
        self,
        repository: TaskRepository,
        *,
        worker_id: str,
    ) -> PersistentTask | None:
        """Atomowo pobiera następne zadanie i ładuje je do kontekstu."""
        worker = TaskWorker(repository, worker_id=worker_id)
        task = worker.claim_next()

        if task is not None:
            self.register_persistent_task(task)

        return task

    def execute_next_task(
        self,
        repository: TaskRepository,
        executor: TaskExecutor,
        *,
        worker_id: str,
    ) -> ExecutionResult | None:
        """Pobiera i wykonuje następne zatwierdzone zadanie z kolejki."""
        task = self.claim_next_task(
            repository,
            worker_id=worker_id,
        )

        if task is None:
            return None

        result = executor.execute(task)

        if result.success:
            repository.complete(
                task.id,
                reason=result.reason,
            )
        else:
            repository.block(
                task.id,
                reason=result.reason,
            )

        return result

    def plan(self) -> List[Dict[str, Any]]:
        plan = self.planner.build_plan(self.context.tasks)
        serialized_plan = [self._serialize_item(step) for step in plan]

        self.audit_logger.log(
            event_type="plan_created",
            message="Plan created from current tasks",
            payload={"steps": len(serialized_plan)},
        )
        return serialized_plan

    def run_safety_check(
        self,
        action_type: str,
        requires_approval: bool = False,
    ) -> Dict[str, Any]:
        result = self.safety_gate.approve(
            action_type,
            requires_approval,
        )

        self.audit_logger.log(
            event_type="safety_check",
            message=result.reason,
            payload={
                "action_type": action_type,
                "requires_approval": requires_approval,
                "allowed": result.allowed,
            },
        )

        return {
            "allowed": result.allowed,
            "reason": result.reason,
        }

    def report(self) -> Dict[str, Any]:
        report = self.reporter.build_report(self.context)
        serialized_report = self._serialize_item(report)

        self.audit_logger.log(
            event_type="report_generated",
            message="Project report generated",
            payload=serialized_report,
        )
        return serialized_report

    def _serialize_item(self, item: Any) -> Any:
        if is_dataclass(item):
            return asdict(item)
        if isinstance(item, list):
            return [self._serialize_item(value) for value in item]
        if isinstance(item, dict):
            return {
                key: self._serialize_item(value)
                for key, value in item.items()
            }
        return item
