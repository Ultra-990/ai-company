from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from sqlalchemy import Engine, inspect, select
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import (
    create_database_engine,
    create_session_factory,
)
from app.models.roadmap import RoadmapItemState, RoadmapItemStatus
from app.services.tasks import TaskRepository


BASE_DIR = Path(__file__).resolve().parents[2]
ROADMAP_FILE = BASE_DIR / "docs" / "roadmap.yaml"

ROADMAP_STATUSES = {
    "planned",
    "ready",
    "in_progress",
    "blocked",
    "completed",
    "cancelled",
}

STATUS_PROGRESS = {
    "planned": 0,
    "ready": 0,
    "in_progress": 50,
    "blocked": 0,
    "completed": 100,
    "cancelled": 0,
}


class RoadmapConfigError(ValueError):
    """Błąd niepoprawnej definicji roadmapy."""


def _require_non_empty_string(
    value: Any,
    *,
    field_name: str,
) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RoadmapConfigError(
            f"Pole '{field_name}' musi być niepustym tekstem."
        )

    return value


def _validate_roadmap(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as file:
            data = yaml.safe_load(file)
    except FileNotFoundError as exc:
        raise RoadmapConfigError(
            f"Nie znaleziono pliku roadmapy: {path}"
        ) from exc
    except yaml.YAMLError as exc:
        raise RoadmapConfigError(
            f"Niepoprawny YAML w pliku roadmapy: {path}"
        ) from exc

    if not isinstance(data, dict):
        raise RoadmapConfigError(
            "Główny dokument roadmapy musi być obiektem."
        )

    project = data.get("project")
    if not isinstance(project, dict):
        raise RoadmapConfigError(
            "Pole 'project' roadmapy musi być obiektem."
        )

    _require_non_empty_string(
        project.get("id"),
        field_name="project.id",
    )
    _require_non_empty_string(
        project.get("name"),
        field_name="project.name",
    )

    phases = data.get("phases")
    if not isinstance(phases, list) or not phases:
        raise RoadmapConfigError(
            "Pole 'phases' musi być niepustą listą."
        )

    phase_ids: set[str] = set()
    item_ids: set[str] = set()

    for phase_index, phase in enumerate(phases, start=1):
        if not isinstance(phase, dict):
            raise RoadmapConfigError(
                f"Faza nr {phase_index} musi być obiektem."
            )

        phase_id = _require_non_empty_string(
            phase.get("id"),
            field_name=f"phases[{phase_index}].id",
        )

        if phase_id in phase_ids:
            raise RoadmapConfigError(
                f"Identyfikator fazy musi być unikalny: {phase_id}."
            )
        phase_ids.add(phase_id)

        _require_non_empty_string(
            phase.get("name"),
            field_name=f"phases[{phase_index}].name",
        )

        weight = phase.get("weight")
        if (
            isinstance(weight, bool)
            or not isinstance(weight, (int, float))
            or weight <= 0
        ):
            raise RoadmapConfigError(
                f"Faza {phase_id} musi mieć dodatnią wagę liczbową."
            )

        items = phase.get("items")
        if not isinstance(items, list) or not items:
            raise RoadmapConfigError(
                f"Faza {phase_id} musi zawierać niepustą listę items."
            )

        for item_index, item in enumerate(items, start=1):
            if not isinstance(item, dict):
                raise RoadmapConfigError(
                    f"Punkt {phase_id}[{item_index}] musi być obiektem."
                )

            item_id = _require_non_empty_string(
                item.get("id"),
                field_name=f"{phase_id}.items[{item_index}].id",
            )

            if item_id in item_ids:
                raise RoadmapConfigError(
                    f"Identyfikator punktu musi być unikalny: {item_id}."
                )
            item_ids.add(item_id)

            _require_non_empty_string(
                item.get("name"),
                field_name=f"{item_id}.name",
            )

            status = item.get("status")
            if status not in ROADMAP_STATUSES:
                raise RoadmapConfigError(
                    f"Punkt {item_id} ma niepoprawny status: {status!r}."
                )

    return data


def _phase_status(items: list[dict[str, Any]]) -> str:
    statuses = {item["status"] for item in items}

    if statuses == {"completed"}:
        return "completed"

    if "blocked" in statuses:
        return "blocked"

    if "in_progress" in statuses:
        return "in_progress"

    if "ready" in statuses:
        return "ready"

    if statuses == {"cancelled"}:
        return "cancelled"

    return "planned"


class ProjectProgressService:
    """
    Łączy statyczną definicję roadmapy z trwałym stanem SQLite.

    YAML określa fazy, wagi i domyślne statusy. Rekord o tym samym item_id
    w roadmap_item_states nadpisuje wyłącznie status, evidence i note.
    """

    def __init__(
        self,
        database_url: str,
        *,
        roadmap_path: Path = ROADMAP_FILE,
    ) -> None:
        self._engine: Engine = create_database_engine(database_url)
        self._session_factory: sessionmaker[Session] = (
            create_session_factory(self._engine)
        )
        self._database_url = database_url
        self._roadmap_path = roadmap_path

    def close(self) -> None:
        self._engine.dispose()

    def _get_task_stats_by_roadmap_item(
        self,
    ) -> dict[str, list[dict[str, object]]]:
        """
        Pobiera statystyki zadań i grupuje je po roadmap_item_id.

        Sprawdzenie obecności tabeli zachowuje zgodność ze starszymi bazami
        danych, które zawierają jedynie roadmap_item_states.
        """
        if not inspect(self._engine).has_table("tasks"):
            return {}

        repository = TaskRepository(
            self._database_url,
            initialize=False,
        )

        try:
            grouped: dict[str, list[dict[str, object]]] = {}

            for stat in repository.get_roadmap_item_stats():
                item_id = stat["roadmap_item_id"]

                if isinstance(item_id, str):
                    grouped.setdefault(item_id, []).append(stat)

            return grouped
        finally:
            repository.close()

    def _calculate_auto_status(
        self,
        stats: list[dict[str, object]],
    ) -> dict[str, object]:
        """
        Wylicza stan punktu roadmapy na podstawie przypisanych zadań.

        Priorytet statusów:
        blocked > completed wszystkie > in_progress > ready > cancelled.
        """
        counts = {status: 0 for status in ROADMAP_STATUSES}
        total_tasks = 0
        weighted_progress = 0.0

        for stat in stats:
            status = stat["status"]
            count = stat["count"]
            average_progress = stat["average_progress"]

            if (
                not isinstance(status, str)
                or not isinstance(count, int)
                or not isinstance(average_progress, (int, float))
            ):
                continue

            counts[status] = counts.get(status, 0) + count
            total_tasks += count
            weighted_progress += float(average_progress) * count

        if total_tasks == 0:
            raise ValueError(
                "Nie można wyliczyć stanu bez przypisanych zadań."
            )

        completed_tasks = counts["completed"]
        average_progress = round(weighted_progress / total_tasks)

        if counts["blocked"] > 0:
            status = "blocked"
        elif completed_tasks == total_tasks:
            status = "completed"
        elif counts["in_progress"] > 0:
            status = "in_progress"
        elif counts["pending"] > 0:
            status = "ready"
        elif counts["cancelled"] == total_tasks:
            status = "cancelled"
        else:
            status = "ready"

        task_summary = {
            task_status: count
            for task_status, count in counts.items()
            if count > 0
        }

        return {
            "status": status,
            "progress": average_progress,
            "status_source": "tasks",
            "task_summary": {
                "total": total_tasks,
                "completed": completed_tasks,
                "by_status": task_summary,
            },
            "evidence": (
                "Automatycznie na podstawie zadań: "
                f"{completed_tasks}/{total_tasks} ukończonych, "
                f"średni postęp {average_progress}%."
            ),
        }

    def has_item(self, item_id: str) -> bool:
        """Sprawdza, czy identyfikator istnieje w aktualnej roadmapie YAML."""
        roadmap = _validate_roadmap(self._roadmap_path)

        return any(
            configured_item["id"] == item_id
            for configured_phase in roadmap["phases"]
            for configured_item in configured_phase["items"]
        )

    def update_item_state(
        self,
        item_id: str,
        changes: dict[str, Any],
    ) -> dict[str, Any]:
        """Tworzy albo częściowo aktualizuje trwały override punktu roadmapy."""
        with self._session_factory() as session:
            state = session.get(RoadmapItemState, item_id)

            if state is None:
                state = RoadmapItemState(item_id=item_id)
                session.add(state)

            for field, value in changes.items():
                setattr(state, field, value)

            session.commit()
            session.refresh(state)

            return {
                "item_id": state.item_id,
                "status": state.status.value,
                "evidence": state.evidence,
                "note": state.note,
            }

    def get_progress(self) -> dict[str, Any]:
        roadmap = _validate_roadmap(self._roadmap_path)

        with self._session_factory() as session:
            states = {
                state.item_id: state
                for state in session.scalars(select(RoadmapItemState)).all()
            }

        task_stats_by_item = self._get_task_stats_by_roadmap_item()

        phases: list[dict[str, Any]] = []
        weighted_progress = 0.0
        total_weight = 0.0

        for configured_phase in roadmap["phases"]:
            phase_items: list[dict[str, Any]] = []

            for configured_item in configured_phase["items"]:
                item_id = configured_item["id"]
                state = states.get(item_id)
                task_stats = task_stats_by_item.get(item_id, [])

                if state is not None:
                    item_data: dict[str, Any] = {
                        "id": item_id,
                        "name": configured_item["name"],
                        "status": state.status.value,
                        "progress": STATUS_PROGRESS[state.status.value],
                        "status_source": "manual",
                        "task_summary": None,
                        "evidence": state.evidence,
                        "note": state.note,
                    }
                elif task_stats:
                    auto_state = self._calculate_auto_status(task_stats)
                    item_data = {
                        "id": item_id,
                        "name": configured_item["name"],
                        "status": auto_state["status"],
                        "progress": auto_state["progress"],
                        "status_source": auto_state["status_source"],
                        "task_summary": auto_state["task_summary"],
                        "evidence": auto_state["evidence"],
                        "note": None,
                    }
                else:
                    status = configured_item["status"]
                    item_data = {
                        "id": item_id,
                        "name": configured_item["name"],
                        "status": status,
                        "progress": STATUS_PROGRESS[status],
                        "status_source": "roadmap",
                        "task_summary": None,
                        "evidence": configured_item.get("evidence"),
                        "note": None,
                    }

                phase_items.append(item_data)

            phase_progress = round(
                sum(item["progress"] for item in phase_items)
                / len(phase_items)
            )
            phase_weight = float(configured_phase["weight"])

            weighted_progress += phase_progress * phase_weight
            total_weight += phase_weight

            phases.append(
                {
                    "id": configured_phase["id"],
                    "name": configured_phase["name"],
                    "weight": configured_phase["weight"],
                    "status": _phase_status(phase_items),
                    "progress": phase_progress,
                    "depends_on": configured_phase.get("depends_on", []),
                    "items": phase_items,
                }
            )

        return {
            "project": {
                "id": roadmap["project"]["id"],
                "name": roadmap["project"]["name"],
                "progress_method": roadmap["project"].get(
                    "progress_method"
                ),
                "source_of_truth": roadmap["project"].get(
                    "source_of_truth"
                ),
            },
            "total_progress": round(weighted_progress / total_weight),
            "phases": phases,
        }
