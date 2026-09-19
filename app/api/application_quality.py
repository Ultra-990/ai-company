"""Explicit authorization for one bounded automatic repair cycle."""
from typing import Literal
from uuid import UUID
from fastapi import APIRouter,Depends,Response,HTTPException
from pydantic import BaseModel,ConfigDict,Field,model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from app.api.auth import require_owner
from app.api.agent_packets import write
from app.api.organization_os import get_organization_session
from app.api.local_inference import get_provider_factory
from app.api.package_runner import get_runner,get_preview_runner
from app.models.artifact import Artifact
from app.services import application_quality as service
from app.services.workspace_packages import PackageIntegrityError

router=APIRouter(prefix='/api/application-quality',tags=['automatic-quality'],dependencies=[Depends(require_owner)])


class QualityRequest(BaseModel):
    model_config=ConfigDict(extra='forbid')
    request_id:UUID
    task_id:int=Field(ge=1,strict=True)
    package_id:int=Field(ge=1,strict=True)
    package_checksum:str=Field(pattern=r'^[a-f0-9]{64}$')
    max_repairs:int=Field(default=2,ge=1,le=2,strict=True)
    confirm_automatic_repairs:Literal[True]
    acceptance_plan_id:int|None=Field(default=None,ge=1,strict=True)
    acceptance_plan_checksum:str|None=Field(default=None,pattern=r'^[a-f0-9]{64}$')

    @model_validator(mode='after')
    def plan_pair(self):
        if (self.acceptance_plan_id is None)!=(self.acceptance_plan_checksum is None):
            raise ValueError('Plan przypadków wymaga ID i sumy kontrolnej.')
        return self


@router.post('')
def create(payload:QualityRequest,response:Response,session:Session=Depends(get_organization_session)):
    data=payload.model_dump(exclude={'confirm_automatic_repairs'},exclude_none=True);data['request_id']=str(data['request_id'])
    try:return write(session,response,lambda:service.create(session,**data))
    except PackageIntegrityError as exc:session.rollback();raise HTTPException(409,str(exc)) from exc


@router.get('')
def listing(response:Response,session:Session=Depends(get_organization_session)):
    response.headers['Cache-Control']='no-store'
    rows=list(session.scalars(select(Artifact.id).where(Artifact.name.like(service.NAME+':request:%')).order_by(Artifact.id.desc()).limit(20)))
    try:return {'cycles':[service.summary(session,id_) for id_ in rows]}
    except (ValueError,LookupError) as exc:raise HTTPException(409,str(exc)) from exc


@router.post('/{id_}/stop')
def stop(id_:int,response:Response,session:Session=Depends(get_organization_session)):
    return write(session,response,lambda:service.stop(session,id_))


@router.post('/{id_}/run')
def run(id_:int,response:Response,session:Session=Depends(get_organization_session),provider=Depends(get_provider_factory),runner=Depends(get_runner),preview_factory=Depends(get_preview_runner)):
    response.headers['Cache-Control']='no-store'
    try:return service.execute(session,id_,provider,runner,preview_factory)
    except LookupError as exc:session.rollback();raise HTTPException(404,str(exc)) from exc
    except (ValueError,PackageIntegrityError) as exc:session.rollback();raise HTTPException(409,str(exc)) from exc
    except SQLAlchemyError as exc:
        session.rollback();raise HTTPException(503,'Niepewny zapis. Odśwież cykle; ponów ten sam cykl, nie twórz nowego.') from exc
