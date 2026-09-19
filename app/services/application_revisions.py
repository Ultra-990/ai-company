"""Version-bound owner correction requests, reusing review, Qwen and runner history."""
import json
from uuid import UUID, uuid5
from sqlalchemy import select
from app.models.artifact import Artifact, ArtifactType
from app.models.local_inference import LocalInference
from app.models.package_run import PackageRun
from app.services import local_inference, package_runner
from app.services.agent_packets import latest_attempt, prepare_packet, digest
from app.services.application_profile import parse_sources, PROFILE, REPAIR_PROFILE
from app.services.result_review import apply_review
from app.services.workspace_packages import read_package, canonical_json

NAME='organization-os.application-revision.v1'
NAMESPACE=UUID('136aa86b-e8fa-40cc-ae3c-bee8ac98dddf')


def test_uuid(request_id):return str(uuid5(NAMESPACE,request_id))


def read_revision(session,revision_id):
    artifact=session.get(Artifact,revision_id)
    if not artifact or not artifact.name.startswith(NAME+':') or artifact.artifact_type!=ArtifactType.REPORT:
        raise LookupError('Nie znaleziono zgłoszenia poprawki.')
    if not artifact.content or digest(artifact.content)!=artifact.checksum:raise ValueError('Naruszona integralność zgłoszenia.')
    data=json.loads(artifact.content)
    if data.get('schema')!=NAME or data['input']['task_id']!=artifact.task_id:raise ValueError('Niezgodne zgłoszenie.')
    run=session.get(LocalInference,data['inference_id'])
    if not run or run.task_id!=artifact.task_id or run.packet_id!=data['packet_id'] or run.request_id!=data['input']['request_id']:
        raise ValueError('Niezgodne powiązanie wykonawcy.')
    if run.limits.get('output_profile','text')!=data.get('output_profile',PROFILE):
        raise ValueError('Niezgodny profil wykonania poprawki.')
    return artifact,data,run


def summary(session,revision_id):
    artifact,data,run=read_revision(session,revision_id)
    tested=session.scalar(select(PackageRun).where(PackageRun.request_id==test_uuid(data['input']['request_id'])))
    return {'id':artifact.id,**data['input'],'inference_id':run.id,'state':run.state,
            'error_code':run.error_code,'new_package_id':(run.metrics or {}).get('package_id'),
            'new_package_checksum':(run.metrics or {}).get('package_checksum'),
            'test_run_id':tested.id if tested else None,'test_state':tested.state if tested else None,
            'accepted':False}


def create(session,*,reviewer_role='owner',output_profile=PROFILE,**data):
    if output_profile not in {PROFILE,REPAIR_PROFILE}:raise ValueError('Nieobsługiwany profil poprawki.')
    name=NAME+':'+data['request_id']
    existing=session.scalar(select(Artifact).where(Artifact.name==name))
    if existing:
        _,saved,_=read_revision(session,existing.id)
        if saved['input']!=data or saved.get('output_profile',PROFILE)!=output_profile:
            raise ValueError('Identyfikator zgłoszenia wskazuje inną zmianę.')
        return summary(session,existing.id)
    source,payload=read_package(session,data['task_id'],data['package_id'])
    if source.checksum!=data['package_checksum']:raise ValueError('Wskazano inną wersję paczki.')
    attempt=latest_attempt(session,data['task_id'])
    if not attempt or not attempt.result_content or digest(attempt.result_content)!=attempt.result_checksum:
        raise ValueError('Brak aktualnego wyniku agenta z poprawną sumą.')
    files=parse_sources(attempt.result_content)
    if files!={f['path']:f['content'] for f in payload['files']}:
        raise ValueError('Paczka nie odpowiada ostatniemu wynikowi. Wybierz najnowszą wersję.')
    origin=session.scalar(select(LocalInference).where(LocalInference.attempt_id==attempt.id))
    if not origin or origin.metrics.get('package_id')!=source.id or origin.metrics.get('package_checksum')!=source.checksum:
        raise ValueError('Poprawki wymagają paczki powiązanej z wykonaniem Qwen.')
    reason=data['description']+'\n\nOczekiwany rezultat / test odbioru: '+data['expected_result']
    apply_review(session,data['task_id'],attempt_id=attempt.id,result_checksum=attempt.result_checksum,
                 accepted=False,reason=reason,evidence=data['evidence'],reviewer_role=reviewer_role)
    session.flush()
    packet=prepare_packet(session,data['task_id'])
    run=local_inference.enqueue(session,data['task_id'],packet.id,packet.checksum,data['request_id'],output_profile)
    content=canonical_json({'schema':NAME,'input':data,'base_attempt_id':attempt.id,
        'output_profile':output_profile,
        'base_result_checksum':attempt.result_checksum,'packet_id':packet.id,'inference_id':run['id']})
    receipt=Artifact(task_id=source.task_id,project_id=source.project_id,plan_id=source.plan_id,
        artifact_type=ArtifactType.REPORT,name=name,content=content,checksum=digest(content),created_by=reviewer_role,
        description='Żądanie nowej wersji; wcześniejszy wynik skierowano do poprawy. Bez automatycznego odbioru.')
    session.add(receipt);session.flush()
    return summary(session,receipt.id)


def execute(session,revision_id,provider_factory,runner):
    _,data,run=read_revision(session,revision_id);run_id=run.id
    session.rollback()
    generated=local_inference.execute(session,run_id,provider_factory)
    if generated['state']=='awaiting_review' and data['input']['auto_test']:
        metrics=generated['metrics']
        package_runner.start(session,data['input']['task_id'],metrics['package_id'],metrics['package_checksum'],
                             test_uuid(data['input']['request_id']),runner)
    return summary(session,revision_id)
