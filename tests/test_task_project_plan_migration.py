from sqlalchemy import create_engine, inspect, text

from app.db.migrations import (
    migrate_plan_schema,
    migrate_project_schema,
    migrate_task_project_plan_schema,
)


def test_task_project_plan_migration_is_idempotent(tmp_path) -> None:
    engine = create_engine(f"sqlite:///{tmp_path / 'tasks.sqlite3'}")

    try:
        with engine.begin() as connection:
            connection.execute(
                text(
                    """
                    CREATE TABLE tasks (
                        id INTEGER PRIMARY KEY,
                        title VARCHAR(200) NOT NULL,
                        description TEXT NOT NULL
                    )
                    """
                )
            )

        migrate_project_schema(engine)
        migrate_plan_schema(engine)
        migrate_task_project_plan_schema(engine)
        migrate_task_project_plan_schema(engine)

        columns = {
            column["name"]
            for column in inspect(engine).get_columns("tasks")
        }

        assert {"project_id", "plan_id"} <= columns
    finally:
        engine.dispose()
