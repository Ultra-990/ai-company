"""Request one app.py-only route repair bound to verified PLAN ZAJĘĆ evidence."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys
from uuid import uuid4

from sqlalchemy import select

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import app.main  # Register persisted model tables.
from app.core.database import create_database_engine,create_session_factory
from app.models.local_inference import LocalInference
from app.models.package_run import PackageRun
from app.services import application_revisions,container_runner,local_inference,package_runner
from app.services.application_profile import REPAIR_PROFILE,parse_sources
from app.services.local_ollama import OllamaProvider,configuration
from app.services.workspace_packages import read_package
from scripts.compare_local_models import check_idle
from scripts.filewise_application_provider import FilewiseApplicationProvider

PILOT=Path('/home/marcin/ai-company-workspaces/workshop-catalog-r59rfvqy')
ORIGINAL=PILOT/'report.json'
SOURCE=PILOT/'repair-2'/'report.json'
ROUTES=PILOT/'routes-check-3'/'report.json'
HARNESS=PILOT/'independent-harness.py'
ORIGINAL_SHA256='80c6bb4d63dfd3fabedc8a2d6a7b0b4808cd61fbddbfa91c6a269c3704aee1e5'
SOURCE_SHA256='7d28033d294b96281ae2d22b2c41f64d226a000301c3b7392455ca6a397d1a74'
ROUTES_SHA256='9ce14a5268ee443f4624a76111a5201af1788c0fc55a9956d9d1f6dae52cd824'
HARNESS_SHA256='29904434ad2a8174ab02a0afc5d38f779217068f87aa43a2e4f3ca22fc54b8fd'
PACKAGE_ID=11
PACKAGE_CHECKSUM='1f0caa952c648f5ac318464a6dfb16f02c38f59c9593980d8f519a8bed4de816'
ORIGINAL_APP_SHA256='aa5986dbf8495fb6b2a223fc2b07aa4393e127c4e16aecfc993715bf4c336e27'
CHANGED_FILES={'app.py'}
DESCRIPTION=('Tylko app.py. Pełne ścieżki /api/sessions;extra?day=all&level=all, /health;extra '
    'i /;extra: 404. Zachowaj /, /health, /style.css, /app.js, poprawne /api/sessions, '
    'parser day/level, katalog i JSON.')
EXPECTED=('Pełny app.py; średniki: 404; all/all: 200 i 6 rekordów. Inne 5 plików i harness bez zmian.')


def digest(path):return sha256(path.read_bytes()).hexdigest()


def save(path,value):
    temporary=path.with_suffix('.tmp');temporary.write_text(
        json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8');temporary.replace(path)


def checked(path):
    if any(item.is_symlink() for item in (path,*path.parents)):raise ValueError('Symlink evidence is not allowed')
    resolved=path.resolve(strict=True)
    if not resolved.is_relative_to(PILOT.resolve(strict=True)):raise ValueError('Evidence is outside pilot')
    return resolved


def original_state():
    raw=checked(ORIGINAL).read_bytes()
    if sha256(raw).hexdigest()!=ORIGINAL_SHA256:
        raise ValueError('Original workshop delivery changed')
    report=json.loads(raw);files=report.get('final_sources',{});quality=report.get('quality',{})
    if (report.get('schema')!='workshop-catalog-delivery.v1' or report.get('candidate_created') is not True
            or quality.get('state')!='passed' or sha256(files.get('app.py','').encode()).hexdigest()!=ORIGINAL_APP_SHA256):
        raise ValueError('Original workshop delivery is not the fixed tested candidate')
    parse_sources(json.dumps({'files':files},ensure_ascii=False))
    return report,files


def source_state(path=SOURCE):
    original,original_files=original_state();path=checked(path);raw=path.read_bytes()
    if sha256(raw).hexdigest()!=SOURCE_SHA256 or digest(checked(HARNESS))!=HARNESS_SHA256:
        raise ValueError('Fixed UI repair or harness changed')
    report=json.loads(raw);revision=report.get('revision',{});files=report.get('final_sources',{})
    if (report.get('schema')!='workshop-catalog-ui-repair.v1'
            or report.get('source_report_sha256')!=ORIGINAL_SHA256
            or report.get('source_package_id')!=2
            or report.get('source_package_checksum')!='8b560f0eacc42150f0635da4638fe96b140a2cc5d1dca39b14583fb48d276938'
            or report.get('candidate_created') is not True or report.get('exact_change_scope') is not True
            or report.get('owner_accepted') is not False or report.get('deployed') is not False
            or revision.get('new_package_id')!=PACKAGE_ID
            or revision.get('new_package_checksum')!=PACKAGE_CHECKSUM
            or revision.get('test_state')!='passed' or revision.get('accepted') is not False
            or set(files)!=set(original_files) or files.get('app.py')!=original_files.get('app.py')
            or any(files.get(name)!=original_files.get(name) for name in ('README.md','style.css','test_app.py'))
            or files.get('index.html')==original_files.get('index.html')
            or files.get('app.js')==original_files.get('app.js')):
        raise ValueError('Selected source is not the pinned successful UI repair chain')
    parse_sources(json.dumps({'files':files},ensure_ascii=False))
    database=checked(Path(report['isolated_database']))
    return path,report,files,database


def evidence_state():
    path=checked(ROUTES);raw=path.read_bytes()
    if sha256(raw).hexdigest()!=ROUTES_SHA256:
        raise ValueError('Fixed route evidence changed')
    data=json.loads(raw);probes=data.get('probes',[])
    expected={
        '/api/sessions?day=all&level=all':(200,200,True),
        '/api/sessions;extra?day=all&level=all':(404,200,False),
        '/health;extra':(404,200,False),
        '/;extra':(404,200,False),
    }
    if (data.get('schema')!='workshop-catalog-routes-check.v1' or data.get('status')!='failed'
            or data.get('source_report_sha256')!=ORIGINAL_SHA256 or data.get('source_unchanged') is not True
            or data.get('source_sha256',{}).get('app.py')!=ORIGINAL_APP_SHA256
            or len(probes)!=4 or {p.get('path') for p in probes}!=set(expected)):
        raise ValueError('Route report is not the fixed original-app evidence')
    for probe in probes:
        wanted=expected[probe['path']];run=probe.get('raw_run',{})
        try:
            payload=json.loads(run.get('log',''));response=payload['response']
        except (ValueError,KeyError,TypeError,json.JSONDecodeError) as exc:
            raise ValueError('Route report contains an invalid raw run') from exc
        if ((probe.get('expected_status'),probe.get('observed_status'),probe.get('passed'))!=wanted
                or run.get('exit_code')!=0 or run.get('cli_exit_code')!=0
                or run.get('cleanup_confirmed') is not True or run.get('reason') is not None
                or payload.get('schema')!='python-web-preview.v1'
                or response.get('status')!=probe.get('observed_status')
                or not isinstance(response.get('body'),str)):
            raise ValueError('Route report contains an invalid probe run')
    return path,ROUTES_SHA256


def repair_scope(base,files):
    if set(files)!=set(base):return False
    changed={name for name in base if files[name]!=base[name]}
    return changed==CHANGED_FILES


def new_output():
    for number in range(1,1000):
        candidate=PILOT/f'route-repair-{number}'
        try:candidate.mkdir(mode=0o700);return candidate
        except FileExistsError:continue
    raise ValueError('Repair directory limit reached')


class CheckedRunner(container_runner.ContainerRunner):
    def run(self,*args,**kwargs):check_idle();return super().run(*args,**kwargs)


def run(source_report=SOURCE):
    source_path,source,base,database=source_state(source_report);routes_path,routes_sha=evidence_state()
    task_id=source['task_id']
    check_idle();out=new_output();report_path=out/'report.json'
    report={'schema':'workshop-catalog-route-repair.v1','status':'running',
        'source_report':str(source_path),'source_report_sha256':SOURCE_SHA256,
        'routes_report':str(routes_path),'routes_report_sha256':routes_sha,
        'source_package_id':PACKAGE_ID,'source_package_checksum':PACKAGE_CHECKSUM,
        'task_id':task_id,'isolated_database':str(database),
        'frozen_harness_sha256':HARNESS_SHA256,
        'preserved_sha256':{name:sha256(content.encode()).hexdigest()
            for name,content in base.items() if name not in CHANGED_FILES},
        'requested_change':sorted(CHANGED_FILES),'candidate_created':False,
        'owner_accepted':False,'deployed':False}
    save(report_path,report)
    engine=create_database_engine('sqlite:///'+str(database));factory=create_session_factory(engine)
    old_package=package_runner.configuration;old_inference=local_inference.enabled_config
    fixed=container_runner.configuration()|{'harness_checksum':HARNESS_SHA256}
    package_runner.configuration=lambda:dict(fixed);local_inference.enabled_config=configuration
    try:
        with factory() as session:
            artifact,manifest=read_package(session,task_id,PACKAGE_ID)
            current={item['path']:item['content'] for item in manifest['files']}
            if artifact.checksum!=PACKAGE_CHECKSUM or current!=base:raise ValueError('Current package changed')
            created=application_revisions.create(session,reviewer_role='automated_qa',
                output_profile=REPAIR_PROFILE,task_id=task_id,package_id=PACKAGE_ID,
                package_checksum=PACKAGE_CHECKSUM,request_id=str(uuid4()),description=DESCRIPTION,
                expected_result=EXPECTED,evidence=[f'routes report sha256={routes_sha}',
                    f'UI repair report sha256={SOURCE_SHA256}',
                    f'original delivery report sha256={ORIGINAL_SHA256}',
                    f'frozen harness sha256={HARNESS_SHA256}'],auto_test=True)
            session.commit();report.update(revision_id=created['id'],inference_id=created['inference_id']);save(report_path,report)
            def provider(config):return FilewiseApplicationProvider(config,out/'model-evidence'/uuid4().hex,
                provider_factory=OllamaProvider,idle_check=check_idle)
            result=application_revisions.execute(session,created['id'],provider,CheckedRunner(harness=HARNESS));session.commit()
            report['revision']=result;report['status']=result['state']
            if result.get('new_package_id'):
                _,manifest=read_package(session,task_id,result['new_package_id'])
                files={item['path']:item['content'] for item in manifest['files']};report['final_sources']=files
                exact_scope=repair_scope(base,files);report['exact_change_scope']=exact_scope
                if result.get('test_state')=='passed' and exact_scope:
                    archive=package_runner.candidate_zip(session,result['test_run_id']);candidate=out/'workshop-catalog-candidate.zip'
                    candidate.write_bytes(archive);report.update(candidate_created=True,candidate_zip=str(candidate),
                        candidate_zip_sha256=digest(candidate))
                elif result.get('test_state')=='passed':report['status']='invalid_change_scope'
    except Exception as exc:
        report['status']='failed';report['failure']={'type':type(exc).__name__,'message':str(exc)[:1000]};raise
    finally:
        package_runner.configuration=old_package;local_inference.enabled_config=old_inference
        try:
            with factory() as session:
                report['tests']=[{'id':r.id,'package_id':r.package_id,'package_checksum':r.package_checksum,
                    'state':r.state,'profile':r.profile,'result':r.result,'report_id':r.report_id}
                    for r in session.scalars(select(PackageRun).where(PackageRun.task_id==task_id))]
                report['inferences']=[{'id':r.id,'state':r.state,'attempt_id':r.attempt_id,
                    'metrics':r.metrics,'error_code':r.error_code,'result_checksum':r.result_checksum,
                    'result_content':r.result_content} for r in session.scalars(select(LocalInference).where(
                        LocalInference.task_id==task_id))]
        finally:
            engine.dispose();report['source_unchanged']=digest(source_path)==SOURCE_SHA256
            report['routes_report_unchanged']=digest(routes_path)==routes_sha
            report['original_report_unchanged']=digest(ORIGINAL)==ORIGINAL_SHA256
            save(report_path,report)
    print(json.dumps({'report':str(report_path),'status':report['status'],'candidate_created':report['candidate_created']}))
    return 0 if report['candidate_created'] else 1


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--run',action='store_true')
    parser.add_argument('--report',type=Path,default=SOURCE,help='pinned successful workshop UI repair report')
    args=parser.parse_args();source_path,_,_,_=source_state(args.report);_,routes_sha=evidence_state()
    if not args.run:
        print(json.dumps({'model_invoked':False,'source_report':str(source_path),
            'source_package_id':PACKAGE_ID,'source_package_checksum':PACKAGE_CHECKSUM,
            'routes_report_sha256':routes_sha,
            'output_profile':REPAIR_PROFILE,'requested_change':sorted(CHANGED_FILES),
            'required_flag':'--run'}));return 0
    return run(args.report)


if __name__=='__main__':raise SystemExit(main())
