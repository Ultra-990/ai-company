from dataclasses import dataclass
from typing import List

from app.brain.context_manager import Task


PRIORITY_ORDER = {
    "high": 3,
    "medium": 2,
    "low": 1,
}


@dataclass
class PlanStep:
    title: str
    detail: str = ""
    priority: str = "medium"


class Planner:
    def build_plan(self, tasks: List[Task]) -> List[PlanStep]:
        ordered = sorted(
            tasks,
            key=lambda t: PRIORITY_ORDER.get(str(t.priority).lower(), 0),
            reverse=True,
        )
        return [
            PlanStep(
                title=task.title,
                detail=task.description,
                priority=task.priority,
            )
            for task in ordered
        ]
