from __future__ import annotations

import subprocess
from datetime import datetime, timezone
from pathlib import Path

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROGRESS_FILE = PROJECT_ROOT / "docs" / "progress.yaml"
CONTINUITY_FILE = PROJECT_ROOT / "docs" / "CONTINUITY.md"


def _git(*args: str) -> str:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip() or "brak danych"
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "brak danych"


def _progress() -> dict:
    if not PROGRESS_FILE.exists():
        return {}

    with PROGRESS_FILE.open(encoding="utf-8") as file:
        return yaml.safe_load(file) or {}


def _task_name(task: dict) -> str:
    return str(task.get("title") or task.get("name") or "bez nazwy")


def _task_lines(tasks: list[dict]) -> str:
    if not tasks:
        return "- brak"

    return "\n".join(f"- {_task_name(task)}" for task in tasks)


def generate_continuity() -> str:
    data = _progress()
    project = data.get("project_progress", {})
    tasks = data.get("tasks", [])

    completed = [
        task for task in tasks
        if task.get("status") in {"completed", "done"}
    ]
    active = [
        task for task in tasks
        if task.get("status") in {"in_progress", "active"}
    ]
    pending = [
        task for task in tasks
        if task.get("status") in {"planned", "pending", "todo"}
    ]

    modified_files = _git("status", "--short")
    last_commit = _git("log", "-1", "--oneline")
    total_progress = project.get("total_progress", 0)

    return f"""# AI Company — Continuity Context

> Dokument wygenerowany automatycznie.
> Ostatnia aktualizacja: {datetime.now(timezone.utc).isoformat()}

## Aktualny stan

- Ostatni commit: `{last_commit}`
- Postęp projektu: **{total_progress}%**

## Ukończone zadania

{_task_lines(completed)}

## Zadania w trakcie realizacji

{_task_lines(active)}

## Zadania oczekujące

{_task_lines(pending)}

## Zmodyfikowane pliki

```text
{modified_files or "brak lokalnych zmian"}

```
## Instrukcja dla kolejnej rozmowy

Najpierw zapoznaj się z tym dokumentem i sprawdź aktualny stan repozytorium.
Nie zakładaj wykonania zadań, których status nie jest potwierdzony w kodzie.
"""


def update_continuity() -> Path:
    CONTINUITY_FILE.write_text(
        generate_continuity(),
        encoding="utf-8",
    )
    return CONTINUITY_FILE
