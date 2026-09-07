from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import Session

from app.core.database import Base
from app.models.plan import Plan
from app.models.project import Project
from app.models.task import Task


def make_task(**kwargs) -> Task:
    """
    Tworzy Task zgodnie z podstawowym kontraktem istniejącego modelu.

    Jeżeli projekt używa innych wymaganych pól Task, należy dopasować
    wyłącznie tę funkcję pomocniczą do aktualnego konstruktora.
    """
    defaults = {
        "title": "Zadanie przypisane do planu",
        "description": "Wykonać krok planu.",
    }
    defaults.update(kwargs)
    return Task(**defaults)


def test_tasks_table_contains_project_and_plan_columns() -> None:
    engine = create_engine("sqlite:///:memory:")

    try:
        Base.metadata.create_all(engine)

        columns = {
            column["name"]
            for column in inspect(engine).get_columns("tasks")
        }

        assert {"project_id", "plan_id"} <= columns
    finally:
        engine.dispose()


def test_task_can_belong_to_project_and_plan() -> None:
    engine = create_engine("sqlite:///:memory:")

    try:
        Base.metadata.create_all(engine)

        with Session(engine) as session:
            project = Project(
                name="Projekt z zadaniem",
                business_goal="Dostarczyć funkcję domenową.",
            )
            plan = Plan(
                project=project,
                name="Plan implementacyjny",
                objective="Wdrożyć relację zadań.",
            )
            task = make_task(project=project, plan=plan)

            session.add(task)
            session.commit()

            task_id = task.id
            project_id = project.id
            plan_id = plan.id

        with Session(engine) as session:
            persisted_task = session.get(Task, task_id)
            persisted_project = session.get(Project, project_id)
            persisted_plan = session.get(Plan, plan_id)

            assert persisted_task is not None
            assert persisted_task.project_id == project_id
            assert persisted_task.plan_id == plan_id

            assert persisted_project is not None
            assert [item.id for item in persisted_project.tasks] == [task_id]

            assert persisted_plan is not None
            assert [item.id for item in persisted_plan.tasks] == [task_id]
    finally:
        engine.dispose()


def test_task_can_remain_unassigned_for_legacy_compatibility() -> None:
    engine = create_engine("sqlite:///:memory:")

    try:
        Base.metadata.create_all(engine)

        with Session(engine) as session:
            task = make_task()
            session.add(task)
            session.commit()
            task_id = task.id

        with Session(engine) as session:
            persisted_task = session.get(Task, task_id)

            assert persisted_task is not None
            assert persisted_task.project_id is None
            assert persisted_task.plan_id is None
    finally:
        engine.dispose()
