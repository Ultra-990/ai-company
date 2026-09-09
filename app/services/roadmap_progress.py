from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import (
    create_database_engine,
    create_session_factory,
)
from app.models.roadmap import RoadmapItemState


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
        self._roadmap_path = roadmap_path

    def close(self) -> None:
        self._engine.dispose()

    def get_progress(self) -> dict[str, Any]:
        roadmap = _validate_roadmap(self._roadmap_path)

        with self._session_factory() as session:
            states = {
                state.item_id: state
                for state in session.scalars(select(RoadmapItemState)).all()
            }

        phases: list[dict[str, Any]] = []
        weighted_progress = 0.0
        total_weight = 0.0

        for configured_phase in roadmap["phases"]:
            phase_items: list[dict[str, Any]] = []

            for configured_item in configured_phase["items"]:
                state = states.get(configured_item["id"])

                status = (
                    state.status.value
                    if state is not None
                    else configured_item["status"]
                )

                phase_items.append(
                    {
                        "id": configured_item["id"],
                        "name": configured_item["name"],
                        "status": status,
                        "progress": STATUS_PROGRESS[status],
                        "evidence": (
                            state.evidence
                            if state is not None
                            else configured_item.get("evidence")
                        ),
                        "note": state.note if state is not None else None,
                    }
                )

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
