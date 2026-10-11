"""Refine the app.py route repair after verified urlparse params evidence."""
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
from scripts import check_workshop_catalog_routes as route_checks

PILOT=Path('/home/marcin/ai-company-workspaces/workshop-catalog-r59rfvqy')
ORIGINAL=PILOT/'report.json'
SOURCE=PILOT/'route-repair-2'/'report.json'
ROUTES=PILOT/'routes-check-4'/'report.json'
HARNESS=PILOT/'independent-harness.py'
ORIGINAL_SHA256='80c6bb4d63dfd3fabedc8a2d6a7b0b4808cd61fbddbfa91c6a269c3704aee1e5'
UI_SOURCE_SHA256='7d28033d294b96281ae2d22b2c41f64d226a000301c3b7392455ca6a397d1a74'
SOURCE_SHA256='27e607b4fae6da9c5868489a464ecc8ca12aed70ab1634b560de7714216d44a7'
ROUTES_SHA256='95b62355921be5ba6462fd091cd16b52e988c7e464fc4543828190ef7b1be354'
HARNESS_SHA256='29904434ad2a8174ab02a0afc5d38f779217068f87aa43a2e4f3ca22fc54b8fd'
PACKAGE_ID=18
PACKAGE_CHECKSUM='b71af69a5f009c07df7151506010196a6b3b7aa1697e52d9658f9f984dd3645f'
ORIGINAL_APP_SHA256='aa5986dbf8495fb6b2a223fc2b07aa4393e127c4e16aecfc993715bf4c336e27'
SOURCE_APP_SHA256='538417ae1e84b1ed10e8f57b7f6641cf3c8d7b2c7392bab97e6ae791f4984374'
CHANGED_FILES={'app.py'}
DESCRIPTION=("urlparse('/health;extra') => path='/health', params='extra', więc `';' in parsed.path` "
    "jest nieskuteczne. URL /api/sessions;extra?day=all&level=all, /health;extra, /;extra, "
    "/health; =>404. Zachowaj trasy, day/level, katalog i JSON.")
EXPECTED="Tylko pełny app.py; 4×404; all/all 200/6. Pozostałe 5 plików+harness bez zmian."

# Immutable round 1 pins remain available for audit and replay validation.
ROUND1={
    'round':1,'source':SOURCE,'source_sha256':SOURCE_SHA256,'source_app_sha256':SOURCE_APP_SHA256,
    'source_package_id':PACKAGE_ID,'source_package_checksum':PACKAGE_CHECKSUM,
    'routes':ROUTES,'routes_sha256':ROUTES_SHA256,'description':DESCRIPTION,'expected':EXPECTED,
}
ROUND2={
    'round':2,
    'source':PILOT/'route-refinement-1'/'report.json',
    'source_sha256':'3857aca7fba6598c0ba9ea0daa49f0d549f2c0f95244999f237a01fa73a64e8a',
    'source_app_sha256':'f22d584d3959c95bd75688c8ddfc40fd581e0eb422c08ca5114f023c072e1355',
    'source_package_id':25,
    'source_package_checksum':'b178c7960aa16934c91a2a98825f6895bcf1b5fa036d2e928ad52a6357f77fdb',
    'routes':PILOT/'routes-check-5'/'report.json',
    'routes_sha256':'c23d8fa3007dba4f5e850d40cfbc1831eff6a973fe543f27c1a87351f17acdbd',
    'description':("Tylko app.py. urlparse('/health;') => path='/health', params='' gubi pusty średnik. "
        "Oceniaj pełną nierozciętą ścieżkę. 5 probes: oczekiwane statusy, /health; =>404. "
        "Zachowaj day/level, katalog, JSON i trasy."),
    'expected':"Pełny app.py; control 200/6, 4 średniki 404; 5 plików+harness bez zmian.",
}
ROUND3={**ROUND2,
    'round':3,
    'description':("Tylko app.py. Poprzednia odpowiedź=base. urlparse gubi pusty ';' w /health;, "
        "urlsplit zachowuje go w ścieżce. Wybierz parser/dopasowanie pełnej nierozciętej ścieżki. "
        "5 probes: oczekiwane statusy. Zachowaj day/level, katalog, JSON."),
    'expected':"Zmieniony app.py; control 200/6, 4 średniki 404; 5 plików+harness bez zmian.",
    'failed_report':PILOT/'route-refinement-2'/'report.json',
    'failed_report_sha256':'bee2701ac4a40e01a9a0a4a4a77d28d7022f6f34823f90f86aae209cddb5fba7',
    'raw_response_sha256':'dc63c8d22b948b6aa39b39312db518766da76e0f886e5dbb35d262eaa5011e07',
    'raw_response_checksum':'dd246e0450e412a472c1a7ea89df97e359f335cb83eab199b29ad3136a0048bd',
}


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


def source_state(path=None,plan=ROUND1):
    path=plan['source'] if path is None else path
    _,original_files=original_state();path=checked(path);raw=path.read_bytes()
    if sha256(raw).hexdigest()!=plan['source_sha256'] or digest(checked(HARNESS))!=HARNESS_SHA256:
        raise ValueError('Fixed failed-behavior route repair or harness changed')
    report=json.loads(raw);revision=report.get('revision',{});files=report.get('final_sources',{})
    checked_path,checked_sha,checked_report,checked_files=route_checks.load_source(path)
    expected_schema='workshop-catalog-route-repair.v1' if plan['round']==1 else 'workshop-catalog-route-refinement.v1'
    if (checked_path!=path or checked_sha!=plan['source_sha256'] or checked_report!=report or checked_files!=files
            or report.get('schema')!=expected_schema
            or report.get('candidate_created') is not True or report.get('exact_change_scope') is not True
            or report.get('owner_accepted') is not False or report.get('deployed') is not False
            or revision.get('new_package_id')!=plan['source_package_id']
            or revision.get('new_package_checksum')!=plan['source_package_checksum']
            or revision.get('test_state')!='passed' or revision.get('accepted') is not False
            or set(files)!=set(original_files) or files.get('app.py')==original_files.get('app.py')
            or sha256(files.get('app.py','').encode()).hexdigest()!=plan['source_app_sha256']
            or any(files.get(name)!=original_files.get(name) for name in ('README.md','style.css','test_app.py'))
            or files.get('index.html')==original_files.get('index.html')
            or files.get('app.js')==original_files.get('app.js')):
        raise ValueError('Selected source is not the pinned failed-behavior route repair chain')
    parse_sources(json.dumps({'files':files},ensure_ascii=False))
    database=checked(Path(report['isolated_database']))
    return path,report,files,database


def evidence_state(plan=ROUND1):
    path=checked(plan['routes']);raw=path.read_bytes()
    if sha256(raw).hexdigest()!=plan['routes_sha256']:
        raise ValueError('Fixed route evidence changed')
    data=json.loads(raw);probes=data.get('probes',[])
    expected={
        '/api/sessions?day=all&level=all':(200,200,True),
        '/api/sessions;extra?day=all&level=all':(404,200,False),
        '/health;extra':(404,200,False),
        '/;extra':(404,200,False),
    }
    if plan['round']>=2:
        expected={path:(wanted,wanted,True) for path,(wanted,_,_) in expected.items()}
        expected['/health;']=(404,200,False)
    if (data.get('schema')!='workshop-catalog-routes-check.v1' or data.get('status')!='failed'
            or data.get('source_report_sha256')!=plan['source_sha256'] or data.get('source_unchanged') is not True
            or data.get('source_sha256',{}).get('app.py')!=plan['source_app_sha256']
            or len(probes)!=len(expected) or {p.get('path') for p in probes}!=set(expected)):
        raise ValueError('Route report is not the fixed failed-refinement evidence')
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
    return path,plan['routes_sha256']


def failed_refinement_state(plan):
    if plan['round']<3:return None
    path=checked(plan['failed_report']);raw=path.read_bytes()
    if sha256(raw).hexdigest()!=plan['failed_report_sha256']:
        raise ValueError('Pinned failed refinement report changed')
    data=json.loads(raw);revision=data.get('revision',{});rows=data.get('inferences',[])
    row=next((item for item in rows if item.get('id')==revision.get('inference_id')),None)
    response_path=path.parent/'model-evidence'/'8641bc64be8d4d6ca92919efa6676e80'/'repair-response.json'
    response_raw=response_path.read_bytes();response=json.loads(response_raw)
    try:changes=json.loads(response['content'])['changes']
    except (KeyError,TypeError,ValueError,json.JSONDecodeError) as exc:
        raise ValueError('Failed refinement raw response is invalid') from exc
    _,_,_,base=route_checks.load_source(plan['source'])
    if (data.get('schema')!='workshop-catalog-route-refinement.v1' or data.get('refinement_round')!=2
            or data.get('status')!='failed' or data.get('candidate_created') is not False
            or revision.get('state')!='failed' or revision.get('error_code')!='invalid_file_repair'
            or revision.get('new_package_id') is not None or revision.get('test_run_id') is not None
            or not row or row.get('state')!='failed' or row.get('error_code')!='invalid_file_repair'
            or row.get('result_checksum') is not None
            or row.get('metrics',{}).get('raw_response_checksum')!=plan['raw_response_checksum']
            or sha256(response_raw).hexdigest()!=plan['raw_response_sha256']
            or set(changes)!={'app.py'} or changes['app.py']!=base['app.py']):
        raise ValueError('Failed refinement is not the pinned unchanged app.py response')
    return path,plan['failed_report_sha256']


def repair_scope(base,files):
    if set(files)!=set(base):return False
    changed={name for name in base if files[name]!=base[name]}
    return changed==CHANGED_FILES


def new_output():
    for number in range(1,1000):
        candidate=PILOT/f'route-refinement-{number}'
        try:candidate.mkdir(mode=0o700);return candidate
        except FileExistsError:continue
    raise ValueError('Repair directory limit reached')


class CheckedRunner(container_runner.ContainerRunner):
    def run(self,*args,**kwargs):check_idle();return super().run(*args,**kwargs)


def run(source_report=None,plan=ROUND1):
    source_path,source,base,database=source_state(source_report,plan);routes_path,routes_sha=evidence_state(plan)
    failed=failed_refinement_state(plan)
    task_id=source['task_id']
    check_idle();out=new_output();report_path=out/'report.json'
    report={'schema':'workshop-catalog-route-refinement.v1','status':'running',
        'refinement_round':plan['round'],
        'source_report':str(source_path),'source_report_sha256':plan['source_sha256'],
        'routes_report':str(routes_path),'routes_report_sha256':routes_sha,
        'source_package_id':plan['source_package_id'],'source_package_checksum':plan['source_package_checksum'],
        'task_id':task_id,'isolated_database':str(database),
        'frozen_harness_sha256':HARNESS_SHA256,
        'preserved_sha256':{name:sha256(content.encode()).hexdigest()
            for name,content in base.items() if name not in CHANGED_FILES},
        'requested_change':sorted(CHANGED_FILES),'candidate_created':False,
        'owner_accepted':False,'deployed':False}
    if failed:report.update(failed_refinement_report=str(failed[0]),failed_refinement_report_sha256=failed[1])
    save(report_path,report)
    engine=create_database_engine('sqlite:///'+str(database));factory=create_session_factory(engine)
    old_package=package_runner.configuration;old_inference=local_inference.enabled_config
    fixed=container_runner.configuration()|{'harness_checksum':HARNESS_SHA256}
    package_runner.configuration=lambda:dict(fixed);local_inference.enabled_config=configuration
    try:
        with factory() as session:
            artifact,manifest=read_package(session,task_id,plan['source_package_id'])
            current={item['path']:item['content'] for item in manifest['files']}
            if artifact.checksum!=plan['source_package_checksum'] or current!=base:raise ValueError('Current package changed')
            created=application_revisions.create(session,reviewer_role='automated_qa',
                output_profile=REPAIR_PROFILE,task_id=task_id,package_id=plan['source_package_id'],
                package_checksum=plan['source_package_checksum'],request_id=str(uuid4()),description=plan['description'],
                expected_result=plan['expected'],evidence=[f'routes report sha256={routes_sha}',
                    f'prior refinement report sha256={plan["source_sha256"]}',
                    *([f'failed refinement report sha256={failed[1]}'] if failed else []),
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
            engine.dispose();report['source_unchanged']=digest(source_path)==plan['source_sha256']
            report['routes_report_unchanged']=digest(routes_path)==routes_sha
            report['original_report_unchanged']=digest(ORIGINAL)==ORIGINAL_SHA256
            save(report_path,report)
    print(json.dumps({'report':str(report_path),'status':report['status'],'candidate_created':report['candidate_created']}))
    return 0 if report['candidate_created'] else 1


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--run',action='store_true')
    group=parser.add_mutually_exclusive_group()
    group.add_argument('--round2',action='store_true',help='use the pinned five-probe refinement plan')
    group.add_argument('--round3',action='store_true',help='retry round 2 after the pinned unchanged response')
    parser.add_argument('--report',type=Path,help='must equal the selected pinned source report')
    args=parser.parse_args();plan=ROUND3 if args.round3 else (ROUND2 if args.round2 else ROUND1)
    source_path,_,_,_=source_state(args.report,plan);_,routes_sha=evidence_state(plan);failed=failed_refinement_state(plan)
    if not args.run:
        print(json.dumps({'model_invoked':False,'source_report':str(source_path),
            'refinement_round':plan['round'],
            'source_package_id':plan['source_package_id'],'source_package_checksum':plan['source_package_checksum'],
            'routes_report_sha256':routes_sha,
            **({'failed_refinement_report_sha256':failed[1]} if failed else {}),
            'output_profile':REPAIR_PROFILE,'requested_change':sorted(CHANGED_FILES),
            'required_flag':'--run'}));return 0
    return run(args.report,plan)


if __name__=='__main__':raise SystemExit(main())
