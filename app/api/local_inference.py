"""Explicit owner-only real local model execution, no arbitrary provider URLs."""
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import select, func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from uuid import UUID
from pydantic import BaseModel, ConfigDict
from typing import Literal
from app.api.auth import require_owner
from app.api.organization_os import get_organization_session
from app.api.agent_packets import write
from app.api.local_model_queue import QueueRequest
from app.models.local_inference import LocalInference
from app.models.project import Project
from app.models.task import Task
from app.services import local_inference as service
from app.services.local_ollama import OllamaProvider, ensure_idle

router=APIRouter(prefix='/api/local-inference',tags=['local-inference'],dependencies=[Depends(require_owner)])


def get_provider_factory():
    return OllamaProvider


def get_idle_check():
    return ensure_idle


class RetryRequest(BaseModel):
    model_config=ConfigDict(extra='forbid')
    request_id:UUID
    confirm:Literal[True]


class InferenceRequest(QueueRequest):
    output_profile:Literal['text','python-web-v1','python-web-multifile-v1']='text'


@router.get('')
def list_runs(response:Response,session:Session=Depends(get_organization_session),
              project_id:int | None=Query(default=None,ge=1),
              before:int | None=Query(default=None,ge=1),attention_only:bool=False):
    response.headers['Cache-Control']='no-store'
    if project_id is not None and session.get(Project,project_id) is None:
        raise HTTPException(404,'Nie znaleziono projektu.')
    try:config=service.enabled_config();enabled=True
    except ValueError:config={};enabled=False
    query=select(LocalInference)
    if project_id is not None:
        query=query.join(Task,Task.id==LocalInference.task_id).where(Task.project_id==project_id)
    attention=query.where(LocalInference.state.in_(['queued','running','uncertain']))
    attention_count=session.scalar(select(func.count()).select_from(attention.subquery()))
    if attention_only:query=attention
    if before is not None:query=query.where(LocalInference.id<before)
    rows=list(session.scalars(query.order_by(LocalInference.id.desc()).limit(31)))
    return {'enabled':enabled,'model':config.get('model'),'concurrency':1,
            'timeout_seconds':config.get('timeout_seconds'),'tools_enabled':False,
            'project_id':project_id,'attention_count':attention_count,
            'next_cursor':rows[29].id if len(rows)>30 else None,
            'runs':[service.summary(run) for run in rows[:30]]}


@router.post('')
def enqueue(payload:InferenceRequest,response:Response,session:Session=Depends(get_organization_session)):
    data=payload.model_dump();data['request_id']=str(data['request_id'])
    return write(session,response,lambda:service.enqueue(session,**data))


@router.post('/{run_id}/run')
def run(run_id:int,response:Response,session:Session=Depends(get_organization_session),factory=Depends(get_provider_factory)):
    response.headers['Cache-Control']='no-store'
    try:return service.execute(session,run_id,factory)
    except LookupError as exc:session.rollback();raise HTTPException(404,str(exc)) from exc
    except ValueError as exc:session.rollback();raise HTTPException(409,str(exc)) from exc
    except SQLAlchemyError as exc:
        session.rollback();raise HTTPException(503,'Niepewny zapis. Odśwież historię wykonania; nie ponawiaj modelu automatycznie.') from exc


@router.post('/{run_id}/cancel')
def cancel(run_id:int,response:Response,session:Session=Depends(get_organization_session)):
    return write(session,response,lambda:service.cancel(session,run_id))


@router.post('/{run_id}/retry')
def retry(run_id:int,payload:RetryRequest,response:Response,session:Session=Depends(get_organization_session),check=Depends(get_idle_check)):
    try:check()
    except ValueError as exc:raise HTTPException(409,str(exc)) from exc
    return write(session,response,lambda:service.requeue(session,run_id,str(payload.request_id)))
