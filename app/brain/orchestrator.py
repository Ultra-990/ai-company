from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any, Dict, List

from app.brain.audit_logger import AuditLogger
from app.brain.context_manager import ContextManager, Task
from app.brain.planner import Planner
from app.brain.reporter import Reporter
from app.brain.safety_gate import SafetyGate


class Orchestrator:
    def __init__(
        self,
        context: ContextManager | None = None,
        planner: Planner | None = None,
        safety_gate: SafetyGate | None = None,
        audit_logger: AuditLogger | None = None,
        reporter: Reporter | None = None,
    ):
        self.context = context or ContextManager()
        self.planner = planner or Planner()
        self.safety_gate = safety_gate or SafetyGate()
        self.audit_logger = audit_logger or AuditLogger()
        self.reporter = reporter or Reporter()

    def register_task(self, task: Task) -> Task:
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

    def plan(self) -> List[Dict[str, Any]]:
        plan = self.planner.build_plan(self.context.tasks)
        serialized_plan = [self._serialize_item(step) for step in plan]

        self.audit_logger.log(
            event_type="plan_created",
            message="Plan created from current tasks",
            payload={"steps": len(serialized_plan)},
        )
        return serialized_plan

    def run_safety_check(self, action_type: str, requires_approval: bool = False) -> Dict[str, Any]:
        result = self.safety_gate.approve(action_type, requires_approval)

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
            return {key: self._serialize_item(value) for key, value in item.items()}
        return item
