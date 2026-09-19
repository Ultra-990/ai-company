from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from collections.abc import Generator
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.auth import require_owner
from app.core.config import load_settings
from app.core.database import create_database_engine, create_session_factory
from app.models.organization import OrganizationUnit
from app.models.organization_os import (
    Alert,
    OrganizationUnitDependency,
    WorkspacePreference,
)
from app.models.project import Project
from app.models.task import Task, TaskAttempt, TaskStatus


router = APIRouter(
    prefix="/api/organization-os",
    tags=["organization-os"],
)

settings = load_settings()
engine = create_database_engine(settings.database.url)
SessionLocal = create_session_factory(engine)


def get_organization_session() -> Generator[Session, None, None]:
    """Udostępnia sesję Organization OS i umożliwia jej izolację w testach."""
    with SessionLocal() as session:
        yield session


OrganizationSession = Annotated[
    Session,
    Depends(get_organization_session),
]

ALLOWED_WORKSPACE_THEMES = {
    "arctic-light",
    "solar-light",
    "deep-space",
    "neon-noir",
}


class WorkspacePreferenceUpdate(BaseModel):
    theme: str = Field(
        default="arctic-light",
        min_length=1,
        max_length=32,
    )
    scene_preferences: dict[str, Any] = Field(default_factory=dict)
    window_state: dict[str, Any] = Field(default_factory=dict)


def serialize_datetime(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def serialize_status(value: object) -> str:
    raw_value = getattr(value, "value", value)
    return str(raw_value).lower()


def task_progress(task: Task) -> int:
    """Zwraca postęp zadania, uwzględniając jego końcowy status."""
    status = serialize_status(task.status)

    if status == TaskStatus.COMPLETED.value:
        return 100

    if status == TaskStatus.CANCELLED.value:
        return 0

    return max(0, min(int(task.progress or 0), 100))


def project_progress(tasks: list[Task]) -> int:
    """Oblicza średni postęp zadań przypisanych do projektu."""
    if not tasks:
        return 0

    return round(sum(task_progress(task) for task in tasks) / len(tasks))


def severity_rank(severity: str) -> int:
    ranks = {
        "critical": 4,
        "blocker": 3,
        "warning": 2,
        "info": 1,
    }
    return ranks.get(severity.lower(), 0)


def serialize_alert(alert: Alert) -> dict[str, Any]:
    return {
        "id": alert.id,
        "organization_unit_id": alert.organization_unit_id,
        "project_id": alert.project_id,
        "task_id": alert.task_id,
        "agent_id": alert.agent_id,
        "severity": serialize_status(alert.severity),
        "status": serialize_status(alert.status),
        "title": alert.title,
        "message": alert.message,
        "source": alert.source,
        "resolution_note": alert.resolution_note,
        "created_at": serialize_datetime(alert.created_at),
        "acknowledged_at": serialize_datetime(alert.acknowledged_at),
        "resolved_at": serialize_datetime(alert.resolved_at),
    }


def build_tree(session: Session) -> tuple[list[dict[str, Any]], dict[str, int]]:
    from app.organization_os.department_foundations import foundation_for
    from app.organization_os.department_operations import operating_model
    units = list(
        session.scalars(
            select(OrganizationUnit).order_by(
                OrganizationUnit.sort_order,
                OrganizationUnit.id,
            )
        )
    )

    projects = list(session.scalars(select(Project)))
    tasks = list(session.scalars(select(Task)))
    pending_review_ids = set(session.scalars(select(TaskAttempt.task_id).where(
        TaskAttempt.status == "awaiting_review",
    )))

    tracked_tasks = [task for task in tasks if task.project_id is not None]

    tasks_by_project: dict[int, list[Task]] = defaultdict(list)
    for task in tracked_tasks:
        if task.project_id is not None:
            tasks_by_project[task.project_id].append(task)

    projects_by_unit: dict[int, list[Project]] = defaultdict(list)
    for project in projects:
        if project.organization_unit_id is not None:
            projects_by_unit[project.organization_unit_id].append(project)

    children_by_parent: dict[int | None, list[OrganizationUnit]] = defaultdict(list)
    for unit in units:
        children_by_parent[unit.parent_id].append(unit)

    totals = {
        "projects": len(projects),
        # "tasks" zachowujemy dla kompatybilności z pierwszym prototypem.
        # Metryki tracked_* są miarą faktycznego postępu Organization OS.
        "tasks": len(tasks),
        "awaiting_review_tasks": sum(task.id in pending_review_ids for task in tasks),
        "tracked_tasks": len(tracked_tasks),
        "unassigned_tasks": len(tasks) - len(tracked_tasks),
        "completed_tasks": sum(
            1
            for task in tasks
            if serialize_status(task.status) == TaskStatus.COMPLETED.value
        ),
        "blocked_tasks": sum(
            1
            for task in tasks
            if serialize_status(task.status) == TaskStatus.BLOCKED.value
        ),
        "tracked_completed_tasks": sum(
            1
            for task in tracked_tasks
            if serialize_status(task.status) == TaskStatus.COMPLETED.value
        ),
        "tracked_blocked_tasks": sum(
            1
            for task in tracked_tasks
            if serialize_status(task.status) == TaskStatus.BLOCKED.value
        ),
    }

    def build_node(unit: OrganizationUnit) -> dict[str, Any]:
        child_nodes = [
            build_node(child)
            for child in children_by_parent.get(unit.id, [])
        ]

        unit_projects = projects_by_unit.get(unit.id, [])
        unit_task_list = [
            task
            for project in unit_projects
            for task in tasks_by_project.get(project.id, [])
        ]

        direct_progress = project_progress(unit_task_list)

        weighted_children = [
            (
                max(int(child["weight"]), 1),
                int(child["progress"]),
            )
            for child in child_nodes
        ]

        if weighted_children:
            total_weight = sum(weight for weight, _ in weighted_children)
            progress = round(
                sum(weight * value for weight, value in weighted_children)
                / total_weight
            )
        else:
            progress = direct_progress

        subtree_tasks = len(unit_task_list) + sum(c['subtree_task_count'] for c in child_nodes)
        unmeasured = sum(c['measurement_state'] != 'tracked' for c in child_nodes)
        measurement = ('unmeasured' if not subtree_tasks else
                       'partial' if unmeasured or (child_nodes and unit_task_list) else 'tracked')
        progress_note = ('Brak zadań przypisanych do tej gałęzi. 0% oznacza brak pomiaru, nie audyt braku wykonanej pracy.'
                         if not subtree_tasks else
                         'Postęp liczony z zadań w projektach i wag dzieci. Nie obejmuje prac bez przypisania ani samych plików w repozytorium.')
        if child_nodes and unit_task_list:
            progress_note += ' Zadania bezpośrednio na rodzicu nie wchodzą do średniej dzieci; trzeba przydzielić im mierzalny zakres w gałęzi.'

        return {
            "id": unit.id,
            "key": unit.os_key,
            "name": unit.name,
            "kind": unit.unit_type,
            "description": unit.description,
            "status": serialize_status(unit.status),
            "active": unit.active,
            "weight": unit.weight,
            "sort_order": unit.sort_order,
            "icon": unit.icon,
            "color": unit.color,
            "manager_agent": unit.manager_agent,
            "owner_agent_id": unit.owner_agent_id,
            "brain_agent_id": unit.brain_agent_id,
            "progress": progress,
            "measurement_state": measurement,
            "progress_note": progress_note,
            "progress_mode": 'weighted_children' if child_nodes else 'project_tasks',
            "unmeasured_children": unmeasured,
            "direct_tasks_outside_aggregation": len(unit_task_list) if child_nodes else 0,
            "subtree_task_count": subtree_tasks,
            "subtree_project_count": len(unit_projects) + sum(c['subtree_project_count'] for c in child_nodes),
            "subtree_blocked_task_count": sum(serialize_status(t.status) == TaskStatus.BLOCKED.value for t in unit_task_list)
                + sum(c['subtree_blocked_task_count'] for c in child_nodes),
            "foundation": foundation_for(unit.os_key),
            "operating_model": operating_model(unit.os_key),
            "project_count": len(unit_projects),
            "task_count": len(unit_task_list),
            "awaiting_review_count": sum(task.id in pending_review_ids for task in unit_task_list)
                + sum(child["awaiting_review_count"] for child in child_nodes),
            "blocked_task_count": sum(
                1
                for task in unit_task_list
                if serialize_status(task.status) == TaskStatus.BLOCKED.value
            ),
            "children": child_nodes,
        }

    root_nodes = [
        build_node(unit)
        for unit in children_by_parent.get(None, [])
    ]

    return root_nodes, totals


@router.get("/overview")
def get_overview(session: OrganizationSession) -> dict[str, Any]:
    tree, totals = build_tree(session)

    active_alerts = list(
        session.scalars(
            select(Alert).where(
                Alert.status.in_(["open", "acknowledged"])
            )
        )
    )

    critical_alert_count = sum(
        1
        for alert in active_alerts
        if serialize_status(alert.severity) == "critical"
    )
    blocker_alert_count = sum(
        1
        for alert in active_alerts
        if serialize_status(alert.severity) == "blocker"
    )

    organization_progress = (
        tree[0]["progress"]
        if len(tree) == 1 and tree[0]["key"] == "ai-company"
        else 0
    )

    return {
        "organization_progress": organization_progress,
        "organization_count": len(tree),
        "department_count": max(
            sum(
                len(root["children"])
                for root in tree
            ),
            0,
        ),
        "active_alert_count": len(active_alerts),
        "critical_alert_count": critical_alert_count,
        "blocker_alert_count": blocker_alert_count,
        **totals,
    }


@router.get("/tree")
def get_organization_tree(session: OrganizationSession) -> dict[str, Any]:
    tree, totals = build_tree(session)
    units = list(session.scalars(select(OrganizationUnit)))
    unit_keys = {unit.id: unit.os_key for unit in units}
    dependencies = list(
        session.scalars(
            select(OrganizationUnitDependency).where(
                OrganizationUnitDependency.active.is_(True)
            )
        )
    )

    return {
        "nodes": tree,
        "summary": totals,
        "dependencies": [
            {
                "source_key": unit_keys.get(dependency.source_unit_id),
                "target_key": unit_keys.get(dependency.target_unit_id),
                "relation_type": dependency.relation_type,
                "description": dependency.description,
            }
            for dependency in dependencies
            if unit_keys.get(dependency.source_unit_id)
            and unit_keys.get(dependency.target_unit_id)
        ],
    }


@router.get("/alerts")
def get_alerts(
    session: OrganizationSession,
    status: str = "open",
    limit: int = 100,
) -> dict[str, Any]:
    safe_limit = max(1, min(limit, 500))

    statement = (
        select(Alert)
        .where(Alert.status == status.lower())
        .order_by(Alert.created_at.desc())
        .limit(safe_limit)
    )
    alerts = list(session.scalars(statement))

    alerts.sort(
        key=lambda alert: (
            severity_rank(serialize_status(alert.severity)),
            alert.created_at,
        ),
        reverse=True,
    )

    return {
        "count": len(alerts),
        "alerts": [serialize_alert(alert) for alert in alerts],
    }


@router.get("/next-move")
def get_next_move(session: OrganizationSession) -> dict[str, Any]:
    """
    Zwraca najważniejszy kolejny ruch dla Brain Core.

    Priorytet:
    1. otwarty CRITICAL/BLOCKER alert,
    2. zablokowane zadanie,
    3. wynik oczekujący na odbiór właściciela,
    4. aktywne zadanie o najniższym postępie,
    5. stan oczekiwania.
    """
    active_alerts = list(
        session.scalars(
            select(Alert).where(
                Alert.status.in_(["open", "acknowledged"])
            )
        )
    )

    urgent_alerts = [
        alert
        for alert in active_alerts
        if serialize_status(alert.severity) in {"critical", "blocker"}
    ]

    if urgent_alerts:
        alert = max(
            urgent_alerts,
            key=lambda item: (
                severity_rank(serialize_status(item.severity)),
                item.created_at,
            ),
        )
        return {
            "type": "alert",
            "priority": serialize_status(alert.severity),
            "title": alert.title,
            "reason": alert.message,
            "target": {
                "alert_id": alert.id,
                "organization_unit_id": alert.organization_unit_id,
                "project_id": alert.project_id,
                "task_id": alert.task_id,
            },
        }

    # Zadania bez projektu są historyczne albo oczekują na klasyfikację.
    # Nie mogą manipulować operacyjną rekomendacją firmy.
    blocked_task = session.scalar(
        select(Task)
        .where(
            Task.project_id.is_not(None),
            Task.status == TaskStatus.BLOCKED,
        )
        .order_by(Task.updated_at.asc())
    )

    if blocked_task is not None:
        return {
            "type": "task",
            "priority": "blocker",
            "title": f"Odblokuj zadanie: {blocked_task.title}",
            "reason": (
                blocked_task.description
                or "Zadanie ma status blocked i wymaga decyzji."
            ),
            "target": {
                "task_id": blocked_task.id,
                "project_id": blocked_task.project_id,
            },
        }

    review = session.execute(
        select(Task, TaskAttempt).join(TaskAttempt, TaskAttempt.task_id == Task.id)
        .where(Task.project_id.is_not(None), Task.status == TaskStatus.IN_PROGRESS,
               TaskAttempt.status == "awaiting_review")
        .order_by(TaskAttempt.finished_at.asc(), TaskAttempt.id.asc()).limit(1)
    ).first()
    if review is not None:
        task, attempt = review
        return {
            "type": "review", "priority": "high",
            "title": f"Odbierz wynik: {task.title}",
            "reason": "Wykonawca przesłał rezultat. Potrzebna jest kontrola i decyzja właściciela.",
            "target": {"task_id": task.id, "project_id": task.project_id,
                       "attempt_id": attempt.id},
        }

    active_tasks = list(
        session.scalars(
            select(Task)
            .where(
                Task.project_id.is_not(None),
                Task.status == TaskStatus.IN_PROGRESS,
            )
            .order_by(Task.progress.asc(), Task.updated_at.asc())
        )
    )

    if active_tasks:
        task = active_tasks[0]
        return {
            "type": "task",
            "priority": "normal",
            "title": f"Przyspiesz zadanie: {task.title}",
            "reason": (
                task.description
                or "To aktywne zadanie ma najniższy postęp."
            ),
            "target": {
                "task_id": task.id,
                "project_id": task.project_id,
            },
        }

    return {
        "type": "system",
        "priority": "info",
        "title": "Brak pilnego kolejnego ruchu",
        "reason": (
            "Nie ma otwartych krytycznych alertów, zablokowanych zadań "
            "ani aktywnych zadań w toku w projektach Organization OS."
        ),
        "target": {},
    }


@router.get("/workspace/{workspace_key}")
def get_workspace_preference(
    workspace_key: str,
    session: OrganizationSession,
) -> dict[str, Any]:
    preference = session.scalar(
        select(WorkspacePreference).where(
            WorkspacePreference.workspace_key == workspace_key
        )
    )

    if preference is None:
        raise HTTPException(
            status_code=404,
            detail="Nie znaleziono preferencji workspace.",
        )

    return {
        "workspace_key": preference.workspace_key,
        "theme": preference.theme,
        "scene_preferences": preference.scene_preferences,
        "window_state": preference.window_state,
        "updated_at": serialize_datetime(preference.updated_at),
    }


@router.put("/workspace/{workspace_key}")
def update_workspace_preference(
    workspace_key: str,
    payload: WorkspacePreferenceUpdate,
    session: OrganizationSession,
    _: None = Depends(require_owner),
) -> dict[str, Any]:
    if payload.theme not in ALLOWED_WORKSPACE_THEMES:
        raise HTTPException(
            status_code=422,
            detail=(
                "Nieobsługiwany motyw workspace. Dozwolone wartości: "
                f"{', '.join(sorted(ALLOWED_WORKSPACE_THEMES))}."
            ),
        )

    preference = session.scalar(
        select(WorkspacePreference).where(
            WorkspacePreference.workspace_key == workspace_key
        )
    )

    if preference is None:
        preference = WorkspacePreference(
            workspace_key=workspace_key,
        )
        session.add(preference)

    preference.theme = payload.theme
    preference.scene_preferences = payload.scene_preferences
    preference.window_state = payload.window_state

    session.commit()
    session.refresh(preference)

    return {
        "workspace_key": preference.workspace_key,
        "theme": preference.theme,
        "scene_preferences": preference.scene_preferences,
        "window_state": preference.window_state,
        "updated_at": serialize_datetime(preference.updated_at),
    }
