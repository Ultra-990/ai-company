from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import Session

from app.core.database import Base
from app.models.organization import OrganizationUnit
from app.models.project import Project, ProjectStatus


def test_projects_table_is_created_with_expected_columns() -> None:
    engine = create_engine("sqlite:///:memory:")

    try:
        Base.metadata.create_all(engine)

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
            "status",
            "organization_unit_id",
            "created_at",
            "updated_at",
        } <= columns
    finally:
        engine.dispose()


def test_project_is_persisted_with_organization_relationship() -> None:
    engine = create_engine("sqlite:///:memory:")

    try:
        Base.metadata.create_all(engine)

        with Session(engine) as session:
            organization = OrganizationUnit(
                name="Dział produktu",
                unit_type="department",
            )
            project = Project(
                name="Automatyzacja obsługi klienta",
                business_goal="Skrócić czas pierwszej odpowiedzi.",
                status=ProjectStatus.PLANNED,
                organization_unit=organization,
            )

            session.add(project)
            session.commit()
            project_id = project.id

        with Session(engine) as session:
            persisted_project = session.get(Project, project_id)

            assert persisted_project is not None
            assert persisted_project.status is ProjectStatus.PLANNED
            assert persisted_project.organization_unit is not None
            assert persisted_project.organization_unit.name == "Dział produktu"
    finally:
        engine.dispose()
