"""Isolated, explicitly enabled canary for the normal filewise inference path."""
import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import sqlite3
from uuid import uuid4

import pytest
from fastapi.encoders import jsonable_encoder
from sqlalchemy import select

from app.models.artifact import Artifact
from app.models.delegation import TaskDelegation
from app.models.local_inference import LocalInference
from app.models.organization_os import Agent
from app.models.task import Task
from app.services import container_runner, local_inference, package_runner
from app.services.agent_teams import team_key
from app.services.local_ollama import OllamaProvider, configuration
from app.services.workspace_packages import read_package
from scripts import filewise_production_canary as wrapper
from scripts import filewise_production_canary_case as scenario
from scripts.filewise_production_canary import command, output_directory
from scripts.compare_local_models import check_idle
from tests.conftest import OWNER_HEADERS
from tests.test_agent_packets import packet
from tests.test_agent_teams import delegate, setup


def write_report(path,report):
    """Use FastAPI's API-compatible datetime/enum encoding; never stringify wholesale."""
    path.write_text(json.dumps(jsonable_encoder(report),ensure_ascii=False,indent=2),encoding='utf-8')


def test_canary_case_is_small_and_harness_is_private():
    source=scenario.harness_source();compile(source,'filewise-canary-harness','exec')
    public=json.dumps(scenario.public_case(),ensure_ascii=False)
    assert scenario.CASE_VERSION=='compact-v2' and sum(scenario.SOFT_FILE_BUDGETS.values())==5900
    assert 'style.css <=400' in public and '/api/count?text=A1-b' not in public
    assert 'isolation_checks()' in source and len(scenario.PROBES)==6


def test_wrapper_is_guarded_and_scoped(tmp_path,monkeypatch):
    workspace=tmp_path/'workspace';workspace.mkdir()
    monkeypatch.setattr(wrapper,'WORKSPACE_ROOT',workspace)
    with pytest.raises(argparse.ArgumentTypeError,match='workspace root'):
        output_directory(str(tmp_path/'outside'))
    target=workspace/'filewise-canary-example'
    assert command(target)[-2:]==['tests/test_filewise_production_canary.py::test_real_filewise_production_path_canary','-s']
    with pytest.raises(argparse.ArgumentTypeError):
        output_directory(str(workspace/'..'/'escape'))
    real=workspace/'real';real.mkdir()
    alias=workspace/'alias';alias.symlink_to(real,target_is_directory=True)
    with pytest.raises(argparse.ArgumentTypeError):wrapper.output_directory(str(alias/'output'))


def test_report_recorder_encodes_service_datetimes_without_lossy_default_str(tmp_path):
    from datetime import datetime,timezone
    path=tmp_path/'report.json';moment=datetime(2026,10,11,19,24,22,tzinfo=timezone.utc)
    write_report(path,{'generation':{'created_at':moment,'finished_at':None},'actual':False})
    saved=json.loads(path.read_text())
    assert saved=={'generation':{'created_at':'2026-10-11T19:24:22+00:00','finished_at':None},
        'actual':False}


@pytest.mark.skipif(os.environ.get('AIC_FILEWISE_PRODUCTION_CANARY')!='1',
    reason='Explicit local Ollama canary only')
def test_real_filewise_production_path_canary(client,task_repository,monkeypatch):
    destination=Path(os.environ['AIC_FILEWISE_PRODUCTION_CANARY_OUTPUT']).absolute()
    assert destination.is_relative_to(wrapper.WORKSPACE_ROOT)
    fixed=configuration()
    assert fixed['num_ctx']==16384 and fixed['num_predict']==4096
    fixed=fixed|{'application_generation_strategy':'filewise-v1'}
    monkeypatch.setattr(local_inference,'enabled_config',lambda:dict(fixed))
    monkeypatch.setattr(local_inference,'ensure_idle',check_idle)
    monkeypatch.setattr(local_inference,'FILEWISE_EVIDENCE_ROOT',destination/'private-evidence')
    harness=destination/'independent-harness.py';harness.write_text(scenario.harness_source(),encoding='utf-8')
    harness_checksum=sha256(harness.read_bytes()).hexdigest()
    def runner_config():return container_runner.configuration()|{'harness_checksum':harness_checksum}
    monkeypatch.setattr(package_runner,'configuration',runner_config)
    class CheckedRunner(container_runner.ContainerRunner):
        def run(self,*args,**kwargs):check_idle();return super().run(*args,**kwargs)
    report={'schema':'filewise-production-canary.v1','case_version':scenario.CASE_VERSION,
        'case':scenario.public_case(),
        'isolated_database':'isolated.db',
        'harness_checksum':sha256(scenario.harness_source().encode()).hexdigest(),
        'source_quality':{'state':'not_created'},'isolated_tests':{'state':'not_created'},'candidate_created':False,
        'owner_accepted':False,'deployed':False}
    try:
        setup(client)
        units=client.get('/api/work-orders/options',headers=OWNER_HEADERS).json()['units']
        unit=next(item for item in units if item['key']=='web-platforms.business')
        case=scenario.public_case()
        intake={key:case[key] for key in ('title','goal','audience','constraints','acceptance_criteria')}
        saved=client.post('/api/work-orders',headers=OWNER_HEADERS,json={
            'request_id':str(uuid4()),**intake,'organization_unit_id':unit['id']})
        assert saved.status_code==201,saved.text
        order=saved.json();assert delegate(client,order).status_code==200
        task_id=order['tasks'][0]['id'];report['task_id']=task_id
        with task_repository._session_factory() as session:
            task=session.get(Task,task_id);assignment=session.get(TaskDelegation,task_id)
            builder=session.scalar(select(Agent).where(
                Agent.agent_key==team_key(assignment.department_id,'builder')))
            task.title=scenario.TITLE;task.description=scenario.GOAL;task.assigned_agent=builder.agent_key
            assignment.worker_id=builder.id;assignment.execution_brief=scenario.GOAL
            assignment.completion_criterion='Sześć małych plików źródłowych; wynik wymaga osobnej izolowanej oceny.'
            session.commit()
        prepared=packet(client,task_id)
        with task_repository._session_factory() as session:
            queued=local_inference.enqueue(session,task_id,prepared['packet_id'],prepared['checksum'],
                str(uuid4()),output_profile='python-web-v1');session.commit()
            report['inference_id']=queued['id']
            result=local_inference.execute(session,queued['id'],OllamaProvider);report['generation']=result
            assert result['state']=='awaiting_review',result
            assert result['metrics']['filewise']['assembled'] is True
            assert result['metrics'].get('package_id') and result['attempt_id']
            _,package=read_package(session,task_id,result['metrics']['package_id'])
            contents={item['path']:item['content'] for item in package['files']}
            report['source_quality']={'state':'measured','all_six_sources':set(contents)==set(
                scenario.SOFT_FILE_BUDGETS),'total_characters':sum(map(len,contents.values())),
                'total_bytes':sum(len(value.encode('utf-8')) for value in contents.values()),
                'files':{name:{'characters':len(contents[name]) if name in contents else None,
                    'bytes':len(contents[name].encode('utf-8')) if name in contents else None,
                    'soft_target_characters':target,
                    'within_soft_target':name in contents and len(contents[name])<=target}
                    for name,target in scenario.SOFT_FILE_BUDGETS.items()}}
            tested=package_runner.start(session,task_id,result['metrics']['package_id'],
                result['metrics']['package_checksum'],str(uuid4()),CheckedRunner(harness=harness))
            report['isolated_tests']=tested
            assert tested['state']=='passed',tested
    except Exception as exc:
        report['failure']={'type':type(exc).__name__,'message':str(exc)[:1000]}
        raise
    finally:
        with task_repository._session_factory() as session:
            rows=list(session.scalars(select(LocalInference)))
            report['inferences']=[{'id':row.id,'state':row.state,'error_code':row.error_code,
                'metrics':row.metrics,'attempt_id':row.attempt_id} for row in rows]
            artifact_ids=[row.metrics.get('filewise',{}).get('artifact_id') for row in rows]
            report['evidence']=[{'artifact_id':item.id,'checksum':item.checksum}
                for item in (session.get(Artifact,value) for value in artifact_ids if value) if item]
        source=sqlite3.connect(task_repository._engine.url.database)
        target=sqlite3.connect(destination/'isolated.db')
        try:source.backup(target)
        finally:target.close();source.close()
        (destination/'isolated.db').chmod(0o600)
        write_report(destination/'report.json',report)
