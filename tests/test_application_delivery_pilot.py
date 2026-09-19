"""Fresh Qwen generation, independent tests, bounded repairs, candidate ZIP."""
import json
import os
from pathlib import Path
from hashlib import sha256
from uuid import uuid4

import pytest
from sqlalchemy import select
from app.main import app
from app.api.local_inference import get_provider_factory
from app.api.package_runner import get_runner
from app.models.task import Task
from app.models.delegation import TaskDelegation
from app.models.organization_os import Agent
from app.models.local_inference import LocalInference
from app.models.package_run import PackageRun
from app.services import local_inference,package_runner,container_runner,application_quality
from app.services.local_ollama import configuration,OllamaProvider,ensure_idle
from app.services.agent_teams import team_key
from app.services.workspace_packages import read_package
from tests.conftest import OWNER_HEADERS
from tests.test_agent_teams import setup,delegate
from tests.test_agent_packets import packet
from tests.test_local_inference import config_and_no_network
from tests.application_pilot_checks import PROBES,harness_source


def test_acceptance_harness_is_separate_and_syntax_valid():
    source=harness_source()
    compile(source,'pilot-harness','exec')  # Compile trusted tester, NOT generated app.
    assert len(PROBES)==14 and 'Independent acceptance' in source
    assert 'isolation_checks()' in source and "signal.alarm(35)" in source


@pytest.mark.skipif(os.environ.get('AIC_DELIVERY_PILOT')!='1',reason='Explicit local Qwen and Docker pilot only')
def test_fresh_application_delivery(client,task_repository,monkeypatch,tmp_path):
    ensure_idle()
    destination=Path(os.environ['AIC_DELIVERY_PILOT_OUTPUT'])
    tester=destination/'independent-harness.py'
    tester.write_text(harness_source(),encoding='utf-8')
    def test_config():
        return container_runner.configuration()|{'harness_checksum':sha256(tester.read_bytes()).hexdigest()}
    monkeypatch.setattr(package_runner,'configuration',test_config)
    monkeypatch.setattr(local_inference,'enabled_config',configuration)
    monkeypatch.setattr(application_quality,'LOCK_ROOT',tmp_path/'quality-locks')
    app.dependency_overrides[get_provider_factory]=lambda:OllamaProvider
    app.dependency_overrides[get_runner]=lambda:container_runner.ContainerRunner(harness=tester)
    setup(client)
    units=client.get('/api/work-orders/options',headers=OWNER_HEADERS).json()['units']
    target=next(u for u in units if u['key']=='web-platforms.business')
    goal=('Build a small Polish web calculator for a project quote with a percentage discount. '
          'GET /api/estimate?hours=8&rate=322&discount=10 returns JSON '
          '{"subtotal":2576,"discount_amount":257.6,"total":2318.4}. '
          'subtotal=hours*rate, discount_amount=subtotal*discount/100, total=subtotal-discount_amount. '
          'Return JSON numbers rounded to two decimal places. Required hours/rate are finite non-negative numbers. '
          'Optional discount defaults to zero and must be finite in range 0..100. '
          'Missing/empty/malformed/negative/non-finite values return HTTP400. Unknown routes404. '
          'Responsive Polish HTML with labels and a button calling the real endpoint; visible result and errors. '
          'Use textContent, no external assets, no database, accounts or tax assumptions. '
          'At least five meaningful unittest cases; /health and other requirements follow python-web-v1.')
    saved=client.post('/api/work-orders',headers=OWNER_HEADERS,json={
        'request_id':str(uuid4()),'title':'Syntetyczny pilot — wycena z rabatem','goal':goal,
        'audience':'Właściciel — test, nie zlecenie klienta',
        'constraints':'Python stdlib. Brak sieci, zależności, publikacji i danych klientów.',
        'organization_unit_id':target['id'],'acceptance_criteria':['8*322 z rabatem10% daje2318.4; błędne dane HTTP400.']}).json()
    assert delegate(client,saved).status_code==200
    task_id=saved['tasks'][0]['id']
    # Fully specified builder pilot, no fabricated accepted analyst result.
    with task_repository._session_factory() as s:
        task=s.get(Task,task_id);assignment=s.get(TaskDelegation,task_id)
        builder=s.scalar(select(Agent).where(Agent.agent_key==team_key(assignment.department_id,'builder')))
        task.title='Implementacja kalkulatora wyceny z rabatem'
        task.description=goal;task.assigned_agent=builder.agent_key
        assignment.worker_id=builder.id;assignment.execution_brief=goal
        assignment.completion_criterion='Pełne źródła, własne testy i zgodność HTTP; odbiór niezależny.'
        s.commit()
    p=packet(client,task_id)
    queued=client.post('/api/local-inference',headers=OWNER_HEADERS,json={
        'request_id':str(uuid4()),'task_id':task_id,'packet_id':p['packet_id'],
        'packet_checksum':p['checksum'],'output_profile':'python-web-v1'}).json()
    report={'scope':'Synthetic isolated DB; fresh Qwen generation; no production work modified.',
            'independent_probes':PROBES,'harness_checksum':test_config()['harness_checksum']}
    try:
        generated=client.post(f"/api/local-inference/{queued['id']}/run",headers=OWNER_HEADERS)
        assert generated.status_code==200,generated.text
        report['generation']=generated.json()
        assert report['generation']['state']=='awaiting_review',report['generation'].get('error_code')
        metrics=report['generation']['metrics']
        params={'request_id':str(uuid4()),'task_id':task_id,'package_id':metrics['package_id'],
                'package_checksum':metrics['package_checksum'],'max_repairs':2,'confirm_automatic_repairs':True}
        created=client.post('/api/application-quality',headers=OWNER_HEADERS,json=params)
        assert created.status_code==200,created.text
        run=client.post(f"/api/application-quality/{created.json()['id']}/run",headers=OWNER_HEADERS)
        assert run.status_code==200,run.text
        report['quality']=run.json()
        with task_repository._session_factory() as s:
            report['tests']=[{'id':r.id,'state':r.state,'result':r.result} for r in s.scalars(select(PackageRun))]
            report['inferences']=[{'id':r.id,'state':r.state,'metrics':r.metrics,'error_code':r.error_code} for r in s.scalars(select(LocalInference))]
        assert report['quality']['state']=='passed',report['quality']
        with task_repository._session_factory() as s:
            _,manifest=read_package(s,task_id,report['quality']['final_package_id'])
            report['final_sources']={f['path']:f['content'] for f in manifest['files']}
            assert s.get(Task,task_id).progress==0
        downloaded=client.get(f"/api/package-runs/{report['quality']['test_run_id']}/candidate.zip",headers=OWNER_HEADERS)
        assert downloaded.status_code==200,downloaded.text
        (destination/'application-candidate.zip').write_bytes(downloaded.content)
        report['candidate_created']=True
        report['owner_accepted']=False
    finally:
        (destination/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
