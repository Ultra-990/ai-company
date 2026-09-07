from sqlalchemy import create_engine, inspect

from app.db.migrations import migrate_plan_schema, migrate_project_schema


def test_plan_migration_creates_table_idempotently(tmp_path) -> None:
    engine = create_engine(f"sqlite:///{tmp_path / 'plans.sqlite3'}")

    try:
        migrate_project_schema(engine)
        migrate_plan_schema(engine)
        migrate_plan_schema(engine)

        inspector = inspect(engine)
        assert "plans" in inspector.get_table_names()

        columns = {
            column["name"]
            for column in inspector.get_columns("plans")
        }

        assert {
            "id",
            "project_id",
            "name",
            "objective",
            "description",
            "status",
            "created_at",
            "updated_at",
            "started_at",
            "completed_at",
        } <= columns
    finally:
        engine.dispose()
