from sqlalchemy import create_engine, text

from app.db.migrations import migrate_legacy_organization_os_enum_values


def test_legacy_organization_os_enum_migration_is_idempotent(tmp_path) -> None:
    engine = create_engine(f"sqlite:///{tmp_path / 'legacy.db'}")

    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE projects (status VARCHAR(32))"))
        connection.execute(
            text("CREATE TABLE tasks (resource_class VARCHAR(32))")
        )
        connection.execute(
            text("INSERT INTO projects (status) VALUES ('ACTIVE')")
        )
        connection.execute(
            text("INSERT INTO tasks (resource_class) VALUES ('MEDIUM')")
        )
        connection.execute(
            text("INSERT INTO tasks (resource_class) VALUES ('HEAVY')")
        )

    migrate_legacy_organization_os_enum_values(engine)
    migrate_legacy_organization_os_enum_values(engine)

    with engine.connect() as connection:
        assert connection.scalar(text("SELECT status FROM projects")) == "IN_PROGRESS"
        assert connection.execute(
            text("SELECT resource_class FROM tasks ORDER BY rowid")
        ).scalars().all() == ["CPU", "CPU_HEAVY"]

    engine.dispose()
