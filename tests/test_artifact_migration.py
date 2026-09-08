from sqlalchemy import create_engine, inspect

from app.db.migrations import (
    migrate_artifact_schema,
    migrate_plan_schema,
    migrate_project_schema,
    migrate_task_attempt_schema,
)


def test_migrate_artifact_schema_is_idempotent() -> None:
    engine = create_engine("sqlite:///:memory:")

    with engine.begin() as connection:
        connection.exec_driver_sql(
            """
            CREATE TABLE tasks (
                id INTEGER PRIMARY KEY
            )
            """
        )

    migrate_project_schema(engine)
    migrate_plan_schema(engine)
    migrate_task_attempt_schema(engine)
    migrate_artifact_schema(engine)
    migrate_artifact_schema(engine)

    inspector = inspect(engine)

    assert "artifacts" in inspector.get_table_names()

    columns = {
        column["name"]
        for column in inspector.get_columns("artifacts")
    }

    assert {
        "id",
        "project_id",
        "plan_id",
        "task_id",
        "task_attempt_id",
        "artifact_type",
        "name",
        "description",
        "uri",
        "content",
        "checksum",
        "created_by",
        "created_at",
    }.issubset(columns)
