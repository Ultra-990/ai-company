from pathlib import Path

from sqlalchemy import create_engine, inspect, text

from app.db.migrations import migrate_task_queue_schema


def test_migration_adds_queue_columns_and_preserves_existing_tasks(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "legacy_tasks.sqlite3"
    engine = create_engine(f"sqlite:///{database_path}")

    try:
        with engine.begin() as connection:
            # Schemat sprzed wprowadzenia kolejki i limitów zasobów.
            connection.execute(
                text(
                    """
                    CREATE TABLE tasks (
                        id INTEGER PRIMARY KEY,
                        title VARCHAR NOT NULL,
                        description TEXT,
                        status VARCHAR NOT NULL,
                        priority VARCHAR NOT NULL,
                        assigned_agent VARCHAR,
                        created_at DATETIME NOT NULL,
                        updated_at DATETIME NOT NULL,
                        progress INTEGER NOT NULL DEFAULT 0,
                        stages JSON NOT NULL DEFAULT '[]'
                    )
                    """
                )
            )

            connection.execute(
                text(
                    """
                    INSERT INTO tasks (
                        title,
                        status,
                        priority,
                        progress,
                        stages,
                        created_at,
                        updated_at
                    )
                    VALUES (
                        'Zadanie ze starego schematu',
                        'PENDING',
                        'NORMAL',
                        0,
                        '[]',
                        '2026-08-12 10:00:00',
                        '2026-08-12 10:00:00'
                    )
                    """
                )
            )

        # Drugie wywołanie potwierdza idempotentność migracji.
        migrate_task_queue_schema(engine)
        migrate_task_queue_schema(engine)

        columns = {
            column["name"]
            for column in inspect(engine).get_columns("tasks")
        }

        assert {
            "resource_class",
            "risk_level",
            "queued_at",
            "started_at",
            "completed_at",
        }.issubset(columns)

        with engine.connect() as connection:
            row = connection.execute(
                text(
                    """
                    SELECT
                        title,
                        resource_class,
                        risk_level,
                        queued_at,
                        started_at,
                        completed_at
                    FROM tasks
                    """
                )
            ).mappings().one()

        assert row["title"] == "Zadanie ze starego schematu"
        assert row["resource_class"] == "LIGHT"
        assert row["risk_level"] == "LOW"
        assert row["queued_at"] is not None
        assert row["started_at"] is None
        assert row["completed_at"] is None
    finally:
        engine.dispose()
