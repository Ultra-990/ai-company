from sqlalchemy.orm import configure_mappers

from app.models.artifact import Artifact, ArtifactType
from app.models.plan import Plan
from app.models.project import Project
from app.models.task import Task, TaskAttempt


def test_artifact_model_and_relations_are_configured() -> None:
    configure_mappers()

    assert Artifact.__tablename__ == "artifacts"
    assert ArtifactType.REPORT.value == "report"

    assert "artifacts" in Project.__mapper__.relationships
    assert "artifacts" in Plan.__mapper__.relationships
    assert "artifacts" in Task.__mapper__.relationships
    assert "attempts" in Task.__mapper__.relationships
    assert "task" in TaskAttempt.__mapper__.relationships
    assert "artifacts" in TaskAttempt.__mapper__.relationships


def test_artifact_has_expected_foreign_keys() -> None:
    columns = Artifact.__table__.c

    assert columns.project_id.foreign_keys
    assert columns.plan_id.foreign_keys
    assert columns.task_id.foreign_keys
    assert columns.task_attempt_id.foreign_keys
