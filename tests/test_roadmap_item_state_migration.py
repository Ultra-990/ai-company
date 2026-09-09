from sqlalchemy import create_engine, inspect

from app.db.migrations import migrate_roadmap_item_state_schema


def test_roadmap_item_state_migration_is_idempotent(tmp_path) -> None:
    engine = create_engine(f"sqlite:///{tmp_path / 'roadmap.sqlite3'}")

    try:
        migrate_roadmap_item_state_schema(engine)
        migrate_roadmap_item_state_schema(engine)

        inspector = inspect(engine)

        assert "roadmap_item_states" in inspector.get_table_names()

        columns = {
            column["name"]
            for column in inspector.get_columns("roadmap_item_states")
        }

        assert {
            "item_id",
            "status",
            "evidence",
            "note",
            "updated_at",
        } <= columns

        indexes = {
            index["name"]
            for index in inspector.get_indexes("roadmap_item_states")
        }

        assert {
            "ix_roadmap_item_states_status",
            "ix_roadmap_item_states_updated_at",
        } <= indexes
    finally:
        engine.dispose()
