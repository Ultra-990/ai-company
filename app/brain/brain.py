from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass
class BrainDecision:
    title: str
    rationale: str
    requires_approval: bool = False
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class BrainTask:
    id: str
    title: str
    status: str = "PENDING"
    priority: int = 0
    meta: Dict[str, Any] = field(default_factory=dict)


class Brain:
    """
    Mózg v1 — centralny moduł orkiestracji AI Company.
    Wersja bazowa: analiza, planowanie, delegowanie, raportowanie.
    """

    def __init__(self) -> None:
        self.decisions: List[BrainDecision] = []
        self.tasks: List[BrainTask] = []

    def add_task(self, task: BrainTask) -> None:
        self.tasks.append(task)

    def decide(self, title: str, rationale: str, requires_approval: bool = False) -> BrainDecision:
        decision = BrainDecision(
            title=title,
            rationale=rationale,
            requires_approval=requires_approval,
        )
        self.decisions.append(decision)
        return decision

    def report(self) -> Dict[str, Any]:
        return {
            "tasks_count": len(self.tasks),
            "decisions_count": len(self.decisions),
            "pending_tasks": [t for t in self.tasks if t.status == "PENDING"],
        }
