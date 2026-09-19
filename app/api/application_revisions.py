from uuid import UUID
from typing import Literal
from fastapi import APIRouter, Depends, Response, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from app.api.auth import require_owner
from app.api.agent_packets import write
from app.api.organization_os import get_organization_session
from app.api.local_inference import get_provider_factory
from app.api.package_runner import get_runner
from app.models.artifact import Artifact
from app.services import application_revisions as service
from app.services.workspace_packages import PackageIntegrityError

router=APIRouter(prefix='/api/application-revisions',tags=['application-revisions'],dependencies=[Depends(require_owner)])


class RevisionRequest(BaseModel):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)
    request_id:UUID
    task_id:int=Field(ge=1,strict=True)
    package_id:int=Field(ge=1,strict=True)
    package_checksum:str=Field(pattern=r'^[a-f0-9]{64}$')
    description:str=Field(min_length=8,max_length=1000)
    expected_result:str=Field(min_length=8,max_length=1000)
    evidence:list[str]=Field(min_length=1,max_length=10)
    auto_test:bool=False
    confirm_revision:Literal[True]

    @field_validator('evidence')
    @classmethod
    def check_evidence(cls,values):
        if any(not v.strip() or len(v)>500 or '\x00' in v for v in values):raise ValueError('Podaj krótkie dowody kontroli.')
        return [v.strip() for v in values]

    @field_validator('description','expected_result')
    @classmethod
    def check_text(cls,value):
        if '\x00' in value:raise ValueError('Nieprawidłowy tekst.')
        value.encode('utf-8');return value


@router.post('')
def create(payload:RevisionRequest,response:Response,session:Session=Depends(get_organization_session)):
    data=payload.model_dump(exclude={'confirm_revision'});data['request_id']=str(data['request_id'])
    try:return write(session,response,lambda:service.create(session,**data))
    except PackageIntegrityError as exc:session.rollback();raise HTTPException(409,str(exc)) from exc


@router.get('')
def listing(response:Response,session:Session=Depends(get_organization_session)):
    response.headers['Cache-Control']='no-store'
    rows=session.scalars(select(Artifact.id).where(Artifact.name.like(service.NAME+':%')).order_by(Artifact.id.desc()).limit(30))
    try:return {'revisions':[service.summary(session,id_) for id_ in rows]}
    except (ValueError,LookupError) as exc:raise HTTPException(409,str(exc)) from exc


@router.post('/{revision_id}/run')
def run(revision_id:int,response:Response,session:Session=Depends(get_organization_session),provider=Depends(get_provider_factory),runner=Depends(get_runner)):
    response.headers['Cache-Control']='no-store'
    try:return service.execute(session,revision_id,provider,runner)
    except LookupError as exc:session.rollback();raise HTTPException(404,str(exc)) from exc
    except (ValueError,PackageIntegrityError) as exc:session.rollback();raise HTTPException(409,str(exc)) from exc
    except SQLAlchemyError as exc:session.rollback();raise HTTPException(503,'Odśwież historię przed ponowieniem; niepewny zapis.') from exc
