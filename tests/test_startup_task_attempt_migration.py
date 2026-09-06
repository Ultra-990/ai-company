from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, text

import app.main as main_module


def test_startup_migrates_legacy_task_attempt_schema(
    tmp_path,
    monkeypatch,
) -> None:
    """Start aplikacji uzupełnia pola prób w historycznej bazie SQLite."""
    database_path = tmp_path / "legacy-task-attempts.db"
    engine = create_engine(f"sqlite:///{database_path}")

    try:
        with engine.begin() as connection:
            connection.execute(
                text(
                    """
                    CREATE TABLE task_attempts (
                        id INTEGER PRIMARY KEY,
                        task_id INTEGER NOT NULL,
                        worker_id VARCHAR(100) NOT NULL,
                        status VARCHAR(20) NOT NULL DEFAULT 'started',
                        started_at DATETIME NOT NULL,
                        finished_at DATETIME,
                        error_summary TEXT
                    )
                    """
                )
            )

        monkeypatch.setattr(main_module, "engine", engine)

        with TestClient(main_module.app) as client:
            response = client.get("/health")

        assert response.status_code == 200

        columns = {
            column["name"]
            for column in inspect(engine).get_columns("task_attempts")
        }

        assert {
            "result_content",
            "result_checksum",
            "verification_status",
            "verification_reason",
            "verified_at",
        } <= columns
    finally:
        engine.dispose()
