from datetime import datetime
from types import SimpleNamespace

from app.services.next_move import NextMoveService


def make_task(
    task_id: int,
    roadmap_item_id: str | None,
    priority: str = "normal",
) -> SimpleNamespace:
    return SimpleNamespace(
        id=task_id,
        title=f"Zadanie {task_id}",
        description=None,
        status=SimpleNamespace(value="pending"),
        approval_status=SimpleNamespace(value="approved"),
        priority=SimpleNamespace(value=priority),
        assigned_agent=None,
        roadmap_item_id=roadmap_item_id,
        progress=0,
        created_at=datetime(2026, 9, 10, 10, 0, task_id),
        updated_at=datetime(2026, 9, 10, 10, 0, task_id),
    )


class FakeRepository:
    def __init__(self, tasks):
        self.tasks = tasks

    def list_ready(self):
        return self.tasks


class FakeProgressService:
    def __init__(self, phases):
        self.phases = phases

    def get_progress(self):
        return {"phases": self.phases}


def make_item(item_id: str, status: str = "ready") -> dict:
    return {
        "id": item_id,
        "name": item_id,
        "status": status,
        "status_source": "roadmap",
    }


def make_phase(
    phase_id: str,
    name: str,
    status: str,
    items: list[dict],
    depends_on: list[str] | None = None,
) -> dict:
    return {
        "id": phase_id,
        "name": name,
        "status": status,
        "depends_on": depends_on or [],
        "items": items,
    }


def build_service(tasks, phases):
    return NextMoveService(
        FakeRepository(tasks),
        FakeProgressService(phases),
    )


def test_prefers_higher_priority_task():
    result = build_service(
        [
            make_task(1, "item-a", "normal"),
            make_task(2, "item-b", "high"),
        ],
        [
            make_phase(
                "phase-a",
                "Faza A",
                "ready",
                [make_item("item-a"), make_item("item-b")],
            )
        ],
    ).get_next_move()

    assert result["available_count"] == 2
    assert result["next_move"]["task"]["id"] == 2


def test_blocks_task_when_phase_dependency_is_not_completed():
    result = build_service(
        [make_task(1, "item-b")],
        [
            make_phase(
                "phase-a",
                "Faza A",
                "in_progress",
                [make_item("item-a")],
            ),
            make_phase(
                "phase-b",
                "Faza B",
                "planned",
                [make_item("item-b")],
                depends_on=["phase-a"],
            ),
        ],
    ).get_next_move()

    assert result["next_move"] is None
    assert result["blocked_count"] == 1
    assert "Faza A" in result["blocked"][0]["reason"]


def test_reports_unassigned_ready_task():
    result = build_service([make_task(1, None)], []).get_next_move()

    assert result["next_move"] is None
    assert result["unassigned_ready_count"] == 1
    assert result["unassigned_ready"][0]["id"] == 1
