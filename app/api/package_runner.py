from uuid import UUID
from typing import Literal
from fastapi import APIRouter, Depends, Response, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from app.api.auth import require_owner
from app.api.agent_packets import write
from app.api.organization_os import get_organization_session
from app.models.package_run import PackageRun
from app.services.container_runner import ContainerRunner, configuration
from app.services import package_runner as service
from app.services.workspace_packages import PackageIntegrityError, read_package

router=APIRouter(prefix='/api/package-runs',tags=['isolated-runner'],dependencies=[Depends(require_owner)])


def get_runner():
    from app.services.execution_profiles import RoutedContainerRunner
    return RoutedContainerRunner()


def get_preview_runner():
    from app.services.application_preview import PreviewRunner
    return PreviewRunner


class RunRequest(BaseModel):
    model_config=ConfigDict(extra='forbid')
    request_id:UUID
    task_id:int=Field(ge=1,strict=True)
    package_id:int=Field(ge=1,strict=True)
    package_checksum:str=Field(pattern=r'^[a-f0-9]{64}$')
    confirm_execution:Literal[True]


class PreviewRequest(RunRequest):
    path:str=Field(default='/',max_length=850)


class PackageReviewRequest(BaseModel):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)
    request_id:UUID
    context_checksum:str=Field(pattern=r'^[a-f0-9]{64}$')
    accepted:bool=Field(strict=True)
    confirm_review:Literal[True]
    criteria:str=Field(min_length=10,max_length=2000)
    evidence:str=Field(min_length=10,max_length=2000)

    @field_validator('criteria','evidence')
    @classmethod
    def valid_text(cls,value):
        if '\x00' in value:raise ValueError('Niedozwolony bajt NUL.')
        try:value.encode('utf-8')
        except UnicodeEncodeError as exc:raise ValueError('Nieprawidłowy tekst UTF-8.') from exc
        return value


@router.get('/{run_id}/package-review')
def package_review_context(run_id:int,response:Response,session:Session=Depends(get_organization_session)):
    from app.services.package_acceptance import review_context
    response.headers['Cache-Control']='no-store'
    try:return review_context(session,run_id)
    except LookupError as exc:raise HTTPException(404,str(exc)) from exc
    except (ValueError,PackageIntegrityError) as exc:raise HTTPException(409,str(exc)) from exc


@router.post('/{run_id}/package-review')
def package_review(run_id:int,payload:PackageReviewRequest,response:Response,session:Session=Depends(get_organization_session)):
    from app.services.package_acceptance import review
    data=payload.model_dump(exclude={'confirm_review'});data['request_id']=str(data['request_id'])
    try:return write(session,response,lambda:review(session,run_id,**data))
    except PackageIntegrityError as exc:session.rollback();raise HTTPException(409,str(exc)) from exc


@router.post('/preview')
def preview(payload:PreviewRequest,response:Response,session:Session=Depends(get_organization_session),factory=Depends(get_preview_runner)):
    from app.services.application_preview import response_of, validate_path
    response.headers['Cache-Control']='no-store'
    try:
        path=validate_path(payload.path)
        data=payload.model_dump(exclude={'confirm_execution','path'});data['request_id']=str(data['request_id'])
        run=service.start(session,runner=factory(path),preview_path=path,**data)
        reply={'run_id':run['id'],'source_checksum':run['package_checksum'],'response':response_of(run)}
        if path=='/':
            artifact,package=read_package(session,payload.task_id,payload.package_id)
            if artifact.checksum!=payload.package_checksum:
                raise ValueError('Zmieniła się suma paczki podglądu.')
            # Package GET intentionally returns metadata, not file contents.
            # Send only public CSS/classic JS after the isolated start succeeded.
            # Never expose Python, tests, README or arbitrary source paths here.
            reply['assets']={entry['path']:entry['content'] for entry in package['files']
                             if entry['path'] in {'app.js','style.css'} or
                             (entry['path'].startswith('static/') and entry['path'].endswith(('.css','.js')))}
            reply['assets'].update({entry['path']:'data:image/png;base64,'+entry['content']
                for entry in package['files'] if entry.get('encoding')=='base64' and entry.get('media_type')=='image/png'})
        return reply
    except LookupError as exc:session.rollback();raise HTTPException(404,str(exc)) from exc
    except (ValueError,PackageIntegrityError) as exc:session.rollback();raise HTTPException(409,str(exc)) from exc
    except SQLAlchemyError as exc:
        session.rollback();raise HTTPException(503,'Odśwież historię podglądu przed ponowieniem.') from exc


@router.get('')
def listing(response:Response,session:Session=Depends(get_organization_session)):
    response.headers['Cache-Control']='no-store'
    try:profile=configuration();enabled=True
    except ValueError:profile=None;enabled=False
    test_rows=list(session.scalars(select(PackageRun).where(PackageRun.profile['request_path'].as_string().is_(None)).order_by(PackageRun.id.desc()).limit(30)))
    preview_rows=list(session.scalars(select(PackageRun).where(PackageRun.profile['request_path'].as_string().is_not(None)).order_by(PackageRun.id.desc()).limit(5)))
    # Preview clicks must not push the downloadable tested version out of history.
    return {'enabled':enabled,'profile':profile,'runs':[service.summary(row) for row in test_rows+preview_rows]}


@router.post('')
def start(payload:RunRequest,response:Response,session:Session=Depends(get_organization_session),runner=Depends(get_runner)):
    response.headers['Cache-Control']='no-store'
    try:
        data=payload.model_dump(exclude={'confirm_execution'});data['request_id']=str(data['request_id'])
        return service.start(session,runner=runner,**data)
    except LookupError as exc:session.rollback();raise HTTPException(404,str(exc)) from exc
    except (ValueError,PackageIntegrityError) as exc:session.rollback();raise HTTPException(409,str(exc)) from exc
    except SQLAlchemyError as exc:
        session.rollback();raise HTTPException(503,'Niepewny zapis wyniku. Odśwież historię; nie uruchamiaj ponownie w ciemno.') from exc


@router.post('/{run_id}/reconcile')
def reconcile(run_id:int,response:Response,session:Session=Depends(get_organization_session),runner=Depends(get_runner)):
    return write(session,response,lambda:service.reconcile(session,run_id,runner))


@router.get('/{run_id}/candidate.zip')
def candidate(run_id:int,session:Session=Depends(get_organization_session)):
    try:content=service.candidate_zip(session,run_id)
    except LookupError as exc:raise HTTPException(404,str(exc)) from exc
    except (ValueError,PackageIntegrityError) as exc:raise HTTPException(409,str(exc)) from exc
    return Response(content,media_type='application/zip',headers={'Cache-Control':'no-store',
        'X-Content-Type-Options':'nosniff','Content-Disposition':f'attachment; filename="candidate-{run_id}.zip"'})


@router.post('/{run_id}/release')
def release(run_id:int,response:Response,session:Session=Depends(get_organization_session)):
    try:return write(session,response,lambda:service.release(session,run_id))
    except PackageIntegrityError as exc:session.rollback();raise HTTPException(409,str(exc)) from exc


@router.get('/{run_id}/delivery-readiness')
def delivery_readiness(run_id:int,response:Response,session:Session=Depends(get_organization_session)):
    response.headers['Cache-Control']='no-store'
    try:return service.delivery_readiness(session,run_id)
    except LookupError as exc:raise HTTPException(404,str(exc)) from exc
    except SQLAlchemyError as exc:
        session.rollback();raise HTTPException(503,'Nie można odczytać gotowości wydania. Spróbuj ponownie.') from exc


@router.get('/{run_id}/released.zip')
def released(run_id:int,session:Session=Depends(get_organization_session)):
    try:content=service.released_zip(session,run_id)
    except LookupError as exc:raise HTTPException(404,str(exc)) from exc
    except (ValueError,PackageIntegrityError) as exc:raise HTTPException(409,str(exc)) from exc
    return Response(content,media_type='application/zip',headers={'Cache-Control':'no-store',
        'X-Content-Type-Options':'nosniff','Content-Disposition':f'attachment; filename="release-{run_id}.zip"'})


@router.get('/{run_id}/handoff')
def handoff(run_id:int,response:Response,session:Session=Depends(get_organization_session)):
    """Owner-only draft; does not contact a model, execute code or publish."""
    from app.services.delivery_handoff import handoff as read_handoff
    response.headers['Cache-Control']='no-store'
    response.headers['X-Content-Type-Options']='nosniff'
    try:return read_handoff(session,run_id)
    except LookupError as exc:raise HTTPException(404,str(exc)) from exc
    except (ValueError,PackageIntegrityError) as exc:raise HTTPException(409,str(exc)) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(503,'Nie można odczytać dokumentów wydania. Spróbuj ponownie.') from exc
