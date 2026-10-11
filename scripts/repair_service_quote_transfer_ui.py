"""Request one two-file UI repair bound to the failed CREMA browser report."""
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

PILOT=Path('/home/marcin/ai-company-workspaces/service-quote-transfer-q4ylytju')
SOURCE=PILOT/'revision-1'/'report.json'
BROWSER=PILOT/'revision-1'/'browser'/'report.json'
ORIGINAL=PILOT/'report.json'
HARNESS=PILOT/'independent-harness.py'
SOURCE_SHA256='e083d95f6a60718f879348275f78cadfc3ef796af44ee64f94654159b34d541d'
HARNESS_SHA256='13e64d0ab231b8e3bb83ec0d421daf0dc35c4a54267f78295f99c130876e10c1'
PACKAGE_ID=14
PACKAGE_CHECKSUM='85e8c47d56adde16b4853ffb272506c9adb63ed5fa98456b7d172a99c5053370'
BROWSER_SHA256='507159007b12507e2e7cb78108c8d4e87519ec909c419a3a22a3c9661cc0cce3'
ORIGINAL_SHA256='c6b5d8ab2fc0eaa5ffac0185ce948c954990d4aa8d9582feb52bc6668b6c2122'
CHANGED_FILES={'index.html','style.css'}
DESCRIPTION=('Popraw wyłącznie index.html i style.css po zachowanej kontroli przeglądarkowej. '
    'Na mobile zamknięty #site-nav ma być naprawdę ukryty, a otwarty ma być widoczny obok nagłówka '
    'w aktualnym viewportcie. Obecne nav ul ma position:absolute i top:100% bez pozycjonowanego '
    'przodka, więc lista kotwiczy się względem viewportu i wypada poza widoczny ekran. Zachowaj '
    'istniejący app.js bajt w bajt: nadal przełącza klasę open na liście, obsługuje aria-expanded, '
    'Escape i fokus. Dobierz poprawną strukturę HTML/CSS współpracującą z tą logiką. W sekcji kontaktu '
    'usuń konkretne wartości pozornego telefonu, e-maila i adresu pocztowego, które poprzednia rewizja '
    'zostawiła mimo feedbacku; pozostaw wyłącznie jasno oznaczony fikcyjny tekst demonstracyjny. '
    'Zmień widoczną polską etykietę planu restore z mylącego „Restauracja (Restore)” na '
    '„Regeneracja” albo „Naprawa kompleksowa”, zachowując value=restore i cenę 235 PLN. Usuń '
    'arbitralny rok 2024 ze stopki albo zastąp go bezczasową, prawdziwą informacją o fikcyjnym demo. '
    'Nie zmieniaj API, kalkulatora, treści cen, app.js, app.py, test_app.py ani README.md.')
EXPECTED=('Zwróć changes zawierające dokładnie kompletne index.html i style.css. Zamknięte menu '
    'mobilne jest ukryte; po otwarciu linki są wyrenderowane w granicach viewportu obok nagłówka. '
    'Kontakt nie zawiera konkretnego telefonu, e-maila ani adresu; etykieta restore jest naturalna '
    'po polsku i nie zmienia value ani ceny. Cztery pozostałe pliki i frozen '
    'harness pozostają identyczne; dotychczasowe trzy świeże wyceny browser/API pozostają bez zmian.')


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


def validate_browser_data(data):
    checks=data.get('checks',[]) if isinstance(data,dict) else []
    failed=[row.get('name') for row in checks if row.get('passed') is not True]
    if (data.get('schema')!='service-quote-transfer-browser.v1'
            or data.get('source_report_sha256')!=SOURCE_SHA256
            or data.get('status')!='failed' or len(checks)!=13
            or failed!=['mobile-menu-closed']
            or not all(any(row.get('name')==name and row.get('passed') is True for row in checks)
                       for name in ('mobile-menu-open','mobile-escape','file-mode-safe',
                                    'quote-check-2-False','quote-restore-1-True','quote-restore-6-True'))):
        raise ValueError('Browser report is not the preserved 12/13 CREMA failure')


def evidence_state():
    browser=checked(BROWSER);original=checked(ORIGINAL)
    if digest(browser)!=BROWSER_SHA256 or digest(original)!=ORIGINAL_SHA256:
        raise ValueError('Browser report or original brief changed')
    data=json.loads(browser.read_text(encoding='utf-8'));validate_browser_data(data)
    return BROWSER_SHA256,ORIGINAL_SHA256


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
    source,base,database=source_state();browser_sha,original_sha=evidence_state()
    task_id=source['revision']['task_id']
    check_idle();out=new_output();report_path=out/'report.json'
    report={'schema':'service-quote-transfer-ui-repair.v1','status':'running',
        'source_report':str(SOURCE),'source_report_sha256':SOURCE_SHA256,
        'browser_report':str(BROWSER),'browser_report_sha256':browser_sha,
        'original_brief':str(ORIGINAL),'original_brief_sha256':original_sha,
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
                    f'original brief sha256={original_sha}',f'revision-1 report sha256={SOURCE_SHA256}',
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
                    archive=package_runner.candidate_zip(session,result['test_run_id']);candidate=out/'service-quote-transfer-candidate.zip'
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
            report['original_brief_unchanged']=digest(ORIGINAL)==original_sha;save(report_path,report)
    print(json.dumps({'report':str(report_path),'status':report['status'],'candidate_created':report['candidate_created']}))
    return 0 if report['candidate_created'] else 1


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--run',action='store_true')
    args=parser.parse_args();source_state();evidence_state()
    if not args.run:
        print(json.dumps({'model_invoked':False,'source_report':str(SOURCE),
            'source_package_id':PACKAGE_ID,'source_package_checksum':PACKAGE_CHECKSUM,
            'browser_report_sha256':BROWSER_SHA256,'original_brief_sha256':ORIGINAL_SHA256,
            'output_profile':REPAIR_PROFILE,'requested_change':sorted(CHANGED_FILES),
            'required_flag':'--run'}));return 0
    return run()


if __name__=='__main__':raise SystemExit(main())
