"""Request one two-file UI repair bound to the failed PLAN ZAJĘĆ browser report."""
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
SOURCE=PILOT/'report.json'
BROWSER=PILOT/'browser'/'report.json'
HARNESS=PILOT/'independent-harness.py'
SOURCE_SHA256='80c6bb4d63dfd3fabedc8a2d6a7b0b4808cd61fbddbfa91c6a269c3704aee1e5'
HARNESS_SHA256='29904434ad2a8174ab02a0afc5d38f779217068f87aa43a2e4f3ca22fc54b8fd'
PACKAGE_ID=2
PACKAGE_CHECKSUM='8b560f0eacc42150f0635da4638fe96b140a2cc5d1dca39b14583fb48d276938'
BROWSER_SHA256='e0f24a77d63cf1e84facee6b0047928802d015fc29921755cda100a8bcd03887'
CHANGED_FILES={'index.html','app.js'}
DESCRIPTION=('Zmień tylko index.html i app.js. Użyj względnych style.css i app.js bez początkowego /, '
    'aby ładowały się także przez file://. Pod HTTP od razu pobierz all/all z istniejącego API '
    'i pokaż sześć rekordów w kolejności katalogu oraz niepusty status. Renderuj dni i poziomy '
    'po polsku, zachowując wartości API. Zachowaj filtry, empty state, bezpieczny DOM bez innerHTML, '
    'menu, Escape/fokus i FAQ; file:// ma pokazać polecenie python app.py, wyłączyć przycisk i nie '
    'wykonywać fetch. Usuń arbitralny rok 2024. Nie zmieniaj pozostałych czterech plików ani danych API.')
EXPECTED=('changes zawiera dokładnie pełne index.html i app.js. HTTP: initial all/all sześć rekordów '
    'i status, polskie etykiety, działające filtry. file://: zasoby lokalne, ostrzeżenie, disabled, '
    'bez fetch. app.py, test_app.py, style.css, README.md i frozen harness bajtowo niezmienione.')


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
    report=json.loads(raw);quality=report.get('quality',{});files=report.get('final_sources',{})
    if (report.get('schema')!='workshop-catalog-delivery.v1' or report.get('candidate_created') is not True
            or quality.get('final_package_id')!=PACKAGE_ID or quality.get('package_id')!=PACKAGE_ID
            or quality.get('package_checksum')!=PACKAGE_CHECKSUM or quality.get('state')!='passed'):
        raise ValueError('Original workshop delivery is not the expected tested source')
    parse_sources(json.dumps({'files':files},ensure_ascii=False))
    database=checked(Path(report['isolated_database']))
    return report,files,database


def validate_browser_data(data):
    checks=data.get('checks',[]) if isinstance(data,dict) else []
    failed=[row.get('name') for row in checks if row.get('passed') is not True]
    if (data.get('schema')!='workshop-catalog-browser.v1'
            or data.get('source_report_sha256')!=SOURCE_SHA256
            or data.get('status')!='failed' or len(checks)!=15
            or failed!=['file-mode-safe']
            or not all(any(row.get('name')==name and row.get('passed') is True for row in checks)
                       for name in ('mobile-menu-open','mobile-escape','mobile-menu-links-in-viewport',
                                    'filter-tuesday-beginner','filter-saturday-advanced',
                                    'filter-tuesday-intermediate'))):
        raise ValueError('Browser report is not the preserved 14/15 workshop failure')


def evidence_state():
    browser=checked(BROWSER)
    if digest(browser)!=BROWSER_SHA256:
        raise ValueError('Browser report changed')
    data=json.loads(browser.read_text(encoding='utf-8'));validate_browser_data(data)
    return BROWSER_SHA256


def repair_scope(base,files):
    if set(files)!=set(base):return False
    changed={name for name in base if files[name]!=base[name]}
    return changed==CHANGED_FILES


def new_output():
    for number in range(1,1000):
        candidate=PILOT/f'repair-{number}'
        try:candidate.mkdir(mode=0o700);return candidate
        except FileExistsError:continue
    raise ValueError('Repair directory limit reached')


class CheckedRunner(container_runner.ContainerRunner):
    def run(self,*args,**kwargs):check_idle();return super().run(*args,**kwargs)


def run():
    source,base,database=source_state();browser_sha=evidence_state()
    task_id=source['task_id']
    check_idle();out=new_output();report_path=out/'report.json'
    report={'schema':'workshop-catalog-ui-repair.v1','status':'running',
        'source_report':str(SOURCE),'source_report_sha256':SOURCE_SHA256,
        'browser_report':str(BROWSER),'browser_report_sha256':browser_sha,
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
                expected_result=EXPECTED,evidence=[f'browser report sha256={browser_sha}',
                    f'original delivery report sha256={SOURCE_SHA256}',
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
            engine.dispose();report['source_unchanged']=digest(SOURCE)==SOURCE_SHA256
            report['browser_report_unchanged']=digest(BROWSER)==browser_sha
            save(report_path,report)
    print(json.dumps({'report':str(report_path),'status':report['status'],'candidate_created':report['candidate_created']}))
    return 0 if report['candidate_created'] else 1


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--run',action='store_true')
    args=parser.parse_args();source_state();evidence_state()
    if not args.run:
        print(json.dumps({'model_invoked':False,'source_report':str(SOURCE),
            'source_package_id':PACKAGE_ID,'source_package_checksum':PACKAGE_CHECKSUM,
            'browser_report_sha256':BROWSER_SHA256,
            'output_profile':REPAIR_PROFILE,'requested_change':sorted(CHANGED_FILES),
            'required_flag':'--run'}));return 0
    return run()


if __name__=='__main__':raise SystemExit(main())
