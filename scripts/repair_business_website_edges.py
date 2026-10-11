"""Request one app.py-only repair bound to a supplemental ROWEROWNIA edge report."""
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

PILOT=Path('/home/marcin/ai-company-workspaces/business-website-pilot-fkf_d3w0')
SOURCE=PILOT/'revision-1'/'report.json'
HARNESS=PILOT/'independent-harness.py'
SOURCE_SHA256='dd4486524418b8cb6406b2029059c1be85aa4237bcd5c743034ffe140e2c3b22'
HARNESS_SHA256='e5844bcf7c678b24ba3e75572eeed10ec982a1dc9c5b0aa96bdc04354a5c2c5b'
PACKAGE_ID=17
PACKAGE_CHECKSUM='4652ea35ae3a7391291456611a24072428f7ce252b86cbc54a297c54a4131b0d'
DESCRIPTION=('Dodatkowa kontrola API wykazała, że jawny dodatkowy pusty parametr, np. coupon=, '
    'nie jest odrzucany, ponieważ parser zapytania go gubi. Popraw wyłącznie app.py: endpoint '
    '/api/estimate ma wymagać dokładnie po jednym parametrze service, bikes i express, odrzucać '
    'każde dodatkowe pole także z pustą wartością oraz odrzucać powtórzone wartości parametrów. '
    'Zachowaj ceny, poprawne odpowiedzi, routing i pozostały kontrakt. Nie zmieniaj testów ani frontendu.')
EXPECTED=('Zwróć changes zawierające wyłącznie kompletny app.py. Dodatkowe puste pole i '
    'powtórzone parametry zwracają HTTP 400; poprawne trzy pojedyncze parametry nadal zwracają '
    'dotychczasową wycenę. Zamrożony harness i wszystkie istniejące testy pozostają niezmienione.')


def digest(path):return sha256(path.read_bytes()).hexdigest()


def save(path,value):
    temporary=path.with_suffix('.tmp');temporary.write_text(
        json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8');temporary.replace(path)


def checked(path):
    if any(item.is_symlink() for item in (path,*path.parents)):raise ValueError('Symlink evidence is not allowed')
    resolved=path.resolve(strict=True)
    if not resolved.is_relative_to(PILOT.resolve(strict=True)):raise ValueError('Evidence is outside pilot')
    return resolved


def source_state():
    raw=checked(SOURCE).read_bytes()
    if sha256(raw).hexdigest()!=SOURCE_SHA256 or digest(checked(HARNESS))!=HARNESS_SHA256:
        raise ValueError('Fixed revision or harness changed')
    report=json.loads(raw);revision=report.get('revision',{});files=report.get('final_sources',{})
    if (revision.get('new_package_id')!=PACKAGE_ID or revision.get('new_package_checksum')!=PACKAGE_CHECKSUM
            or revision.get('test_state')!='passed' or report.get('status')!='awaiting_review'):
        raise ValueError('Revision 1 is not the expected tested source')
    parse_sources(json.dumps({'files':files},ensure_ascii=False))
    database=checked(Path(report['isolated_database']))
    return report,files,database


def edge_state(path):
    path=checked(path);raw=path.read_bytes();data=json.loads(raw)
    if (path.parent.name.startswith('edge-check-') is False
            or data.get('schema')!='business-website-edge-check.v1'
            or data.get('source_report_sha256')!=SOURCE_SHA256
            or data.get('gate_passed') is not False
            or not any(p.get('name')=='extra-empty-rejected' and p.get('passed') is False
                       and p.get('observed_status')==200 for p in data.get('probes',[]))):
        raise ValueError('Edge report does not bind the observed empty-extra-parameter failure')
    return path,sha256(raw).hexdigest(),data


def new_output():
    for number in range(1,1000):
        candidate=PILOT/f'repair-{number}'
        try:candidate.mkdir(mode=0o700);return candidate
        except FileExistsError:continue
    raise ValueError('Repair directory limit reached')


class CheckedRunner(container_runner.ContainerRunner):
    def run(self,*args,**kwargs):check_idle();return super().run(*args,**kwargs)


def run(edge_report):
    source,base,database=source_state();edge_path,edge_sha,edge=edge_state(edge_report)
    task_id=source['revision']['task_id']
    check_idle();out=new_output();report_path=out/'report.json'
    report={'schema':'business-website-edge-repair.v1','status':'running',
        'source_report':str(SOURCE),'source_report_sha256':SOURCE_SHA256,
        'edge_report':str(edge_path),'edge_report_sha256':edge_sha,
        'source_package_id':PACKAGE_ID,'source_package_checksum':PACKAGE_CHECKSUM,
        'task_id':task_id,'isolated_database':str(database),
        'frozen_harness_sha256':HARNESS_SHA256,
        'preserved_sha256':{name:sha256(content.encode()).hexdigest()
            for name,content in base.items() if name!='app.py'},
        'requested_change':['app.py'],'candidate_created':False,
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
                expected_result=EXPECTED,evidence=[f'edge report sha256={edge_sha}',
                    f'revision-1 report sha256={SOURCE_SHA256}'],auto_test=True)
            session.commit();report.update(revision_id=created['id'],inference_id=created['inference_id']);save(report_path,report)
            def provider(config):return FilewiseApplicationProvider(config,out/'model-evidence'/uuid4().hex,
                provider_factory=OllamaProvider,idle_check=check_idle)
            result=application_revisions.execute(session,created['id'],provider,CheckedRunner(harness=HARNESS));session.commit()
            report['revision']=result;report['status']=result['state']
            if result.get('new_package_id'):
                _,manifest=read_package(session,task_id,result['new_package_id'])
                files={item['path']:item['content'] for item in manifest['files']};report['final_sources']=files
                preserved=all(files.get(name)==content for name,content in base.items() if name!='app.py')
                only_app=preserved and files.get('app.py')!=base['app.py'] and set(files)==set(base)
                report['only_app_changed']=only_app
                if result.get('test_state')=='passed' and only_app:
                    archive=package_runner.candidate_zip(session,result['test_run_id']);candidate=out/'business-website-candidate.zip'
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
            engine.dispose();report['source_unchanged']=digest(SOURCE)==SOURCE_SHA256
            report['edge_report_unchanged']=digest(edge_path)==edge_sha;save(report_path,report)
    print(json.dumps({'report':str(report_path),'status':report['status'],'candidate_created':report['candidate_created']}))
    return 0 if report['candidate_created'] else 1


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--run',action='store_true')
    parser.add_argument('--edge-report',type=Path,help='immutable report.json from check_business_website_edges.py --run')
    args=parser.parse_args();source_state()
    if not args.run:
        print(json.dumps({'model_invoked':False,'source_report':str(SOURCE),
            'source_package_id':PACKAGE_ID,'source_package_checksum':PACKAGE_CHECKSUM,
            'output_profile':REPAIR_PROFILE,'requested_change':['app.py'],
            'required_flags':['--run','--edge-report PATH']}));return 0
    if args.edge_report is None:parser.error('--edge-report is required with --run')
    return run(args.edge_report)


if __name__=='__main__':raise SystemExit(main())
