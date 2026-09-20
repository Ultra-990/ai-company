"""Owner-triggered fixed-profile execution and download of a tested candidate."""
import io
import json
from datetime import timezone
from hashlib import sha256
from uuid import uuid4
from zipfile import ZipFile, ZIP_STORED
from sqlalchemy import select, text, func
from app.models.package_run import PackageRun
from app.models.artifact import Artifact, ArtifactType
from app.models.audit import AuditEvent
from app.models.task import utc_now
from app.models.task import Task, TaskAttempt, TaskStatus
from app.models.local_inference import LocalInference
from app.services.workspace_packages import read_package, canonical_json, PackageIntegrityError
from app.services.application_profile import parse_sources
from app.services.container_runner import configuration
from app.services.execution_profiles import multifile_configuration, capabilities
from app.services.multifile_profile import PROFILE as MULTIFILE_PROFILE, require_sources
from app.services.application_layout import execution_profile
from app.services.media_packages import PROFILE as MEDIA_PROFILE, bytes_of
from app.services.media_package_runner import media_configuration

ISOLATION_KEYS={'non_root','capabilities_dropped','no_new_privileges','seccomp','no_docker_socket',
                'no_host_home','no_gpu_device','network_only_loopback','readonly_root','readonly_source'}


def summary(run):
    return {k:getattr(run,k) for k in ('id','task_id','package_id','package_checksum','container_name','state',
        'profile','result','report_id')}|{'accepted':False,'deployed':False,
            'capabilities':capabilities(run.profile.get('profile'))}


def start(session,task_id,package_id,package_checksum,request_id,runner,preview_path=None):
    from app.services.application_preview import preview_configuration, validate_path
    config_factory = preview_configuration if preview_path is not None else configuration
    config=config_factory()
    if preview_path is not None:config=config | {'request_path':validate_path(preview_path)}
    session.execute(text('BEGIN IMMEDIATE'))
    existing=session.scalar(select(PackageRun).where(PackageRun.request_id==request_id))
    if existing:
        if ((existing.task_id,existing.package_id,existing.package_checksum)!=(task_id,package_id,package_checksum)
            or existing.profile.get('request_path')!=preview_path):
            raise ValueError('UUID wskazuje inną paczkę.')
        result=summary(existing);session.rollback();return result
    artifact,payload=read_package(session,task_id,package_id)
    if artifact.checksum!=package_checksum:raise ValueError('Nieaktualna suma paczki.')
    files={entry['path']:entry['content'] for entry in payload['files']}
    layout = execution_profile(files, media=payload['schema'] == 'organization-os.workspace-media.v1')
    if layout == MEDIA_PROFILE:
        config_factory = lambda: media_configuration(preview_path is not None)
        config = config_factory()
        if preview_path is not None: config = config | {'request_path':validate_path(preview_path)}
    elif layout == MULTIFILE_PROFILE:
        require_sources(files)
        if preview_path is not None:
            from app.services.multifile_preview import certified_configuration
            config_factory=certified_configuration
        else:
            config_factory=multifile_configuration
        config=config_factory()
        if preview_path is not None:config=config | {'request_path':validate_path(preview_path)}
    else:
        parse_sources(json.dumps({'files':files}))
    if session.scalar(select(PackageRun.id).where(PackageRun.state.in_(['running','uncertain'])).limit(1)):
        raise ValueError('Runner jest zajęty lub poprzedni kontener wymaga uzgodnienia stanu.')
    previous=list(session.scalars(select(PackageRun).where(PackageRun.package_id==package_id)))
    same_mode=[r for r in previous if ('request_path' in r.profile)==(preview_path is not None)]
    if len(same_mode)>=(120 if preview_path is not None else 3):
        raise ValueError('Limit 120 żądań podglądu tej wersji.' if preview_path is not None else 'Limit trzech uruchomień tej wersji; popraw paczkę po analizie raportów.')
    run=PackageRun(request_id=request_id,task_id=task_id,package_id=package_id,package_checksum=package_checksum,
                   container_name='aic-package-'+uuid4().hex,state='running',profile=config)
    session.add(run);session.flush()
    session.add(AuditEvent(event_type='package_run',operation='start',allowed=True,decision='running',
                          reason=f'owner; run={run.id}; package={package_id}; sha256={package_checksum}; network=none'))
    session.commit();run_id=run.id
    try:result=runner.run(files,config,run.container_name)
    except Exception as exc:
        result={'reason':'runner_'+type(exc).__name__,'cleanup_confirmed':False,'log':'','exit_code':None}
    session.execute(text('BEGIN IMMEDIATE'));session.expire_all();run=session.get(PackageRun,run_id)
    if run.state!='running':session.rollback();raise ValueError('Wykonanie zmieniło stan. Nie nadpisano raportu.')
    try:
        _,fresh=read_package(session,task_id,package_id)
        fresh_config=config_factory()
        if preview_path is not None:fresh_config=fresh_config | {'request_path':preview_path}
        if fresh!=payload or fresh_config!=config:raise ValueError('Profile/source changed')
    except Exception:result=dict(result,reason='source_or_policy_changed')
    try:
        harness=json.loads(result.get('log',''))
        passed=(result.get('reason') is None and result.get('exit_code')==0 and result.get('cli_exit_code')==0 and
                harness.get('schema')==({MULTIFILE_PROFILE:'python-web-multifile-test.v1',MEDIA_PROFILE:'python-web-media-test.v1'}.get(config['profile'],'python-web-test.v1')) and harness.get('tests_ok') is True and
                harness.get('http_ok') is True and harness.get('source_not_exposed') is True and
                set(harness.get('isolation',{}))==ISOLATION_KEYS and all(v is True for v in harness['isolation'].values()) and
                harness.get('errors')==[])
        if config['profile'] == MEDIA_PROFILE:
            passed = passed and harness.get('assets_ok') is True
        if preview_path is not None:
            multifile_preview=config['profile'] in ('python-web-multifile-preview-v1','python-web-media-preview-v1')
            media_preview=config['profile']=='python-web-media-preview-v1'
            reply=harness.get('response',{})
            passed=(result.get('reason') is None and result.get('exit_code')==0 and result.get('cli_exit_code')==0
                and harness.get('schema')==('python-web-media-preview.v1' if media_preview else 'python-web-multifile-preview.v1' if multifile_preview else 'python-web-preview.v1') and isinstance(reply.get('body'),str)
                and len(reply['body'].encode('utf-8'))<=(18000 if media_preview and preview_path=='/' else 12000) and type(reply.get('status')) is int
                and 200<=reply['status']<=599 and isinstance(reply.get('content_type'),str))
            if multifile_preview:
                passed=passed and set(harness.get('isolation',{}))==ISOLATION_KEYS and all(v is True for v in harness['isolation'].values()) and harness.get('errors')==[]
    except (ValueError,TypeError,AttributeError):passed=False
    run.state=(('previewed' if preview_path is not None else 'passed') if passed else 'failed') if result.get('cleanup_confirmed') is True else 'uncertain'
    run.result=result;run.finished_at=utc_now()
    content=canonical_json({'schema':'package-run-report.v1','run_id':run_id,'task_id':task_id,'package_id':package_id,
        'source_checksum':package_checksum,'profile':config,'state':run.state,'result':result,
        'limitations':['Kontener współdzieli jądro hosta; nie jest granicą dla celowo wrogiego kodu.',
                       'Testy modelu i smoke HTTP nie potwierdzają wszystkich wymagań klienta.',
                       'Nie wykonano odbioru wizualnego, wdrożenia ani akceptacji klienta.']})
    report=Artifact(task_id=task_id,project_id=artifact.project_id,plan_id=artifact.plan_id,
        artifact_type=ArtifactType.TEST_RESULT,name=('organization-os.application-preview.v1' if preview_path is not None else 'organization-os.container-test.v1'),content=content,
        checksum=sha256(content.encode()).hexdigest(),created_by='isolated-runner',description=('Pojedyncze żądanie podglądu HTTP; nie test funkcjonalny ani odbiór.' if preview_path is not None else 'Rzeczywisty wynik izolowanego profilu Python web; nie odbiór klienta.'))
    session.add(report);session.flush();run.report_id=report.id
    session.add(AuditEvent(event_type='package_run',operation='finish',allowed=True,decision=run.state,
                          reason=f'run={run.id}; report={report.id}; automatic_acceptance=false'))
    session.commit();return summary(run)


def reconcile(session,run_id,runner):
    run=session.get(PackageRun,run_id)
    if not run:raise LookupError('Brak wykonania.')
    if run.state not in {'running','uncertain'}:return summary(run)
    started=run.created_at.replace(tzinfo=timezone.utc) if run.created_at.tzinfo is None else run.created_at
    if (utc_now()-started).total_seconds()<90:raise ValueError('Odczekaj 90 sekund od rozpoczęcia przed odzyskaniem slotu.')
    if not runner.cleanup(run.container_name):raise ValueError('Nie potwierdzono usunięcia własnego kontenera.')
    run.state='interrupted';run.finished_at=utc_now()
    run.result=dict(run.result or {},cleanup_confirmed=True,recovered=True)
    session.add(AuditEvent(event_type='package_run',operation='reconcile',allowed=True,decision='interrupted',reason=f'owner; run={run_id}'))
    return summary(run)


def validated_candidate(session,run_id):
    """Read-only validation shared by downloads and delivery readiness."""
    run=session.get(PackageRun,run_id)
    if not run:raise LookupError('Brak wykonania.')
    if run.state!='passed':raise ValueError('Paczka kandydata wymaga zaliczonego wykonania tej wersji.')
    artifact,payload=read_package(session,run.task_id,run.package_id)
    report=session.get(Artifact,run.report_id)
    if artifact.checksum!=run.package_checksum or not report or sha256((report.content or '').encode()).hexdigest()!=report.checksum:
        raise ValueError('Naruszona integralność źródeł lub raportu.')
    saved=json.loads(report.content)
    if (not isinstance(saved,dict) or report.task_id!=run.task_id
        or report.artifact_type!=ArtifactType.TEST_RESULT
        or saved.get('schema')!='package-run-report.v1' or saved.get('profile')!=run.profile
        or saved.get('run_id')!=run.id or saved.get('package_id')!=run.package_id
        or saved.get('task_id')!=run.task_id or saved.get('source_checksum')!=run.package_checksum
        or saved.get('state')!='passed'):
        raise ValueError('Raport nie dotyczy tej wersji.')
    return run,payload,report


def candidate_zip(session,run_id,release=None,handoff=None):
    run,payload,report=validated_candidate(session,run_id)
    multifile=run.profile.get('profile') in (MULTIFILE_PROFILE, MEDIA_PROFILE)
    manifest={'schema':'delivery-candidate.v1','task_id':run.task_id,'package_id':run.package_id,
        'source_checksum':run.package_checksum,'test_run_id':run.id,'test_report_checksum':report.checksum,
        'accepted':False,'deployed':False,'profile':run.profile,
        'files':[{k:v for k,v in f.items() if k!='content'} for f in payload['files']]}
    if release:
        manifest.update(schema='owner-approved-delivery.v1',accepted=True,owner_review=release,client_accepted=False)
    output=io.BytesIO()
    with ZipFile(output,'w',compression=ZIP_STORED) as archive:
        for f in payload['files']:archive.writestr('sources/'+f['path'],bytes_of(f))
        archive.writestr('delivery.json',canonical_json(manifest))
        archive.writestr('test-report.json',report.content)
        if handoff:
            for name,content in handoff['guides'].items():
                archive.writestr(name,content)
            archive.writestr('handoff.json',canonical_json({
                k:handoff[k] for k in ('schema','source_checksum','test_report_checksum',
                                      'release_checksum','document_checksums')}))
        archive.writestr('READ-ME-FIRST.md',('# Wydanie odebrane przez właściciela\n\n' if release else '# Kandydat do odbioru\n\n')+'Źródła w sources/. '
            'UWAGA: nie otwieraj samego index.html z dysku. To aplikacja serwerowa, nie samodzielny plik HTML. '
            + ('Klient: przeczytaj CLIENT-START-HERE.md (EN) lub CLIENT-START-HERE.pl.md (PL). ' if handoff else
               'W panelu /os/build otwórz aplikację w izolacji i odbierz tę wersję paczki przed przygotowaniem wydania. ' if multifile else
               'W panelu właściciela /os/build wybierz „Otwórz aplikację w izolacji”. ') +
            ('Python 3.10, bez zależności. Polecenia: python app.py; python -m unittest discover -s tests -t . -p "test_*.py" -v. ' if multifile else
             'Python 3.10, bez zależności. Polecenia: python app.py; python -m unittest test_app -v. ') +
            'Uruchamiaj tylko w zatwierdzonym środowisku, nie w katalogu panelu firmy. '
            'Adres aplikacji: http://127.0.0.1:8080. Testy profilu zaliczono dla wersji w delivery.json. '
            'Nie jest to dowód pełnego odbioru, audytu bezpieczeństwa ani wdrożenia. '
            'Przed przekazaniem klientowi sprawdź jego kryteria i README aplikacji.\n')
    return output.getvalue()


def delivery_readiness(session,run_id):
    """Explain existing release gates without accepting, executing or publishing."""
    run=session.get(PackageRun,run_id)
    if not run:raise LookupError('Brak wykonania.')
    checks=[]
    result={'run_id':run.id,'task_id':run.task_id,'package_id':run.package_id,
            'source_checksum':run.package_checksum,'ready':False,'release_id':None,
            'checks':checks,'client_accepted':False,'deployed':False,
            'note':'To kontrola wydania właściciela, nie status publikacji ani odbioru klienta.'}
    try:
        validated_candidate(session,run_id)
    except (ValueError,PackageIntegrityError,LookupError,KeyError,TypeError):
        checks.append({'key':'tests','passed':False,'message':'Brak zaliczonych testów tej paczki lub niespójne źródła i raport. Sprawdź raport wykonania.'})
        return result
    checks.append({'key':'tests','passed':True,'message':'Źródła i raport zaliczonych testów dotyczą tej samej wersji.'})
    if run.profile.get('profile') in (MULTIFILE_PROFILE, MEDIA_PROFILE):
        from app.services.package_acceptance import readiness
        return readiness(session,run_id,result)
    from app.services.acceptance_gate import require_current
    try:
        acceptance_proof=require_current(session,run.task_id,run.package_id,run.package_checksum)
    except ValueError as exc:
        checks.append({'key':'acceptance_plan','passed':False,'message':str(exc)})
        return result
    if acceptance_proof:
        result['acceptance_proof']=acceptance_proof
        checks.append({'key':'acceptance_plan','passed':True,
            'message':f'Plan HTTP #{acceptance_proof["plan_id"]}: {acceptance_proof["case_count"]} przykładów potwierdzonych dla tej wersji. Nie jest to pełny odbiór biznesowy.'})
    try:
        attempt=approved_result(session,run)
    except (ValueError,PackageIntegrityError,LookupError) as exc:
        checks.append({'key':'owner_review','passed':False,'message':str(exc)})
        return result
    checks.append({'key':'owner_review','passed':True,'message':'Właściciel odebrał dokładnie te źródła; test jest najnowszy i zgodny z aktualnym profilem.'})
    saved=session.scalar(select(Artifact).where(Artifact.task_id==run.task_id,Artifact.name==f'organization-os.release.{run_id}'))
    if saved:
        try:
            release_payload(saved,run,attempt,acceptance_proof)
            valid=True
        except (ValueError,TypeError,AttributeError):valid=False
        if not valid:
            checks.append({'key':'release','passed':False,'message':'Zapis wydania jest niespójny. Wstrzymaj przekazanie i sprawdź dane.'})
            return result
        result['release_id']=saved.id
    result['ready']=True
    checks.append({'key':'release','passed':bool(saved),'message':'Wydanie przygotowane — można je pobrać.' if saved else 'Można przygotować wydanie. Nie zostało jeszcze zapisane ani wysłane klientowi.'})
    return result


def approved_result(session,run):
    """Acceptance must be of the exact generated source, not any completed task."""
    if run.profile.get('profile') in (MULTIFILE_PROFILE, MEDIA_PROFILE):
        raise ValueError('Profil wielomodułowy wymaga odbioru konkretnej paczki, nie starego odbioru próby Qwen.')
    latest_run=next((r.id for r in session.scalars(select(PackageRun).where(PackageRun.package_id==run.package_id).order_by(PackageRun.id.desc())) if 'request_path' not in r.profile),None)
    if latest_run!=run.id or configuration()!=run.profile:
        raise ValueError('Wydanie wymaga najnowszego zaliczonego wykonania w aktualnym profilu testów.')
    task=session.get(Task,run.task_id)
    attempt=session.scalar(select(TaskAttempt).where(TaskAttempt.task_id==run.task_id).order_by(TaskAttempt.id.desc()).limit(1))
    if not task or task.status!=TaskStatus.COMPLETED or not attempt or attempt.status!='completed' or attempt.verification_status!='accepted' or not attempt.verified_at:
        raise ValueError('Najpierw odbierz wynik tego zadania w panelu właściciela.')
    if not attempt.result_content or sha256(attempt.result_content.encode()).hexdigest()!=attempt.result_checksum:
        raise ValueError('Naruszona integralność odebranego wyniku.')
    generated=session.scalar(select(LocalInference).where(LocalInference.attempt_id==attempt.id))
    if not generated or (generated.metrics or {}).get('package_id')!=run.package_id:
        raise ValueError('Odbiór nie dotyczy źródeł tej paczki Qwen.')
    _,payload=read_package(session,run.task_id,run.package_id)
    if parse_sources(attempt.result_content)!={f['path']:f['content'] for f in payload['files']}:
        raise ValueError('Odebrany wynik różni się od paczki.')
    return attempt


def release(session,run_id):
    run=session.get(PackageRun,run_id)
    if not run:raise LookupError('Brak wykonania.')
    if run.profile.get('profile') in (MULTIFILE_PROFILE, MEDIA_PROFILE):
        from app.services.package_acceptance import release as package_release
        return package_release(session,run_id)
    candidate_zip(session,run_id)  # validates source and test report before approval
    from app.services.acceptance_gate import require_current
    acceptance_proof=require_current(session,run.task_id,run.package_id,run.package_checksum)
    attempt=approved_result(session,run)
    name=f'organization-os.release.{run_id}'
    saved=session.scalar(select(Artifact).where(Artifact.task_id==run.task_id,Artifact.name==name))
    if saved:
        release_payload(saved,run,attempt,acceptance_proof)
        return {'release_id':saved.id,'run_id':run_id,'owner_accepted':True,'client_accepted':False,'deployed':False}
    task=session.get(Task,run.task_id)
    payload={'run_id':run_id,'source_checksum':run.package_checksum,'attempt_id':attempt.id,
             'result_checksum':attempt.result_checksum,'owner_accepted':True,'client_accepted':False,'deployed':False,
             **({'acceptance_proof':acceptance_proof} if acceptance_proof else {})}
    content=canonical_json(payload)
    artifact=Artifact(task_id=task.id,project_id=task.project_id,plan_id=task.plan_id,task_attempt_id=attempt.id,
        artifact_type=ArtifactType.REPORT,name=name,content=content,checksum=sha256(content.encode()).hexdigest(),
        created_by='owner',description='Wydanie źródeł odebrane przez właściciela; bez wdrożenia i odbioru klienta.')
    session.add(artifact);session.flush()
    session.add(AuditEvent(event_type='package_release',operation='prepare',allowed=True,decision='owner_accepted',
                          reason=f'owner; run={run_id}; release={artifact.id}; attempt={attempt.id}'))
    return {'release_id':artifact.id,**payload}


def release_payload(artifact,run,attempt,acceptance_proof=None):
    """Validate the same saved owner decision for readiness, replay and download."""
    if sha256((artifact.content or '').encode()).hexdigest()!=artifact.checksum:raise ValueError('Naruszona integralność wydania.')
    try:payload=json.loads(artifact.content)
    except (ValueError,TypeError) as exc:raise ValueError('Nieprawidłowy zapis wydania.') from exc
    if (not isinstance(payload,dict) or payload.get('run_id')!=run.id
        or payload.get('owner_accepted') is not True
        or artifact.task_id!=run.task_id or artifact.artifact_type!=ArtifactType.REPORT
        or artifact.task_attempt_id!=attempt.id
        or payload.get('attempt_id')!=attempt.id or payload.get('result_checksum')!=attempt.result_checksum
        or payload.get('source_checksum')!=run.package_checksum
        or payload.get('acceptance_proof')!=acceptance_proof):
        raise ValueError('Wydanie nie odpowiada bieżącej odebranej wersji.')
    return payload


def validated_release(session,run_id):
    """One read-only gate for the ZIP and its client-facing documents."""
    run,package,report=validated_candidate(session,run_id)
    if run.profile.get('profile') in (MULTIFILE_PROFILE, MEDIA_PROFILE):
        from app.services.package_acceptance import validated_release as package_release
        return package_release(session,run_id)
    from app.services.acceptance_gate import require_current
    acceptance_proof=require_current(session,run.task_id,run.package_id,run.package_checksum)
    attempt=approved_result(session,run)
    artifact=session.scalar(select(Artifact).where(Artifact.task_id==run.task_id,Artifact.name==f'organization-os.release.{run_id}'))
    if not artifact:raise ValueError('Najpierw przygotuj wydanie po odbiorze.')
    payload=release_payload(artifact,run,attempt,acceptance_proof)
    return run,package,report,artifact,payload


def released_zip(session,run_id):
    from app.services.delivery_handoff import documents
    run,package,report,artifact,payload=validated_release(session,run_id)
    handoff=documents(run,package,report,artifact,payload.get('acceptance_proof'))
    return candidate_zip(session,run_id,release=payload,handoff=handoff)
