from sqlalchemy import create_engine, inspect, text

from app.db.migrations import migrate_task_roadmap_item_schema


def test_task_roadmap_item_migration_is_idempotent(tmp_path) -> None:
    engine = create_engine(f"sqlite:///{tmp_path / 'tasks.sqlite3'}")

    try:
        with engine.begin() as connection:
            connection.execute(
                text(
                    """
                    CREATE TABLE tasks (
                        id INTEGER PRIMARY KEY,
                        title VARCHAR(200) NOT NULL,
                        created_at DATETIME NOT NULL
                    )
                    """
                )
            )

        migrate_task_roadmap_item_schema(engine)
        migrate_task_roadmap_item_schema(engine)

        inspector = inspect(engine)

        columns = {
            column["name"]
            for column in inspector.get_columns("tasks")
        }
        assert "roadmap_item_id" in columns

        indexes = {
            index["name"]
            for index in inspector.get_indexes("tasks")
        }
        assert "ix_tasks_roadmap_item_id" in indexes
    finally:
        engine.dispose()
