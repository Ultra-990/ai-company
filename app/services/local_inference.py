"""Single real text-generation slot; versioned output requires owner acceptance."""
import json
from datetime import timezone
from hashlib import sha256
from pathlib import Path
import stat
from uuid import uuid4
from sqlalchemy import func, select, text
from app.core.config import load_settings
from app.models.local_inference import LocalInference
from app.models.task import Task, TaskAttempt, TaskStatus, utc_now
from app.models.artifact import Artifact, ArtifactType
from app.models.audit import AuditEvent
from app.services.agent_packets import export_prompt, digest, read_packet
from app.services.local_ollama import configuration, ensure_idle, ModelFailure
from app.services.application_profile import (messages_for, parse_sources, SOURCE_SCHEMA,
    PROFILE, REPAIR_PROFILE, REPAIR_SCHEMA, repair_base, assemble_repair)
from app.services.filewise_application_provider import (ASSEMBLED_BYTES, FILES as FILEWISE_FILES,
    MAX_CALLS, MAX_CALL_NUM_PREDICT, TOTAL_DEADLINE_SECONDS, FilewiseApplicationProvider,
    validate_first_filewise_call)
from app.services.workspace_packages import create_package
from app.services import upwork_scope
from app.services import multifile_generation
from app.services.model_routing import route_for_packet, executable

FILEWISE_EVIDENCE_ROOT=Path('/home/marcin/ai-company-workspaces/local-inference-evidence')


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
    packet = read_packet(session, task_id, packet_id)['packet']
    route = route_for_packet(packet)
    if not executable(route):
        # Experimental adapters are recorded for evaluation but cannot enter
        # the Ollama runtime until an independent promotion changes the route.
        raise ValueError('Wybrany adapter nie ma jeszcze zgody na wykonanie produkcyjne.')
    config = config | {'route_key': route.service_key}
    if (profile==PROFILE
            and config.get('application_generation_strategy','single-call-v1')=='filewise-v1'):
        config=config|{'filewise_total_timeout_seconds':TOTAL_DEADLINE_SECONDS,
            'filewise_max_calls':MAX_CALLS,'filewise_max_call_num_predict':MAX_CALL_NUM_PREDICT,
            'filewise_assembled_bytes':ASSEMBLED_BYTES}
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
    prepared_messages=messages_for(prompt['messages'],output_profile)
    if (output_profile==PROFILE
            and config.get('application_generation_strategy')=='filewise-v1'):
        validate_first_filewise_call(config,prepared_messages)
    else:
        byte_count=sum(len(m['content'].encode('utf-8')) for m in prepared_messages)
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


def _bounded_regular_file(path):
    metadata=path.stat(follow_symlinks=False)
    if not stat.S_ISREG(metadata.st_mode) or metadata.st_size>1024*1024:
        raise ValueError('invalid_filewise_evidence')
    with path.open('rb') as stream:raw=stream.read(1024*1024+1)
    if len(raw)!=metadata.st_size or len(raw)>1024*1024:
        raise ValueError('invalid_filewise_evidence')
    return raw


def _filewise_bundle(directory,expected_manifest=None):
    directory=Path(directory)
    root=FILEWISE_EVIDENCE_ROOT.absolute()
    if (directory.is_symlink() or not directory.is_dir()
            or directory.absolute().parent!=root or not root.is_dir()
            or any(item.is_symlink() for item in (root,*root.parents))):
        raise ValueError('invalid_filewise_evidence')
    for ancestor in (directory,*directory.parents):
        if ancestor.is_symlink():raise ValueError('invalid_filewise_evidence')
        if ancestor==root:break
    manifest_path=directory/'manifest.json'
    manifest_raw=_bounded_regular_file(manifest_path)
    manifest=json.loads(manifest_raw.decode('utf-8'))
    if expected_manifest is not None and manifest!=expected_manifest:
        raise ValueError('invalid_filewise_evidence')
    if (not isinstance(manifest,dict) or manifest.get('schema')!='filewise-application-provider.v1'
            or not isinstance(manifest.get('calls'),list) or len(manifest['calls'])>len(FILEWISE_FILES)):
        raise ValueError('invalid_filewise_evidence')
    allowed={'manifest.json'}
    for number,name in enumerate(FILEWISE_FILES,1):
        allowed|={f'{number:02d}-{name}.request.json',f'{number:02d}-{name}.response.json'}
    files=[];raw_by_name={};total=0
    for path in sorted(directory.iterdir(),key=lambda item:item.name):
        if path.is_symlink() or path.name not in allowed:
            raise ValueError('invalid_filewise_evidence')
        raw=_bounded_regular_file(path);total+=len(raw)
        if total>8*1024*1024:raise ValueError('invalid_filewise_evidence')
        raw_by_name[path.name]=raw
        files.append({'name':path.name,'sha256':sha256(raw).hexdigest(),'content':raw.decode('utf-8')})
    if raw_by_name.get('manifest.json')!=manifest_raw or manifest.get('evidence_bytes')!=total:
        raise ValueError('invalid_filewise_evidence')
    sources={};attempted=0;rejected=0;declared={'manifest.json'}
    for index,call in enumerate(manifest['calls'],1):
        if not isinstance(call,dict) or call.get('number')!=index or call.get('filename')!=FILEWISE_FILES[index-1]:
            raise ValueError('invalid_filewise_evidence')
        request_name=f'{index:02d}-{call["filename"]}.request.json'
        declared.add(request_name)
        request=raw_by_name.get(request_name)
        if (request is None or call.get('request_sha256')!=sha256(request).hexdigest()
                or call.get('request_bytes')!=len(request)
                or type(call.get('model_attempted')) is not bool
                or call.get('status') not in {'prepared','rejected_before_model','model_attempted','completed'}):
            raise ValueError('invalid_filewise_evidence')
        if ((call['status'] in {'model_attempted','completed'})!=call['model_attempted']
                or (index<len(manifest['calls']) and call['status']!='completed')):
            raise ValueError('invalid_filewise_evidence')
        if call.get('model_attempted') is True:attempted+=1
        if call.get('status')=='rejected_before_model':rejected+=1
        response_name=f'{index:02d}-{call["filename"]}.response.json'
        response=raw_by_name.get(response_name)
        if response is None:
            if any(key in call for key in ('response_sha256','response_bytes','source_sha256')):
                raise ValueError('invalid_filewise_evidence')
            continue
        declared.add(response_name)
        if (call.get('response_sha256')!=sha256(response).hexdigest()
                or call.get('response_bytes')!=len(response) or not call['model_attempted']):
            raise ValueError('invalid_filewise_evidence')
        try:
            envelope=json.loads(response.decode('utf-8'))
            source=json.loads(envelope['content'])['content']
        except (KeyError,TypeError,ValueError,UnicodeError):
            source=None
        if 'source_sha256' in call:
            if (call['status']!='completed' or not isinstance(source,str)
                    or call['source_sha256']!=digest(source)):
                raise ValueError('invalid_filewise_evidence')
            sources[call['filename']]=source
        elif call['status']=='completed':raise ValueError('invalid_filewise_evidence')
    file_records=manifest.get('files')
    expected_records=[{'path':name,'sha256':digest(value),'bytes':len(value.encode('utf-8'))}
        for name,value in sources.items()]
    if (set(raw_by_name)!=declared or manifest.get('attempted_model_calls')!=attempted
            or manifest.get('rejected_before_model')!=rejected
            or file_records!=expected_records):
        raise ValueError('invalid_filewise_evidence')
    if manifest.get('assembled') is True:
        combined=json.dumps({'files':sources},ensure_ascii=False)
        if (tuple(sources)!=FILEWISE_FILES or manifest.get('status')!='assembled'
                or manifest.get('assembled_sha256')!=digest(combined)):
            raise ValueError('invalid_filewise_evidence')
    elif 'assembled_sha256' in manifest:
        raise ValueError('invalid_filewise_evidence')
    content=json.dumps({'schema':'local-inference-filewise-evidence.v1','files':files},
                       ensure_ascii=False,sort_keys=True,separators=(',',':'))
    if len(content.encode('utf-8'))>16*1024*1024:raise ValueError('invalid_filewise_evidence')
    return content,manifest


def _attach_filewise_evidence(session,run,bundle,manifest,attempt=None):
    if bundle is None:return
    task=session.get(Task,run.task_id)
    artifact=Artifact(task_id=task.id,project_id=task.project_id,plan_id=task.plan_id,
        task_attempt_id=attempt.id if attempt is not None else None,
        artifact_type=ArtifactType.REPORT,name=f'local-inference.filewise-evidence.{run.id}',
        content=bundle,checksum=digest(bundle),created_by='local-ollama',
        description='Surowe, ograniczone dowody etapów generowania plikowego; bez odbioru produktu.')
    session.add(artifact);session.flush()
    run.metrics=dict(run.metrics or {})|{'filewise':{
        'schema':'filewise-application-provider.v1','artifact_id':artifact.id,
        'artifact_checksum':artifact.checksum,
        'attempted_model_calls':manifest.get('attempted_model_calls'),
        'rejected_before_model':manifest.get('rejected_before_model'),
        'assembled':manifest.get('assembled') is True}}


def _filewise_finished(manifest,error):
    calls=manifest.get('calls',[]) if isinstance(manifest,dict) else []
    if error in {'truncated_output','empty_output','model_changed','model_inventory','model_http_error'}:
        return True
    if not calls:return True
    last=calls[-1]
    return last.get('status')=='rejected_before_model' or 'response_sha256' in last


def _execution_deadline(limits,profile):
    if profile==PROFILE and limits.get('application_generation_strategy')=='filewise-v1':
        return limits.get('filewise_total_timeout_seconds',TOTAL_DEADLINE_SECONDS)
    return limits['timeout_seconds']


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
    filewise_directory=None;filewise_bundle=None;filewise_manifest=None;filewise_provider=None
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
        prepared_messages=messages_for(prompt['messages'],profile)
        if (profile==PROFILE
                and config.get('application_generation_strategy')=='filewise-v1'):
            filewise_directory=FILEWISE_EVIDENCE_ROOT/f'run-{run.id}-{execution_token}'
            provider=FilewiseApplicationProvider(provider_config,filewise_directory,
                provider_factory=provider_factory,idle_check=ensure_idle,
                execution_context={'kind':'local-inference-service','version':'filewise-v1'})
            filewise_provider=provider
        else:
            provider=provider_factory(provider_config)
        output=provider.complete(prepared_messages)
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
    except Exception as exc:
        error=error or ('filewise_context_limit' if str(exc)=='filewise_context_limit'
                        else 'model_failed_or_invalid_output')
    if filewise_directory is not None:
        try:
            filewise_bundle,filewise_manifest=_filewise_bundle(filewise_directory,
                filewise_provider.manifest if filewise_provider is not None else None)
        except Exception:
            error=error or 'filewise_evidence_invalid'
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
        _attach_filewise_evidence(session,run,filewise_bundle,filewise_manifest)
        finished=(_filewise_finished(filewise_manifest,error) if filewise_manifest is not None else
            output is not None or error in {'truncated_output','empty_output','model_changed','model_inventory','model_http_error'})
        fail(session,run,'instruction_or_policy_changed','stale' if finished else 'uncertain')
    else:
        if error:
            _attach_filewise_evidence(session,run,filewise_bundle,filewise_manifest)
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
            finished=(_filewise_finished(filewise_manifest,error) if filewise_manifest is not None else
                output is not None or error in {'truncated_output','empty_output','model_changed','model_inventory','model_http_error'})
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
            _attach_filewise_evidence(session,run,filewise_bundle,filewise_manifest,attempt)
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
        profile=run.limits.get('output_profile','text')
        if (utc_now()-started).total_seconds()<=_execution_deadline(run.limits,profile)+15:
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
    prepared_messages=messages_for(prompt['messages'],profile)
    if profile==PROFILE and config.get('application_generation_strategy')=='filewise-v1':
        validate_first_filewise_call(config,prepared_messages)
    elif sum(len(m['content'].encode()) for m in prepared_messages)>config['num_ctx']-config['num_predict']-1024:
        raise ValueError('Instrukcja przekracza aktualny limit kontekstu.')
    snapshot={k:getattr(run,k).isoformat() if getattr(run,k) is not None else None for k in ('started_at','finished_at')}
    snapshot.update(request_id=request_id,state=run.state,error_code=run.error_code,limits=run.limits)
    run.metrics=dict(run.metrics or {})|{'retry_history':history+[snapshot]}
    run.limits=config if profile=='text' else config|{'output_profile':profile}
    run.model=config['model'];run.model_digest=config['digest']
    run.state='queued';run.error_code=None;run.started_at=None;run.finished_at=None
    audit(session,run,'explicit_retry');return summary(run)
