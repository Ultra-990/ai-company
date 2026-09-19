from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.api.auth import require_owner
from app.api.agent_packets import write
from app.api.organization_os import get_organization_session
from app.models.artifact import Artifact, ArtifactType
from app.services import acceptance_cases as service
from app.services.requirement_checks import context

router = APIRouter(prefix='/api/tasks', tags=['acceptance-cases'], dependencies=[Depends(require_owner)])


class Plan(BaseModel):
    model_config = ConfigDict(extra='forbid')
    request_id: UUID
    source_checksum: str = Field(pattern=r'^[a-f0-9]{64}$')
    scope_checksum: str = Field(pattern=r'^[a-f0-9]{64}$')
    cases: service.Cases


@router.post('/{task_id}/workspace-packages/{package_id}/acceptance-plans')
def create(task_id: int, package_id: int, payload: Plan, response: Response,
           session: Session = Depends(get_organization_session)):
    data = payload.model_dump(mode='json')
    return write(session, response, lambda: service.create(session, task_id, package_id, **data))


@router.get('/{task_id}/workspace-packages/{package_id}/acceptance-plans')
def listing(task_id: int, package_id: int, response: Response, session: Session = Depends(get_organization_session)):
    response.headers['Cache-Control'] = 'no-store'
    try:
        context(session, task_id, package_id)
        rows = session.scalars(select(Artifact).where(Artifact.task_id == task_id,
            Artifact.artifact_type == ArtifactType.SPECIFICATION,
            Artifact.name.like(service.NAME + ':%')).order_by(Artifact.id.desc()).limit(20))
        plans = []
        for row in rows:
            try:
                plans.append(service.view(row, service.read(session, task_id, package_id, row.id, row.checksum)))
            except (ValueError, LookupError):
                plans.append({'id': row.id, 'invalid': True})
        return {'plans': plans, 'execution_enabled': service.execution_enabled()}
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    except SQLAlchemyError as exc:
        session.rollback()
        raise HTTPException(503, 'Nie można teraz odczytać planów. Spróbuj ponownie.') from exc
