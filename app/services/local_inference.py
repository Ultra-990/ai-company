"""Single real text-generation slot; versioned output requires owner acceptance."""
import json
from datetime import timezone
from uuid import uuid4
from sqlalchemy import func, select, text
from app.core.config import load_settings
from app.models.local_inference import LocalInference
from app.models.task import Task, TaskAttempt, TaskStatus, utc_now
from app.models.artifact import Artifact, ArtifactType
from app.models.audit import AuditEvent
from app.services.agent_packets import export_prompt, digest, read_packet
from app.services.local_ollama import configuration, ModelFailure
from app.services.application_profile import (messages_for, parse_sources, SOURCE_SCHEMA,
    REPAIR_PROFILE, REPAIR_SCHEMA, repair_base, assemble_repair)
from app.services.workspace_packages import create_package
from app.services import upwork_scope
from app.services import multifile_generation


def enabled_config():
    if load_settings().safety.emergency_stop:
        raise ValueError('Emergency Stop: lokalny model jest wstrzymany.')
    return configuration()


def summary(run):
    data = {key:getattr(run,key) for key in (
        'id','task_id','packet_id','packet_checksum','state','model','model_digest',
        'limits','result_content','result_checksum','metrics','error_code','attempt_id',
        'created_at','started_at','finished_at',
    )}
    for key in ('created_at','started_at','finished_at'):
        if data[key] is not None:
            value=data[key];data[key]=value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)
    return data | {'model_request_started':run.started_at is not None,
                   'task_completed':False,'tools_enabled':False}


def audit(session, run, operation):
    session.add(AuditEvent(event_type='local_inference',operation=operation,
        decision=run.state,allowed=True,
        reason=f'owner; run={run.id}; task={run.task_id}; model={run.model}; tools=none; automatic_acceptance=false'))


def execution_config(session,task_id,packet_id,profile,config):
    if profile=='text' and read_packet(session,task_id,packet_id)['packet'].get('result_contract')==upwork_scope.CONTRACT:
        return config | {'num_predict':min(1536,config['num_predict']),
                         'scope_decoder':'json-schema.v1'}
    if profile!='text' and read_packet(session,task_id,packet_id)['packet']['revision']['previous_attempt_id'] is not None:
        # Full old sources + requested correction must fit without truncation.
        # Bounded code-revision profile, not a caller-supplied model parameter.
        return config | {'num_ctx':min(32768,config['num_ctx']+16384)}
    return config


def enqueue(session, task_id, packet_id, packet_checksum, request_id, output_profile='text'):
    existing=session.scalar(select(LocalInference).where(LocalInference.request_id==request_id))
    if existing:
        if existing.limits.get('output_profile','text')!=output_profile:raise ValueError('Ta instrukcja ma już inny profil wykonania.')
        if (existing.task_id,existing.packet_id,existing.packet_checksum)!=(task_id,packet_id,packet_checksum):
            raise ValueError('Ten identyfikator wskazuje inną instrukcję.')
        return summary(existing)
    existing=session.scalar(select(LocalInference).where(LocalInference.packet_id==packet_id))
    if existing:
        if existing.limits.get('output_profile','text')!=output_profile:raise ValueError('Ta instrukcja ma już inny profil wykonania.')
        if existing.task_id!=task_id or existing.packet_checksum!=packet_checksum:
            raise ValueError('Niezgodne powiązanie instrukcji.')
        return summary(existing)
    config=enabled_config()
    prompt=export_prompt(session,task_id,packet_id)
    if output_profile!='text' and read_packet(session,task_id,packet_id)['packet']['role']!='builder':
        raise ValueError('Pliki aplikacji generuje etap wykonawcy, po przygotowaniu zakresu.')
    if (output_profile==multifile_generation.PROFILE
            and read_packet(session,task_id,packet_id)['packet']['revision']['previous_attempt_id'] is not None):
        raise ValueError('Poprawki modułowe wymagają oddzielnej kontroli zmian i zachowania testów. Nie regeneruj całej wersji jako poprawki.')
    if prompt['packet_checksum']!=packet_checksum:raise ValueError('Nieaktualna wersja instrukcji.')
    config=execution_config(session,task_id,packet_id,output_profile,config)
    if output_profile==REPAIR_PROFILE:
        repair_base(read_packet(session,task_id,packet_id)['packet'])
    # Upper bound based on UTF-8 bytes, intentionally conservative. No hidden
    # truncation of task context, predecessor evidence or policy instructions.
    byte_count=sum(len(m['content'].encode('utf-8')) for m in messages_for(prompt['messages'],output_profile))
    if byte_count>config['num_ctx']-config['num_predict']-1024:
        raise ValueError('Instrukcja przekracza bezpieczny kontekst. Podziel zadanie na mniejszy zakres.')
    if session.scalar(select(func.count()).select_from(LocalInference).where(LocalInference.state.in_(['queued','running','uncertain'])))>=50:
        raise ValueError('Limit 50 pozycji oczekujących lub wykonywanych.')
    if output_profile!='text':config=config|{'output_profile':output_profile}
    run=LocalInference(request_id=request_id,task_id=task_id,packet_id=packet_id,packet_checksum=packet_checksum,
                       state='queued',model=config['model'],model_digest=config['digest'],limits=config)
    session.add(run);session.flush();audit(session,run,'enqueue')
    return summary(run)


def fail(session,run,code,state='failed'):
    run.state=state;run.error_code=code;run.finished_at=utc_now();audit(session,run,'finish')


def execute(session,run_id,provider_factory):
    config=enabled_config()
    session.execute(text('BEGIN IMMEDIATE'));session.expire_all()
    run=session.get(LocalInference,run_id)
    if not run:session.rollback();raise LookupError('Nie znaleziono wykonania.')
    if run.state!='queued':
        result=summary(run);session.rollback();return result
    from app.services.media_generation import busy as media_busy
    if media_busy(session):
        session.rollback();raise ValueError('Generator grafiki zajmuje slot GPU lub wymaga sprawdzenia wyniku.')
    if session.scalar(select(LocalInference.id).where(LocalInference.state.in_(['running','uncertain'])).limit(1)):
        session.rollback();raise ValueError('Jeden model jest już wykonywany. Odśwież stan; nie uruchomiono drugiego.')
    profile=run.limits.get('output_profile','text')
    try:config=execution_config(session,run.task_id,run.packet_id,profile,config)
    except (LookupError,ValueError):
        fail(session,run,'instruction_not_current','stale');session.commit();return summary(run)
    if {k:v for k,v in run.limits.items() if k!='output_profile'}!=config:
        fail(session,run,'configuration_changed','stale');session.commit();return summary(run)
    try:
        prompt=export_prompt(session,run.task_id,run.packet_id)
        if prompt['packet_checksum']!=run.packet_checksum:raise ValueError('checksum')
        scope_contract=read_packet(session,run.task_id,run.packet_id)['packet'].get('result_contract')==upwork_scope.CONTRACT
        base=repair_base(read_packet(session,run.task_id,run.packet_id)['packet']) if profile==REPAIR_PROFILE else None
    except (LookupError,ValueError):
        fail(session,run,'instruction_not_current','stale');session.commit();return summary(run)
    execution_token=str(uuid4())
    run.metrics=dict(run.metrics or {})|{'execution_token':execution_token}
    run.state='running';run.started_at=utc_now();audit(session,run,'reserve');session.commit()
    error=None;output=None;files=None;assembly=None;raw_content=None;repair_validation=None
    try:
        provider_config=config
        if scope_contract:
            provider_config=config|{'format':upwork_scope.ScopeResult.model_json_schema()}
        elif profile==REPAIR_PROFILE:
            provider_config=config|{'format':REPAIR_SCHEMA}
        elif profile==multifile_generation.PROFILE:
            provider_config=config|{'format':multifile_generation.SOURCE_SCHEMA}
        elif profile!='text':
            provider_config=config|{'format':SOURCE_SCHEMA}
        output=provider_factory(provider_config).complete(messages_for(prompt['messages'],profile))
        content=output['content']
        if (not isinstance(content,str) or not content.strip() or len(content)>32000 or '\x00' in content
            or output['model']!=run.model or output['digest']!=run.model_digest or output['done_reason']!='stop'):
            raise ValueError('invalid output')
        content.encode('utf-8')
        if scope_contract:
            try:upwork_scope.validate_result(content)
            except ValueError:
                error='scope_contract_invalid'
                raise
        if profile==REPAIR_PROFILE:
            raw_content=content
            try:content,files,changed=assemble_repair(raw_content,base)
            except ValueError as exc:
                error='invalid_file_repair';repair_validation=str(exc)[:200]
                raise
            assembly={'schema':REPAIR_PROFILE,'raw_response_checksum':digest(raw_content),
                      'base_files_checksum':digest(json.dumps(base,ensure_ascii=False,sort_keys=True)),
                      'changed_files':changed,'preserved_files':sorted(set(base)-set(changed)),
                      'tests_checksum':digest(base['test_app.py'])}
        elif profile==multifile_generation.PROFILE:files=multifile_generation.parse_sources(content)
        elif profile!='text':files=parse_sources(content)
    except ModelFailure as exc:error=exc.code
    except TimeoutError:error='model_timeout'
    except Exception:error=error or 'model_failed_or_invalid_output'
    # The model never holds a database write lock. Check the full context again
    # before handing a response to an actual TaskAttempt.
    session.execute(text('BEGIN IMMEDIATE'));session.expire_all();run=session.get(LocalInference,run_id)
    if not run or run.state!='running' or (run.metrics or {}).get('execution_token')!=execution_token:
        session.rollback();raise ValueError('Stan wykonania zmienił się; odpowiedź nie została przekazana do zadania.')
    try:
        current=export_prompt(session,run.task_id,run.packet_id)
        if current['packet_checksum']!=run.packet_checksum:raise ValueError('changed')
        if execution_config(session,run.task_id,run.packet_id,profile,enabled_config())!=config:raise ValueError('configuration changed')
    except (ValueError,LookupError):
        finished=output is not None or error in {'truncated_output','empty_output','model_changed','model_inventory','model_http_error'}
        fail(session,run,'instruction_or_policy_changed','stale' if finished else 'uncertain')
    else:
        if error:
            if error=='invalid_file_repair' and raw_content is not None:
                raw_artifact=Artifact(task_id=run.task_id,artifact_type=ArtifactType.REPORT,
                    name=f'local-inference.raw-repair.{run.id}',content=raw_content,checksum=digest(raw_content),
                    created_by='local-ollama',description='Odrzucona poprawka: nie utworzono wersji źródeł ani próby zadania.')
                session.add(raw_artifact);session.flush()
                run.metrics=dict(run.metrics or {})|{'raw_artifact_id':raw_artifact.id,
                    'raw_response_checksum':digest(raw_content),'repair_validation':repair_validation,
                    **{k:output.get(k) for k in ('elapsed_seconds','eval_count','prompt_eval_count','done_reason')}}
            # Closing the HTTP transport is not proof that a remote daemon has
            # stopped computing. Hold the slot after ambiguous transport errors.
            finished=output is not None or error in {'truncated_output','empty_output','model_changed','model_inventory','model_http_error'}
            fail(session,run,error,'failed' if finished else 'uncertain')
        else:
            task=session.get(Task,run.task_id);task.transition_to(TaskStatus.IN_PROGRESS)
            result_checksum=digest(content);now=utc_now()
            attempt=TaskAttempt(task_id=task.id,worker_id='local-ollama',status='awaiting_review',
                result_content=content,result_checksum=result_checksum,started_at=run.started_at,
                finished_at=now,verification_status='pending')
            session.add(attempt);session.flush()
            run.state='awaiting_review';run.result_content=content;run.result_checksum=result_checksum
            run.attempt_id=attempt.id;run.finished_at=now
            run.metrics=dict(run.metrics or {})|{k:output.get(k) for k in ('elapsed_seconds','eval_count','prompt_eval_count','done_reason')}
            if assembly is not None:
                raw_artifact=Artifact(task_id=task.id,project_id=task.project_id,plan_id=task.plan_id,
                    task_attempt_id=attempt.id,artifact_type=ArtifactType.REPORT,
                    name=f'local-inference.raw-repair.{run.id}',content=raw_content,
                    checksum=digest(raw_content),created_by='local-ollama',
                    description='Surowa poprawka Qwen. Wynik zadania złożono z tej zmiany i niezmienionych plików bazowych.')
                session.add(raw_artifact);session.flush()
                run.metrics=run.metrics|{'assembly':assembly|{'raw_artifact_id':raw_artifact.id}}
            if files is not None:
                purpose=('Źródła złożone z poprawki Qwen i zachowanych plików bazowych; surowa odpowiedź w historii inferencji.'
                         if assembly is not None else 'Źródła wygenerowane przez lokalnego Qwen; wymagają uruchomienia testów i odbioru.')
                package=create_package(session,task.id,files,purpose,commit=False)
                package.created_by='local-ollama'
                package.task_attempt_id=attempt.id
                run.metrics=run.metrics|{'package_id':package.id,'package_checksum':package.checksum,'output_profile':profile}
            receipt=json.dumps({'schema':'local-inference.v1','run_id':run.id,'packet_id':run.packet_id,
                'packet_checksum':run.packet_checksum,'attempt_id':attempt.id,'result_checksum':result_checksum,
                'model':run.model,'model_digest':run.model_digest,'metrics':run.metrics,
                'model_invoked':True,'tools':[],'acceptance':'pending'},sort_keys=True,ensure_ascii=True)
            session.add(Artifact(task_id=task.id,project_id=task.project_id,plan_id=task.plan_id,
                task_attempt_id=attempt.id,artifact_type=ArtifactType.REPORT,
                name=f'local-inference.receipt.{run.id}',content=receipt,checksum=digest(receipt),
                created_by='local-ollama',description=('Potwierdzenie złożenia wersji z poprawki Qwen; odnośnik do surowej odpowiedzi w metrics. Bez odbioru.'
                    if assembly is not None else 'Rzeczywista odpowiedź lokalnego modelu. Bez wykonania kodu i automatycznego odbioru.')))
            audit(session,run,'finish')
    session.commit();return summary(run)


def cancel(session,run_id):
    run=session.get(LocalInference,run_id)
    if not run:raise LookupError('Nie znaleziono wykonania.')
    if run.state=='cancelled':return summary(run)
    if run.state!='queued':raise ValueError('Anulować można tylko oczekujący wpis. Trwający transport ma własny deadline.')
    run.state='cancelled';run.finished_at=utc_now();audit(session,run,'cancel');return summary(run)


def requeue(session,run_id,request_id):
    """Explicit retry after API verified empty Ollama; history is retained."""
    run=session.get(LocalInference,run_id)
    if not run:raise LookupError('Nie znaleziono wykonania.')
    history=(run.metrics or {}).get('retry_history',[])
    if any(h['request_id']==request_id for h in history):return summary(run)
    if run.state=='running':
        started=run.started_at
        if started is None:raise ValueError('Brak czasu rozpoczęcia; wymagany audyt wpisu.')
        if started.tzinfo is None:started=started.replace(tzinfo=timezone.utc)
        if (utc_now()-started).total_seconds()<=run.limits['timeout_seconds']+15:
            raise ValueError('Nie upłynął jeszcze limit trwającego przebiegu.')
    elif run.state not in {'failed','uncertain'}:
        raise ValueError('Ponawiać można tylko nieudany lub niepewny przebieg.')
    if len(history)>=2:raise ValueError('Limit trzech prób tej instrukcji. Wymagany przegląd zakresu.')
    if session.scalar(select(LocalInference.id).where(LocalInference.state=='running',LocalInference.id!=run_id).limit(1)):
        raise ValueError('Inny przebieg nadal trwa. Nie ponowiono zadania.')
    config=enabled_config();prompt=export_prompt(session,run.task_id,run.packet_id)
    if prompt['packet_checksum']!=run.packet_checksum:raise ValueError('Instrukcja zmieniła się.')
    profile=run.limits.get('output_profile','text')
    config=execution_config(session,run.task_id,run.packet_id,profile,config)
    if sum(len(m['content'].encode()) for m in messages_for(prompt['messages'],profile))>config['num_ctx']-config['num_predict']-1024:
        raise ValueError('Instrukcja przekracza aktualny limit kontekstu.')
    snapshot={k:getattr(run,k).isoformat() if getattr(run,k) is not None else None for k in ('started_at','finished_at')}
    snapshot.update(request_id=request_id,state=run.state,error_code=run.error_code,limits=run.limits)
    run.metrics=dict(run.metrics or {})|{'retry_history':history+[snapshot]}
    run.limits=config if profile=='text' else config|{'output_profile':profile}
    run.model=config['model'];run.model_digest=config['digest']
    run.state='queued';run.error_code=None;run.started_at=None;run.finished_at=None
    audit(session,run,'explicit_retry');return summary(run)
