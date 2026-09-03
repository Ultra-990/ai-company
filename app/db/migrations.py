from __future__ import annotations

from sqlalchemy import Engine, inspect, text


TASK_QUEUE_COLUMNS = {
    "resource_class": (
        "VARCHAR(32) NOT NULL DEFAULT 'LIGHT'"
    ),
    "risk_level": (
        "VARCHAR(16) NOT NULL DEFAULT 'LOW'"
    ),
    "approval_status": (
        "VARCHAR(16) NOT NULL DEFAULT 'APPROVED'"
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
        connection.execute(
            text(
                """
                UPDATE tasks
                SET approval_status = 'APPROVED'
                WHERE approval_status IS NULL
                   OR TRIM(approval_status) = ''
                """
            )
        )


APPROVAL_REQUEST_COLUMNS = {
    "tool_name": "VARCHAR(128)",
    "arguments_digest": "VARCHAR(64)",
    "executed_at": "DATETIME",
}


def migrate_approval_request_schema(engine: Engine) -> None:
    """
    Dodaje pola kontraktu wykonania narzędzi do approval_requests.

    Migracja jest idempotentna i pozostawia historyczne rekordy bez zmian.
    """
    inspector = inspect(engine)

    if "approval_requests" not in inspector.get_table_names():
        return

    existing_columns = {
        column["name"]
        for column in inspector.get_columns("approval_requests")
    }

    with engine.begin() as connection:
        for name, definition in APPROVAL_REQUEST_COLUMNS.items():
            if name not in existing_columns:
                connection.execute(
                    text(
                        "ALTER TABLE approval_requests "
                        f"ADD COLUMN {name} {definition}"
                    )
                )

        connection.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS ix_approval_requests_tool_name
                ON approval_requests (tool_name)
                """
            )
        )


def migrate_pending_tool_execution_schema(engine: Engine) -> None:
    """
    Tworzy trwały magazyn argumentów oczekujących wykonań narzędzi.

    Migracja jest idempotentna i bezpieczna dla istniejących baz SQLite.
    """
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS pending_tool_executions (
                    id INTEGER PRIMARY KEY,
                    approval_request_id INTEGER NOT NULL UNIQUE,
                    tool_name VARCHAR(128) NOT NULL,
                    arguments_json TEXT NOT NULL,
                    arguments_digest VARCHAR(64) NOT NULL,
                    created_at DATETIME NOT NULL
                )
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS
                ix_pending_tool_executions_approval_request_id
                ON pending_tool_executions (approval_request_id)
                """
            )
        )
