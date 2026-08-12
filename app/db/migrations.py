from __future__ import annotations

from sqlalchemy import Engine, inspect, text


TASK_QUEUE_COLUMNS = {
    "resource_class": (
        "VARCHAR(32) NOT NULL DEFAULT 'LIGHT'"
    ),
    "risk_level": (
        "VARCHAR(16) NOT NULL DEFAULT 'LOW'"
    ),
    "queued_at": "DATETIME",
    "started_at": "DATETIME",
    "completed_at": "DATETIME",
}


def migrate_task_queue_schema(engine: Engine) -> None:
    """
    Uzupełnia istniejącą tabelę tasks o pola kolejki.

    Migracja jest idempotentna: można ją bezpiecznie wywoływać przy każdym
    utworzeniu TaskRepository. Nie usuwa ani nie przebudowuje tabeli.
    """
    inspector = inspect(engine)

    if "tasks" not in inspector.get_table_names():
        return

    existing_columns = {
        column["name"]
        for column in inspector.get_columns("tasks")
    }

    with engine.begin() as connection:
        for name, definition in TASK_QUEUE_COLUMNS.items():
            if name not in existing_columns:
                connection.execute(
                    text(
                        f"ALTER TABLE tasks "
                        f"ADD COLUMN {name} {definition}"
                    )
                )

        connection.execute(
            text(
                """
                UPDATE tasks
                SET resource_class = 'LIGHT'
                WHERE resource_class IS NULL
                   OR TRIM(resource_class) = ''
                """
            )
        )
        connection.execute(
            text(
                """
                UPDATE tasks
                SET risk_level = 'LOW'
                WHERE risk_level IS NULL
                   OR TRIM(risk_level) = ''
                """
            )
        )
        connection.execute(
            text(
                """
                UPDATE tasks
                SET queued_at = created_at
                WHERE queued_at IS NULL
                """
            )
        )
        connection.execute(
            text(
                """
                UPDATE tasks
                SET started_at = updated_at
                WHERE status = 'IN_PROGRESS'
                  AND started_at IS NULL
                """
            )
        )
        connection.execute(
            text(
                """
                UPDATE tasks
                SET completed_at = updated_at
                WHERE status = 'COMPLETED'
                  AND completed_at IS NULL
                """
            )
        )

        connection.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS ix_tasks_resource_class
                ON tasks (resource_class)
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS ix_tasks_risk_level
                ON tasks (risk_level)
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS ix_tasks_queued_at
                ON tasks (queued_at)
                """
            )
        )
