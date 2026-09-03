from __future__ import annotations

from sqlalchemy import create_engine, inspect, text

from app.services.approvals import ApprovalRepository
from app.services.audit import AuditRepository


def test_approval_audit_events_have_structured_safe_correlation(
    tmp_path,
) -> None:
    database_url = f"sqlite:///{tmp_path / 'audit-phase4.sqlite3'}"
    approvals = ApprovalRepository(database_url)
    audit = AuditRepository(database_url)

    try:
        request = approvals.create_tool_request(
            task_id=123,
            tool_name="write_project_file",
            arguments={
                "path": "reports/private.txt",
                "content": "TAJNA_TRESC_NIE_MOZE_TRAFiC_DO_AUDYTU",
            },
        )

        approvals.approve(request.id, reason="Weryfikacja właściciela")
        approvals.begin_execution(
            request.id,
            tool_name="write_project_file",
            arguments_digest=request.arguments_digest,
        )
        approvals.finish_execution(request.id)

        events = audit.list_recent(limit=10)
        correlated = [
            event
            for event in events
            if event.approval_request_id == request.id
        ]

        assert [event.operation for event in reversed(correlated)] == [
            "approved",
            "execution_started",
            "executed",
        ]

        for event in correlated:
            assert event.task_id == 123
            assert event.tool_name == "write_project_file"
            assert event.arguments_digest == request.arguments_digest
            assert "TAJNA_TRESC_NIE_MOZE_TRAFiC_DO_AUDYTU" not in event.reason
            assert "reports/private.txt" not in event.reason
    finally:
        audit.close()
        approvals.close()


def test_audit_schema_migration_upgrades_legacy_table(tmp_path) -> None:
    database_path = tmp_path / "legacy-audit.sqlite3"
    database_url = f"sqlite:///{database_path}"
    engine = create_engine(database_url)

    try:
        with engine.begin() as connection:
            connection.execute(
                text(
                    """
                    CREATE TABLE audit_events (
                        id INTEGER PRIMARY KEY,
                        created_at DATETIME NOT NULL,
                        event_type VARCHAR(64) NOT NULL,
                        operation VARCHAR(64) NOT NULL,
                        decision VARCHAR(32) NOT NULL,
                        allowed BOOLEAN NOT NULL,
                        reason TEXT NOT NULL
                    )
                    """
                )
            )

        repository = AuditRepository(database_url)
        try:
            columns = {
                column["name"]
                for column in inspect(engine).get_columns("audit_events")
            }

            assert {
                "approval_request_id",
                "task_id",
                "tool_name",
                "arguments_digest",
            }.issubset(columns)
        finally:
            repository.close()
    finally:
        engine.dispose()
