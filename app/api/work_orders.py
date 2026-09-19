"""Owner-only workbench. Does not expose any executor or host controls."""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.auth import require_owner
from app.api.organization_os import get_organization_session
from app.models.organization import OrganizationUnit
from app.models.project import Project
from app.models.plan import Plan
from app.models.task import Task, TaskAttempt
from app.models.work_order import WorkOrder
from app.models.artifact import Artifact
from app.models.local_inference import LocalInference
from app.services.project_guidance import project_guidance
from app.services.project_coordination import checkpoint
from app.services.agent_packets import prepare_packet, read_packet
from app.services.work_orders import create_order, fingerprint, website_starter, stored_criterion
from app.services.workspace_packages import create_package, package_summary, read_package
from app.services.agent_teams import delegate_order, delegation_details

router = APIRouter(prefix="/api/work-orders", tags=["work-orders"], dependencies=[Depends(require_owner)])


class Intake(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    request_id: UUID
    title: str = Field(min_length=1, max_length=160)
    goal: str = Field(min_length=10, max_length=6000)
    audience: str = Field(min_length=2, max_length=1000)
    constraints: str = Field(min_length=1, max_length=3000)
    organization_unit_id: int = Field(ge=1)
    acceptance_criteria: list[Annotated[str, Field(min_length=1, max_length=500)]] = Field(min_length=1, max_length=20)

    @field_validator("acceptance_criteria")
    @classmethod
    def unique_criteria(cls, value):
        if len(set(value)) != len(value):
            raise ValueError("Kryteria nie mogą się powtarzać.")
        return value


class PrepareNext(BaseModel):
    model_config = ConfigDict(extra='forbid')
    task_id: int = Field(ge=1)
    expected_revision: str = Field(pattern=r'^[0-9a-f]{64}$')


def detail(session: Session, order: WorkOrder) -> dict:
    project = session.get(Project, order.project_id)
    plan = session.get(Plan, order.plan_id)
    tasks = list(session.scalars(select(Task).where(Task.id.in_(order.task_ids), Task.project_id == order.project_id,
                                                   Task.plan_id == order.plan_id).order_by(Task.id)))
    attempts = list(session.scalars(select(TaskAttempt).where(TaskAttempt.task_id.in_(order.task_ids)).order_by(TaskAttempt.id)))
    latest = {attempt.task_id: attempt for attempt in attempts}
    artifacts = list(session.scalars(select(Artifact).where(Artifact.project_id == order.project_id).order_by(Artifact.id.desc()).limit(50)))
    result = {"request_id": order.request_id, "project_id": order.project_id, "plan_id": order.plan_id,
            "project_status": project.status.value, "brief": order.brief,
            "plan_status": plan.status.value if plan and plan.project_id == order.project_id else None,
            "execution_policy": "manual_resource_approval_required", "automatically_queued": False,
            "tasks": [{"id": task.id, "title": task.title, "status": task.status.value,
                       "approval_status": task.approval_status.value, "progress": task.progress,
                       "assigned_role": task.assigned_agent, "queued": task.queued_at is not None,
                       "attempt_status": latest[task.id].status if task.id in latest else None,
                       "delegation": delegation_details(session, task),
                       "completion_criterion": stored_criterion(task, index)}
                      for index, task in enumerate(tasks)],
            "artifacts": [{"id": a.id, "task_id": a.task_id, "type": a.artifact_type.value,
                           "name": a.name, "description": a.description} for a in artifacts]}
    runs = session.execute(select(LocalInference.id, LocalInference.task_id, LocalInference.state)
                           .where(LocalInference.task_id.in_([task.id for task in tasks]))).all()
    result['guidance'] = project_guidance(order.task_ids, result['tasks'], latest, runs, project.status.value)
    result['coordination'] = checkpoint(result, tasks, latest, runs)
    return result


@router.get("/options")
def options(response: Response, session: Session = Depends(get_organization_session)):
    response.headers["Cache-Control"] = "no-store"
    units = list(session.scalars(select(OrganizationUnit).where(OrganizationUnit.active.is_(True)).order_by(OrganizationUnit.sort_order, OrganizationUnit.id)))
    parents = set(session.scalars(select(OrganizationUnit.parent_id).where(OrganizationUnit.parent_id.is_not(None))))
    return {"units": [{"id": u.id, "key": u.os_key, "name": u.name} for u in units if u.id not in parents],
            "execution": "not_started", "inference": "local_qwen_owner_action",
            "runner": "python_web_v1_owner_action", "starter": "local_static_website_template"}


@router.post("", status_code=201)
def intake(payload: Intake, response: Response, session: Session = Depends(get_organization_session)):
    response.headers["Cache-Control"] = "no-store"
    brief = payload.model_dump(exclude={"request_id"})
    key = str(payload.request_id)
    try:
        replay = session.get(WorkOrder, key) is not None
        order = create_order(session, key, brief)
        session.commit()
        if replay:
            response.status_code = 200
        return detail(session, order)
    except LookupError as exc:
        session.rollback()
        raise HTTPException(422, str(exc)) from exc
    except ValueError as exc:
        session.rollback()
        raise HTTPException(409, str(exc)) from exc
    except IntegrityError as exc:
        session.rollback()
        order = session.get(WorkOrder, key)
        if order and order.request_hash == fingerprint(brief):
            response.status_code = 200
            return detail(session, order)
        raise HTTPException(409, "Konflikt zapisu. Odśwież listę przed ponowieniem.") from exc
    except SQLAlchemyError as exc:
        session.rollback()
        raise HTTPException(503, "Nie można zapisać zlecenia. Ponów z tym samym request_id.") from exc


@router.get("")
def list_orders(response: Response, before: int | None = Query(default=None, ge=1),
                session: Session = Depends(get_organization_session)):
    response.headers["Cache-Control"] = "no-store"
    query = select(WorkOrder).order_by(WorkOrder.project_id.desc())
    if before is not None:
        query = query.where(WorkOrder.project_id < before)
    orders = list(session.scalars(query.limit(21)))
    return {"orders": [{"request_id": o.request_id, "project_id": o.project_id,
                        "title": o.brief["title"], "created_at": o.created_at.isoformat()} for o in orders[:20]],
            "next_cursor": orders[19].project_id if len(orders) > 20 else None}


def required_order(session, project_id):
    order = session.scalar(select(WorkOrder).where(WorkOrder.project_id == project_id))
    if order is None:
        raise HTTPException(404, "Nie znaleziono zlecenia utworzonego w centrum realizacji.")
    return order


@router.get("/{project_id}")
def get_order(project_id: int, response: Response, session: Session = Depends(get_organization_session)):
    response.headers["Cache-Control"] = "no-store"
    return detail(session, required_order(session, project_id))


@router.post("/{project_id}/delegate")
def assign_order(project_id: int, response: Response, session: Session = Depends(get_organization_session)):
    response.headers["Cache-Control"] = "no-store"
    try:
        session.execute(text("BEGIN IMMEDIATE"))
        order = required_order(session, project_id)
        delegate_order(session, order)
        session.commit()
        return detail(session, order)
    except ValueError as exc:
        session.rollback()
        raise HTTPException(409, str(exc)) from exc
    except SQLAlchemyError as exc:
        session.rollback()
        raise HTTPException(503, "Niepewny wynik przydziału. Odśwież zlecenie przed ponowieniem.") from exc


@router.post('/{project_id}/prepare-next')
def prepare_next(project_id: int, payload: PrepareNext, response: Response,
                 session: Session = Depends(get_organization_session)):
    """Prepare exactly the stage the owner saw, atomically and without inference."""
    response.headers['Cache-Control'] = 'no-store'
    try:
        session.execute(text('BEGIN IMMEDIATE'))
        session.expire_all()
        order = required_order(session, project_id)
        current = detail(session, order)
        state = current['coordination']
        if (payload.expected_revision != state['revision'] or payload.task_id != state['task_id']):
            raise ValueError('Stan projektu zmienił się. Odśwież projekt; nie przygotowano innego etapu.')
        if not state['can_prepare']:
            raise ValueError('Etap wymaga wyjaśnienia blokady lub odbioru. Nie uruchomiono wykonania.')
        artifact = prepare_packet(session, payload.task_id)
        packet = read_packet(session, payload.task_id, artifact.id)
        # Persisted packet + its existing audit are the resumption point.
        session.commit()
        return {'project_id': project_id, 'instruction': packet,
                'model_invoked': False, 'automatically_queued': False}
    except HTTPException:
        session.rollback()
        raise
    except LookupError as exc:
        session.rollback()
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        session.rollback()
        raise HTTPException(409, str(exc)) from exc
    except SQLAlchemyError as exc:
        session.rollback()
        raise HTTPException(503, 'Niepewny zapis instrukcji. Odśwież projekt; ponowienie tego samego etapu nie tworzy drugiej instrukcji.') from exc


@router.post("/{project_id}/website-starter", status_code=201)
def make_starter(project_id: int, response: Response, session: Session = Depends(get_organization_session)):
    """Explicit owner action creates a fresh immutable version, not an AI execution."""
    response.headers["Cache-Control"] = "no-store"
    order = required_order(session, project_id)
    try:
        artifact = create_package(session, order.task_ids[1], website_starter(order.brief),
                                  "Szkielet strony z lokalnego szablonu; bez AI, wykonania i odbioru.")
        return package_summary(*read_package(session, order.task_ids[1], artifact.id))
    except SQLAlchemyError as exc:
        session.rollback()
        raise HTTPException(503, "Niepewny wynik zapisu paczki. Sprawdź wersje przed ponowieniem.") from exc
