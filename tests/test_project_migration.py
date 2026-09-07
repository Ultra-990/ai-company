from sqlalchemy import create_engine, inspect

from app.db.migrations import migrate_project_schema


def test_project_migration_creates_table_idempotently(tmp_path) -> None:
    engine = create_engine(f"sqlite:///{tmp_path / 'projects.sqlite3'}")

    try:
        migrate_project_schema(engine)
        migrate_project_schema(engine)

        inspector = inspect(engine)
        assert "projects" in inspector.get_table_names()

        columns = {
            column["name"]
            for column in inspector.get_columns("projects")
        }

        assert {
            "id",
            "name",
            "business_goal",
            "description",
            "status",
            "organization_unit_id",
            "created_at",
            "updated_at",
            "started_at",
            "completed_at",
        } <= columns
    finally:
        engine.dispose()
