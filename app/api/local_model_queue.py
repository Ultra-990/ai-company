"""Owner-only rehearsal queue. No live adapter or background worker is registered."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.agent_packets import write
from app.api.auth import require_owner
from app.api.organization_os import get_organization_session
from app.models.local_model_job import LocalModelJob
from app.services.local_model_queue import FixtureProvider, cancel, enqueue, run_next, summary

router = APIRouter(prefix='/api/local-model-queue', tags=['local-model-rehearsal'], dependencies=[Depends(require_owner)])


class QueueRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    request_id: UUID
    task_id: int = Field(ge=1, strict=True)
    packet_id: int = Field(ge=1, strict=True)
    packet_checksum: str = Field(pattern=r'^[0-9a-f]{64}$')


@router.get('')
def list_jobs(response: Response, before: int | None = Query(default=None, ge=1), session: Session = Depends(get_organization_session)):
    response.headers['Cache-Control'] = 'no-store'
    query = select(LocalModelJob).order_by(LocalModelJob.id.desc()).limit(31)
    if before:
        query = query.where(LocalModelJob.id < before)
    rows = list(session.scalars(query))
    return {'mode': 'simulation', 'live_enabled': False, 'concurrency': 1,
            'reason': 'To kolejka symulacyjna. Rzeczywiste generowanie ma oddzielną historię lokalnego Qwen.',
            'jobs': [summary(job) for job in rows[:30]],
            'next_cursor': rows[29].id if len(rows) > 30 else None}


@router.post('')
def add_job(payload: QueueRequest, response: Response, session: Session = Depends(get_organization_session)):
    data = payload.model_dump(); data['request_id'] = str(data['request_id'])
    return write(session, response, lambda: enqueue(session, **data))


@router.post('/{job_id}/cancel')
def cancel_job(job_id: int, response: Response, session: Session = Depends(get_organization_session)):
    return write(session, response, lambda: cancel(session, job_id))


@router.post('/simulate-next')
def simulate(response: Response, session: Session = Depends(get_organization_session)):
    response.headers['Cache-Control'] = 'no-store'
    try:
        return run_next(session, FixtureProvider())
    except ValueError as exc:
        session.rollback(); raise HTTPException(409, str(exc)) from exc
    except SQLAlchemyError as exc:
        session.rollback()
        raise HTTPException(503, 'Niepewny zapis. Odśwież kolejkę. Nie uruchomiono automatycznej ponownej próby.') from exc
