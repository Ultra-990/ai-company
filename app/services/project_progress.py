from pathlib import Path
from typing import Any

import yaml


BASE_DIR = Path(__file__).resolve().parents[2]
PROGRESS_FILE = BASE_DIR / "docs" / "progress.yaml"

VALID_STATUSES = {"completed", "in_progress", "planned"}


class ProgressConfigError(ValueError):
    """Błąd niepoprawnej konfiguracji postępu projektu."""


def _validate_stage(stage: Any, index: int) -> dict[str, Any]:
    if not isinstance(stage, dict):
        raise ProgressConfigError(f"Etap nr {index} musi być obiektem.")

    required_fields = {"id", "name", "status", "progress"}
    missing = required_fields - stage.keys()
    if missing:
        missing_fields = ", ".join(sorted(missing))
        raise ProgressConfigError(
            f"Etap nr {index} nie zawiera pól: {missing_fields}."
        )

    if not isinstance(stage["id"], str) or not stage["id"].strip():
        raise ProgressConfigError(f"Etap nr {index} ma niepoprawne id.")

    if not isinstance(stage["name"], str) or not stage["name"].strip():
        raise ProgressConfigError(f"Etap nr {index} ma niepoprawną nazwę.")

    if stage["status"] not in VALID_STATUSES:
        raise ProgressConfigError(
            f"Etap {stage['id']} ma niepoprawny status: "
            f"{stage['status']!r}."
        )

    progress = stage["progress"]
    if isinstance(progress, bool) or not isinstance(progress, int):
        raise ProgressConfigError(
            f"Etap {stage['id']} musi mieć całkowity postęp."
        )

    if not 0 <= progress <= 100:
        raise ProgressConfigError(
            f"Etap {stage['id']} musi mieć postęp od 0 do 100."
        )

    items = stage.get("items", [])
    if not isinstance(items, list):
        raise ProgressConfigError(
            f"Elementy etapu {stage['id']} muszą być listą."
        )

    return stage


def load_project_progress(
    path: Path = PROGRESS_FILE,
) -> dict[str, Any]:
    """Wczytuje i waliduje konfigurację postępu projektu."""
    try:
        with path.open("r", encoding="utf-8") as file:
            data = yaml.safe_load(file)
    except FileNotFoundError as exc:
        raise ProgressConfigError(
            f"Nie znaleziono pliku postępu: {path}"
        ) from exc
    except yaml.YAMLError as exc:
        raise ProgressConfigError(
            f"Niepoprawny YAML w pliku: {path}"
        ) from exc

    if not isinstance(data, dict):
        raise ProgressConfigError("Główny dokument YAML musi być obiektem.")

    if not isinstance(data.get("project"), str):
        raise ProgressConfigError("Pole 'project' musi być tekstem.")

    stages = data.get("stages")
    if not isinstance(stages, list) or not stages:
        raise ProgressConfigError("Pole 'stages' musi być niepustą listą.")

    validated_stages = [
        _validate_stage(stage, index)
        for index, stage in enumerate(stages, start=1)
    ]

    ids = [stage["id"] for stage in validated_stages]
    if len(ids) != len(set(ids)):
        raise ProgressConfigError("Identyfikatory etapów muszą być unikalne.")

    total_progress = round(
        sum(stage["progress"] for stage in validated_stages)
        / len(validated_stages)
    )

    return {
        "project": data["project"],
        "total_progress": total_progress,
        "stages": validated_stages,
    }
