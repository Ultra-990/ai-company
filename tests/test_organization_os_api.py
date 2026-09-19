from sqlalchemy import select

from app.models.organization import OrganizationUnit
from app.models.project import Project, ProjectStatus
from app.models.task import (
    ApprovalStatus,
    ResourceClass,
    RiskLevel,
    Task,
    TaskPriority,
    TaskStatus,
)
from app.services.tasks import TaskRepository
from tests.conftest import OWNER_HEADERS, WORKER_HEADERS


def test_organization_os_uses_the_isolated_test_database(client) -> None:
    overview = client.get("/api/organization-os/overview")
    tree = client.get("/api/organization-os/tree")

    assert overview.status_code == 200
    assert tree.status_code == 200
    assert overview.json()["department_count"] == 12
    assert tree.json()["nodes"][0]["key"] == "ai-company"
    assert sum(
        node["weight"]
        for node in tree.json()["nodes"][0]["children"]
    ) == 100
    assert tree.json()["dependencies"]
    assert {
        "source_key": "platform",
        "target_key": "strategy",
        "relation_type": "depends_on",
        "description": "Platforma realizuje priorytety strategiczne.",
    } in tree.json()["dependencies"]


def test_next_move_ignores_unassigned_history_but_uses_project_tasks(
    client,
    task_repository: TaskRepository,
) -> None:
    historical_task = task_repository.create(
        title="Historyczna blokada",
        description="To zadanie nie należy jeszcze do projektu.",
    )
    task_repository.transition(historical_task.id, TaskStatus.BLOCKED)

    with task_repository._session_factory() as session:
        platform = session.scalar(
            select(OrganizationUnit).where(
                OrganizationUnit.os_key == "platform"
            )
        )
        assert platform is not None

        project = Project(
            name="Projekt testowy Organization OS",
            business_goal="Weryfikacja priorytetyzacji zadań projektu.",
            status=ProjectStatus.IN_PROGRESS,
            organization_unit_id=platform.id,
        )
        session.add(project)
        session.flush()

        tracked_task = Task(
            project_id=project.id,
            title="Blokada przypisana do projektu",
            description="Ta blokada ma być widoczna dla Organization OS.",
            status=TaskStatus.BLOCKED,
            approval_status=ApprovalStatus.APPROVED,
            priority=TaskPriority.HIGH,
            resource_class=ResourceClass.CPU,
            risk_level=RiskLevel.LOW,
            progress=20,
            stages=[],
        )
        session.add(tracked_task)
        session.commit()
        tracked_task_id = tracked_task.id

    response = client.get("/api/organization-os/next-move")

    assert response.status_code == 200
    assert response.json()["type"] == "task"
    assert response.json()["target"]["task_id"] == tracked_task_id
    assert response.json()["target"]["task_id"] != historical_task.id


def test_workspace_write_requires_owner_authorization(client) -> None:
    payload = {
        "theme": "neon-noir",
        "scene_preferences": {"reduced_motion": True},
        "window_state": {"owner_menu_open": False},
    }

    anonymous = client.put("/api/organization-os/workspace/default", json=payload)
    worker = client.put(
        "/api/organization-os/workspace/default",
        json=payload,
        headers=WORKER_HEADERS,
    )
    owner = client.put(
        "/api/organization-os/workspace/default",
        json=payload,
        headers=OWNER_HEADERS,
    )

    assert anonymous.status_code == 401
    assert worker.status_code == 403
    assert owner.status_code == 200
    assert owner.json()["theme"] == "neon-noir"


def test_workspace_rejects_unknown_theme(client) -> None:
    response = client.put(
        "/api/organization-os/workspace/default",
        json={"theme": "unknown-theme"},
        headers=OWNER_HEADERS,
    )

    assert response.status_code == 422
    assert "Nieobsługiwany motyw" in response.json()["detail"]
