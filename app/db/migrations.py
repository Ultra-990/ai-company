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


TASK_ATTEMPT_VERIFICATION_COLUMNS = {
    "result_content": "TEXT",
    "result_checksum": "VARCHAR(64)",
    "verification_status": (
        "VARCHAR(20) NOT NULL DEFAULT 'pending'"
    ),
    "verification_reason": "TEXT",
    "verified_at": "DATETIME",
}


def migrate_task_attempt_schema(engine: Engine) -> None:
    """
    Tworzy i aktualizuje trwały rejestr prób wykonania zadań.

    Migracja jest idempotentna i obsługuje zarówno nowe bazy, jak i bazy
    zawierające tabelę task_attempts utworzoną przed fazą 5.
    """
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS task_attempts (
                    id INTEGER PRIMARY KEY,
                    task_id INTEGER NOT NULL,
                    worker_id VARCHAR(100) NOT NULL,
                    status VARCHAR(20) NOT NULL DEFAULT 'started',
                    started_at DATETIME NOT NULL,
                    finished_at DATETIME,
                    error_summary TEXT,
                    result_content TEXT,
                    result_checksum VARCHAR(64),
                    verification_status VARCHAR(20)
                        NOT NULL DEFAULT 'pending',
                    verification_reason TEXT,
                    verified_at DATETIME,
                    FOREIGN KEY(task_id) REFERENCES tasks(id) ON DELETE CASCADE
                )
                """
            )
        )

        # Inspektor jest tworzony po CREATE TABLE, dzięki czemu obsługujemy
        # też całkowicie nową bazę danych.
        existing_columns = {
            column["name"]
            for column in inspect(engine).get_columns("task_attempts")
        }

        for name, definition in TASK_ATTEMPT_VERIFICATION_COLUMNS.items():
            if name not in existing_columns:
                connection.execute(
                    text(
                        "ALTER TABLE task_attempts "
                        f"ADD COLUMN {name} {definition}"
                    )
                )

        # Historyczne rekordy sprzed fazy 5 nie miały tego pola.
        connection.execute(
            text(
                """
                UPDATE task_attempts
                SET verification_status = 'pending'
                WHERE verification_status IS NULL
                   OR TRIM(verification_status) = ''
                """
            )
        )

        connection.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS ix_task_attempts_task_id
                ON task_attempts (task_id)
                """
            )
        )

        connection.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS ix_task_attempts_worker_id
                ON task_attempts (worker_id)
                """
            )
        )

        connection.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS ix_task_attempts_status
                ON task_attempts (status)
                """
            )
        )

        connection.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS ix_task_attempts_result_checksum
                ON task_attempts (result_checksum)
                """
            )
        )

        connection.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS ix_task_attempts_verification_status
                ON task_attempts (verification_status)
                """
            )
        )

        connection.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS ix_task_attempts_verified_at
                ON task_attempts (verified_at)
                """
            )
        )

        connection.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS ix_task_attempts_started_at
                ON task_attempts (started_at)
                """
            )
        )

        connection.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS ix_task_attempts_finished_at
                ON task_attempts (finished_at)
                """
            )
        )


def migrate_project_schema(engine: Engine) -> None:
    """
    Tworzy tabelę nadrzędnych agregatów Project.

    Migracja jest idempotentna. Tabela jest tworzona również przez
    Base.metadata.create_all(), lecz jawna migracja zapewnia poprawne
    działanie dla istniejących środowisk i samodzielnych wywołań migracji.
    """
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS projects (
                    id INTEGER PRIMARY KEY,
                    name VARCHAR(200) NOT NULL,
                    business_goal TEXT NOT NULL,
                    description TEXT,
                    status VARCHAR(20) NOT NULL DEFAULT 'DRAFT',
                    organization_unit_id INTEGER,
                    created_at DATETIME NOT NULL,
                    updated_at DATETIME NOT NULL,
                    started_at DATETIME,
                    completed_at DATETIME,
                    FOREIGN KEY(organization_unit_id)
                        REFERENCES organization_units(id)
                )
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS ix_projects_name
                ON projects (name)
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS ix_projects_status
                ON projects (status)
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS ix_projects_organization_unit_id
                ON projects (organization_unit_id)
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS ix_projects_created_at
                ON projects (created_at)
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS ix_projects_started_at
                ON projects (started_at)
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS ix_projects_completed_at
                ON projects (completed_at)
                """
            )
        )


def migrate_plan_schema(engine: Engine) -> None:
    """
    Tworzy tabelę planów wykonawczych.

    Migracja jest idempotentna i może być uruchamiana wielokrotnie.
    """
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS plans (
                    id INTEGER PRIMARY KEY,
                    project_id INTEGER NOT NULL,
                    name VARCHAR(200) NOT NULL,
                    objective TEXT NOT NULL,
                    description TEXT,
                    status VARCHAR(20) NOT NULL DEFAULT 'DRAFT',
                    created_at DATETIME NOT NULL,
                    updated_at DATETIME NOT NULL,
                    started_at DATETIME,
                    completed_at DATETIME,
                    FOREIGN KEY(project_id) REFERENCES projects(id)
                )
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS ix_plans_project_id
                ON plans (project_id)
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS ix_plans_name
                ON plans (name)
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS ix_plans_status
                ON plans (status)
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS ix_plans_created_at
                ON plans (created_at)
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS ix_plans_started_at
                ON plans (started_at)
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS ix_plans_completed_at
                ON plans (completed_at)
                """
            )
        )


def migrate_task_project_plan_schema(engine: Engine) -> None:
    """
    Uzupełnia istniejącą tabelę tasks o opcjonalne powiązania domenowe.

    Kolumny pozostają nullable, aby dotychczasowe zadania techniczne mogły
    działać bez przypisania do projektu lub planu. Migracja obsługuje SQLite
    oraz PostgreSQL i może być wykonywana wielokrotnie.
    """
    with engine.begin() as connection:
        dialect = connection.dialect.name

        if dialect == "sqlite":
            columns = {
                row[1]
                for row in connection.execute(
                    text("PRAGMA table_info(tasks)")
                )
            }

            if "project_id" not in columns:
                connection.execute(
                    text(
                        """
                        ALTER TABLE tasks
                        ADD COLUMN project_id INTEGER
                        REFERENCES projects(id)
                        """
                    )
                )

            if "plan_id" not in columns:
                connection.execute(
                    text(
                        """
                        ALTER TABLE tasks
                        ADD COLUMN plan_id INTEGER
                        REFERENCES plans(id)
                        """
                    )
                )
        else:
            connection.execute(
                text(
                    """
                    ALTER TABLE tasks
                    ADD COLUMN IF NOT EXISTS project_id INTEGER
                    REFERENCES projects(id)
                    """
                )
            )
            connection.execute(
                text(
                    """
                    ALTER TABLE tasks
                    ADD COLUMN IF NOT EXISTS plan_id INTEGER
                    REFERENCES plans(id)
                    """
                )
            )

        connection.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS ix_tasks_project_id
                ON tasks (project_id)
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS ix_tasks_plan_id
                ON tasks (plan_id)
                """
            )
        )
