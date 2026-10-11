"""Opt-in full model revision of the pinned LICZNIK LITER canary package."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import shutil
import sys
from uuid import uuid4

from fastapi.encoders import jsonable_encoder
from sqlalchemy import select

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import app.main  # Register all persisted model tables for standalone execution.
from app.core.database import create_database_engine,create_session_factory
from app.models.artifact import Artifact
from app.models.local_inference import LocalInference
from app.models.package_run import PackageRun
from app.services import application_revisions,container_runner,local_inference,package_runner
from app.services.application_profile import PROFILE
from app.services.local_ollama import OllamaProvider,configuration
from app.services.workspace_packages import read_package
from scripts.compare_local_models import check_idle
from scripts.filewise_production_canary import output_directory

SOURCE=Path('/home/marcin/ai-company-workspaces/filewise-production-canary-20261011-02')
SOURCE_DB_SHA256='5d546bf4a25c27104ca2e92723eb7aa66e3df73328725d3a54df8035d62a47d6'
SOURCE_REPORT_SHA256='9c2cc99fbf58e9fc2c12c049b7c7ce24dee60d3b349f7bcca543840be5c55be7'
HARNESS_SHA256='f0bdbed665f3cbccea72cf441b226e3ae619e3cf4b084bfd0a0120a11de86d8d'
PACKAGE_ID=3
PACKAGE_CHECKSUM='3a529586c94acef80f9ea95fce97d0c30f9fa146adcb14d1991f35786fc7567d'

DESCRIPTION='''Pełna rewizja compact-v2 po rzeczywistym izolowanym teście. Zachowaj cały
kontrakt API, UI, sześć plików i zwięzłość. Obecne test_app.py błędnie konstruuje
BaseHTTPRequestHandler przez H(None, None, None), co wywołuje próbę None.makefile.
Napisz pełną nową wersję wszystkich źródeł. Testy mają ćwiczyć rzeczywisty handler
przez prawidłowy socket/serwer HTTP albo równie rzeczywistą bezpieczną konstrukcję,
bez atrap implementujących zachowanie zamiast aplikacji. Nie osłabiaj asercji.'''
EXPECTED='''Co najmniej sześć sensownych asercji przechodzi dla rzeczywistej aplikacji:
/health, poprawne liczenie liter, pusty text, duplikat, dodatkowy parametr, limit
długości i 404. Zachowaj lokalne CSS/JS, encodeURIComponent, textContent, aria-live,
brak zapisu oraz brak usług zewnętrznych. Zamrożony niezależny harness także przechodzi.'''
EVIDENCE=[
    'Pinned package 3, checksum '+PACKAGE_CHECKSUM+'.',
    'Isolated package run 1 failed: six model tests raised because H(None,None,None) calls None.makefile.',
    'Frozen independent HTTP probes are retained unchanged; no product requirement is removed.',
]


def file_sha(path):return sha256(path.read_bytes()).hexdigest()


def validate_source():
    if (not SOURCE.is_dir() or SOURCE.is_symlink()
            or file_sha(SOURCE/'isolated.db')!=SOURCE_DB_SHA256
            or file_sha(SOURCE/'report.json')!=SOURCE_REPORT_SHA256
            or file_sha(SOURCE/'independent-harness.py')!=HARNESS_SHA256):
        raise ValueError('pinned_canary_source_changed')


def revision_input(request_id):
    return {'task_id':1,'package_id':PACKAGE_ID,'package_checksum':PACKAGE_CHECKSUM,
        'request_id':request_id,'description':DESCRIPTION,'expected_result':EXPECTED,
        'evidence':EVIDENCE,'auto_test':True}


def write_report(path,data):
    path.write_text(json.dumps(jsonable_encoder(data),ensure_ascii=False,indent=2),encoding='utf-8')


def run(destination):
    validate_source()
    destination.mkdir(mode=0o700,parents=False,exist_ok=False)
    database=destination/'isolated.db';shutil.copy2(SOURCE/'isolated.db',database);database.chmod(0o600)
    harness=destination/'independent-harness.py';shutil.copy2(SOURCE/'independent-harness.py',harness)
    if file_sha(harness)!=HARNESS_SHA256:raise ValueError('copied_harness_changed')
    engine=create_database_engine('sqlite:///'+str(database));factory=create_session_factory(engine)
    fixed=configuration()
    if fixed['num_ctx']!=16384 or fixed['num_predict']!=4096:raise ValueError('canary_model_limits_changed')
    fixed=fixed|{'application_generation_strategy':'filewise-v1'}
    local_inference.enabled_config=lambda:dict(fixed)
    local_inference.ensure_idle=check_idle
    local_inference.FILEWISE_EVIDENCE_ROOT=destination/'private-evidence'
    def runner_config():return container_runner.configuration()|{'harness_checksum':HARNESS_SHA256}
    package_runner.configuration=runner_config
    class CheckedRunner(container_runner.ContainerRunner):
        def run(self,*args,**kwargs):check_idle();return super().run(*args,**kwargs)
    request_id=str(uuid4())
    report={'schema':'filewise-production-canary-revision.v1','case_version':'compact-v2-full-revision-1',
        'source':{'database_sha256':SOURCE_DB_SHA256,'report_sha256':SOURCE_REPORT_SHA256,
            'harness_sha256':HARNESS_SHA256,'package_id':PACKAGE_ID,'package_checksum':PACKAGE_CHECKSUM},
        'revision_scope':revision_input(request_id),'state':'running','new_sources':None,
        'new_evidence':[],'isolated_test':{'state':'not_created'},'owner_accepted':False,
        'candidate_created':False,'deployed':False}
    try:
        with factory() as session:
            source,payload=read_package(session,1,PACKAGE_ID)
            if source.checksum!=PACKAGE_CHECKSUM:raise ValueError('pinned_package_changed')
            report['base_sources']={item['path']:item['content'] for item in payload['files']}
            created=application_revisions.create(session,output_profile=PROFILE,
                reviewer_role='automated_qa',**revision_input(request_id));session.commit()
            report['revision_id']=created['id'];report['inference_id']=created['inference_id']
            queued=session.get(LocalInference,created['inference_id'])
            if (queued.limits.get('num_ctx')!=32768
                    or queued.limits.get('application_generation_strategy')!='filewise-v1'):
                raise ValueError('full_revision_profile_changed')
            result=application_revisions.execute(session,created['id'],OllamaProvider,
                CheckedRunner(harness=harness));report['revision']=result
            report['state']=result['state'];report['isolated_test']={'run_id':result['test_run_id'],
                'state':result['test_state'] or 'not_created'}
            if result['new_package_id']:
                _,new_payload=read_package(session,1,result['new_package_id'])
                report['new_sources']={item['path']:item['content'] for item in new_payload['files']}
            if result['state']!='awaiting_review' or result['test_state']!='passed':
                raise RuntimeError('full_revision_or_isolated_test_failed')
    except Exception as exc:
        report['failure']={'type':type(exc).__name__,'message':str(exc)[:1000]}
        raise
    finally:
        with factory() as session:
            report['inferences']=[{'id':row.id,'state':row.state,'error_code':row.error_code,
                'attempt_id':row.attempt_id,'metrics':row.metrics,'limits':row.limits}
                for row in session.scalars(select(LocalInference).order_by(LocalInference.id))]
            report['tests']=[{'id':row.id,'state':row.state,'package_id':row.package_id,
                'report_id':row.report_id,'result':row.result}
                for row in session.scalars(select(PackageRun).order_by(PackageRun.id))]
            evidence=list(session.scalars(select(Artifact).where(
                Artifact.name.like('local-inference.filewise-evidence.%')).order_by(Artifact.id)))
            report['new_evidence']=[{'artifact_id':item.id,'checksum':item.checksum,
                'task_attempt_id':item.task_attempt_id} for item in evidence if item.id>2]
        engine.dispose()
        report['result_database_sha256']=file_sha(database)
        write_report(destination/'report.json',report)
    return 0


def main(argv=None):
    parser=argparse.ArgumentParser()
    parser.add_argument('--run',action='store_true')
    parser.add_argument('--output',type=output_directory,required=True)
    args=parser.parse_args(argv)
    if not args.run:parser.error('--run is required')
    return run(args.output)


if __name__=='__main__':sys.exit(main())
