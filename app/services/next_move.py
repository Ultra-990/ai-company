from __future__ import annotations

from typing import Any

from app.services.roadmap_progress import ProjectProgressService
from app.services.tasks import TaskRepository


PRIORITY_ORDER = {
    "critical": 0,
    "high": 1,
    "normal": 2,
    "low": 3,
}


class NextMoveService:
    """Wybiera najbliższe zatwierdzone zadanie dostępne na roadmapie."""

    def __init__(
        self,
        repository: TaskRepository,
        progress_service: ProjectProgressService,
    ) -> None:
        self._repository = repository
        self._progress_service = progress_service

    @staticmethod
    def _serialize_task(task: Any) -> dict[str, Any]:
        return {
            "id": task.id,
            "title": task.title,
            "description": task.description,
            "status": task.status.value,
            "approval_status": task.approval_status.value,
            "priority": task.priority.value,
            "assigned_agent": task.assigned_agent,
            "roadmap_item_id": task.roadmap_item_id,
            "progress": task.progress,
            "created_at": task.created_at.isoformat(),
            "updated_at": task.updated_at.isoformat(),
        }

    @staticmethod
    def _dependencies_completed(
        phase: dict[str, Any],
        phases_by_id: dict[str, dict[str, Any]],
    ) -> tuple[bool, list[str]]:
        unresolved: list[str] = []

        for dependency_id in phase.get("depends_on", []):
            dependency = phases_by_id.get(dependency_id)

            if dependency is None:
                unresolved.append(dependency_id)
            elif dependency["status"] != "completed":
                unresolved.append(dependency["name"])

        return not unresolved, unresolved

    def get_next_move(self) -> dict[str, Any]:
        """Zwraca rekomendowane zadanie i informacje o blokadach."""
        progress = self._progress_service.get_progress()
        phases = progress["phases"]
        phases_by_id = {phase["id"]: phase for phase in phases}

        items_by_id: dict[str, dict[str, Any]] = {}

        for phase_position, phase in enumerate(phases):
            for item_position, item in enumerate(phase["items"]):
                items_by_id[item["id"]] = {
                    "phase": phase,
                    "item": item,
                    "phase_position": phase_position,
                    "item_position": item_position,
                }

        available: list[tuple[tuple[Any, ...], dict[str, Any]]] = []
        blocked: list[dict[str, Any]] = []
        unassigned_ready: list[dict[str, Any]] = []
        invalid_roadmap_item: list[dict[str, Any]] = []

        for task in self._repository.list_ready():
            task_data = self._serialize_task(task)
            roadmap_item_id = task.roadmap_item_id

            if roadmap_item_id is None:
                unassigned_ready.append(task_data)
                continue

            context = items_by_id.get(roadmap_item_id)

            if context is None:
                invalid_roadmap_item.append(
                    {
                        **task_data,
                        "reason": (
                            "Zadanie wskazuje punkt roadmapy, "
                            "który nie istnieje w aktualnym YAML."
                        ),
                    }
                )
                continue

            phase = context["phase"]
            item = context["item"]

            if item["status"] in {"blocked", "cancelled"}:
                blocked.append(
                    {
                        **task_data,
                        "reason": (
                            f"Punkt roadmapy „{item['name']}” ma status "
                            f"„{item['status']}”."
                        ),
                    }
                )
                continue

            dependencies_completed, unresolved = (
                self._dependencies_completed(phase, phases_by_id)
            )

            if not dependencies_completed:
                blocked.append(
                    {
                        **task_data,
                        "reason": (
                            "Oczekuje na ukończenie faz: "
                            + ", ".join(unresolved)
                            + "."
                        ),
                    }
                )
                continue

            available.append(
                (
                    (
                        PRIORITY_ORDER.get(task.priority.value, 99),
                        context["phase_position"],
                        context["item_position"],
                        task.created_at,
                        task.id,
                    ),
                    {
                        "task": task_data,
                        "roadmap": {
                            "phase_id": phase["id"],
                            "phase_name": phase["name"],
                            "item_id": item["id"],
                            "item_name": item["name"],
                            "item_status": item["status"],
                            "status_source": item["status_source"],
                        },
                        "reason": (
                            "Zadanie jest zatwierdzone, oczekujące "
                            "i dostępne po spełnieniu zależności fazowych."
                        ),
                    },
                )
            )

        available.sort(key=lambda candidate: candidate[0])

        return {
            "next_move": available[0][1] if available else None,
            "available_count": len(available),
            "blocked_count": len(blocked),
            "unassigned_ready_count": len(unassigned_ready),
            "invalid_roadmap_item_count": len(invalid_roadmap_item),
            "blocked": blocked,
            "unassigned_ready": unassigned_ready,
            "invalid_roadmap_item": invalid_roadmap_item,
        }
