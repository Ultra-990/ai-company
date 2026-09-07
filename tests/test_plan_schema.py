from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import Session

from app.core.database import Base
from app.models.plan import Plan, PlanStatus
from app.models.project import Project


def test_plans_table_is_created_with_expected_columns() -> None:
    engine = create_engine("sqlite:///:memory:")

    try:
        Base.metadata.create_all(engine)

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
            "status",
            "created_at",
            "updated_at",
        } <= columns
    finally:
        engine.dispose()


def test_plan_is_persisted_with_project_relationship() -> None:
    engine = create_engine("sqlite:///:memory:")

    try:
        Base.metadata.create_all(engine)

        with Session(engine) as session:
            project = Project(
                name="Projekt nadrzędny",
                business_goal="Zrealizować cel biznesowy.",
            )
            plan = Plan(
                name="Plan wykonawczy",
                objective="Zrealizować etap projektu.",
                status=PlanStatus.READY,
                project=project,
            )

            session.add(plan)
            session.commit()
            plan_id = plan.id
            project_id = project.id

        with Session(engine) as session:
            persisted_plan = session.get(Plan, plan_id)
            persisted_project = session.get(Project, project_id)

            assert persisted_plan is not None
            assert persisted_plan.status is PlanStatus.READY
            assert persisted_plan.project_id == project_id
            assert persisted_plan.project is not None
            assert persisted_plan.project.name == "Projekt nadrzędny"

            assert persisted_project is not None
            assert len(persisted_project.plans) == 1
            assert persisted_project.plans[0].id == plan_id
    finally:
        engine.dispose()
