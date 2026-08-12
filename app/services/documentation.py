from datetime import datetime, timezone
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[2]
STATUS_FILE = BASE_DIR / "docs" / "STATUS.md"


def _value(task: Any, name: str, default: Any = None) -> Any:
    """Odczytuje pole z obiektu Task albo słownika."""
    if isinstance(task, dict):
        return task.get(name, default)

    return getattr(task, name, default)


def _status_value(task: Any) -> str:
    status = _value(task, "status", "unknown")
    return getattr(status, "value", str(status))


def generate_status_document(tasks: list[Any]) -> None:
    total = len(tasks)

    completed = sum(
        1
        for task in tasks
        if _status_value(task).lower() in {"completed", "done"}
    )

    active = sum(
        1
        for task in tasks
        if _status_value(task).lower()
        in {"active", "in_progress", "pending"}
    )

    progress = (
        round(
            sum(int(_value(task, "progress", 0) or 0) for task in tasks)
            / total
        )
        if total
        else 0
    )

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    lines = [
        "# Aktualny status projektu",
        "",
        f"Ostatnia aktualizacja: **{now}**",
        "",
        "## Podsumowanie",
        "",
        f"- Łączna liczba zadań: **{total}**",
        f"- Zadania ukończone: **{completed}**",
        f"- Zadania aktywne: **{active}**",
        f"- Średni postęp: **{progress}%**",
        "",
        "## Zadania",
        "",
    ]

    if not tasks:
        lines.append("Brak zarejestrowanych zadań.")
    else:
        for task in tasks:
            title = _value(task, "title", "Bez tytułu")
            status = _status_value(task)
            task_progress = _value(task, "progress", 0)

            lines.append(
                f"- **{title}** — status: `{status}`, "
                f"postęp: **{task_progress}%**"
            )

    lines.extend(
        [
            "",
            "## Informacja",
            "",
            "Ten plik jest generowany automatycznie na podstawie danych aplikacji.",
            "Nie należy edytować go ręcznie.",
            "",
        ]
    )

    STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATUS_FILE.write_text("\n".join(lines), encoding="utf-8")
