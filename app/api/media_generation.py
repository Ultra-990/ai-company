"""Owner-only local graphics. Existing session/RBAC, no public ComfyUI proxy."""
from typing import Literal
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from app.api.auth import require_owner
from app.api.organization_os import get_organization_session
from app.models.media_generation import MediaGeneration
from app.services import media_generation as service
from app.services.comfyui_provider import ComfyProvider

router = APIRouter(prefix='/api/tasks', tags=['local-graphics'], dependencies=[Depends(require_owner)])


def get_provider():
    return ComfyProvider()


class GenerateRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    request_id: UUID
    prompt: str = Field(min_length=3, max_length=2000)
    seed: int = Field(default=20260913, ge=0, le=2**32-1, strict=True)
    confirm: Literal[True]

    @field_validator('prompt')
    @classmethod
    def clean_prompt(cls, value):
        value = value.strip()
        if len(value) < 3 or any(ord(c) < 32 and c not in '\n\t' for c in value):
            raise ValueError('Nieprawidłowy opis grafiki.')
        return value


class ReviewRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    checksum: str = Field(pattern=r'^[0-9a-f]{64}$')
    decision: Literal['accepted', 'rejected']
    reason: str = Field(min_length=5, max_length=1000)

    @field_validator('reason')
    @classmethod
    def meaningful_reason(cls, value):
        if len(value.strip()) < 5:
            raise ValueError('Podaj uzasadnienie odbioru.')
        return value.strip()


def checked(session, response, action):
    response.headers['Cache-Control'] = 'no-store'
    try:
        return action()
    except LookupError as exc:
        session.rollback(); raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        session.rollback(); raise HTTPException(409, str(exc)) from exc
    except SQLAlchemyError as exc:
        session.rollback()
        raise HTTPException(503, 'Niepewny zapis. Odśwież historię przed kolejnym generowaniem.') from exc


@router.get('/{task_id}/images')
def list_images(task_id: int, response: Response, session: Session = Depends(get_organization_session)):
    response.headers['Cache-Control'] = 'no-store'
    return {'jobs': [service.summary(run) for run in session.scalars(select(MediaGeneration)
        .where(MediaGeneration.task_id == task_id).order_by(MediaGeneration.id.desc()).limit(30))]}


@router.post('/{task_id}/images')
def generate(task_id: int, payload: GenerateRequest, response: Response,
             session: Session = Depends(get_organization_session), provider=Depends(get_provider)):
    return checked(session, response, lambda: service.submit(session, task_id, str(payload.request_id),
        payload.prompt, payload.seed, provider))


@router.post('/{task_id}/images/{job_id}/refresh')
def refresh(task_id: int, job_id: int, response: Response,
            session: Session = Depends(get_organization_session), provider=Depends(get_provider)):
    return checked(session, response, lambda: service.refresh(session, task_id, job_id, provider))


@router.get('/{task_id}/images/{job_id}/report')
def report(task_id: int, job_id: int, response: Response, session: Session = Depends(get_organization_session)):
    return checked(session, response, lambda: service.read_result(session, task_id, job_id)[0])


@router.get('/{task_id}/images/{job_id}/download')
def download(task_id: int, job_id: int, response: Response, session: Session = Depends(get_organization_session)):
    _, image = checked(session, response, lambda: service.read_result(session, task_id, job_id))
    return Response(image, media_type='image/png', headers={'Cache-Control': 'no-store',
        'X-Content-Type-Options': 'nosniff', 'Content-Disposition': f'attachment; filename="task-{task_id}-image-{job_id}.png"'})


@router.post('/{task_id}/images/{job_id}/review')
def review(task_id: int, job_id: int, payload: ReviewRequest, response: Response,
           session: Session = Depends(get_organization_session)):
    return checked(session, response, lambda: service.review(session, task_id, job_id,
        payload.checksum, payload.decision, payload.reason))
