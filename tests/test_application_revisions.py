import json
import os
from pathlib import Path
from zipfile import ZipFile
from uuid import uuid4
import pytest
from app.main import app
from app.api.local_inference import get_provider_factory
from app.api.package_runner import get_runner
from app.models.artifact import Artifact
from app.models.task import TaskAttempt, TaskStatus
from app.services import local_inference
from app.services.workspace_packages import read_package
from app.services.package_runner import ISOLATION_KEYS
from tests.conftest import OWNER_HEADERS,WORKER_HEADERS
from tests.test_application_generation import builder_packet
from tests.test_local_inference import config_and_no_network,CONFIG
from tests.test_package_runner import fake_runner,FILES


@pytest.fixture
def generated(client,request):
    base_files=FILES
    if request.node.name in {'test_real_qwen_revision_pilot','test_real_qwen_automatic_repair_pilot'}:
        with ZipFile('/home/marcin/ai-company-workspaces/candidate-vmq0lxsm/application-candidate.zip') as archive:
            base_files={name.removeprefix('sources/'):archive.read(name).decode() for name in archive.namelist() if name.startswith('sources/')}
        if request.node.name=='test_real_qwen_automatic_repair_pilot':
            assert 'total = hours * rate' in base_files['app.py']
            base_files['app.py']=base_files['app.py'].replace('total = hours * rate','total = hours + rate')
    class Provider:
        calls=[]
        def __init__(self,config):self.config=config
        def complete(self,messages):
            Provider.calls.append(messages)
            files=base_files if len(Provider.calls)==1 else base_files|{'README.md':'Poprawiona instrukcja uruchomienia serwera.'}
            payload={'changes':{'README.md':files['README.md']}} if 'changes' in self.config.get('format',{}).get('properties',{}) else {'files':files}
            return {'content':json.dumps(payload),'model':CONFIG['model'],'digest':CONFIG['digest'],'done_reason':'stop'}
    app.dependency_overrides[get_provider_factory]=lambda:Provider
    p=builder_packet(client)
    queued=client.post('/api/local-inference',headers=OWNER_HEADERS,json={
        'request_id':str(uuid4()),'task_id':p['task_id'],'packet_id':p['packet_id'],'packet_checksum':p['checksum'],'output_profile':'python-web-v1'}).json()
    response=client.post(f"/api/local-inference/{queued['id']}/run",headers=OWNER_HEADERS)
    assert response.status_code==200,response.text
    run=response.json();assert run['state']=='awaiting_review'
    body={'task_id':p['task_id'],'package_id':run['metrics']['package_id'],'package_checksum':run['metrics']['package_checksum'],
          'request_id':str(uuid4()),'description':'README nie wyjaśnia sposobu uruchomienia.',
          'expected_result':'Instrukcja podaje uruchomienie serwera i adres aplikacji.',
          'evidence':['Otworzono README paczki i nie znaleziono adresu.'],'auto_test':True,'confirm_revision':True}
    return body,run,Provider


def test_revision_preserves_old_version_and_runs_tests_once(client,task_repository,generated):
    body,old,provider=generated
    class Runner:
        calls=0
        def run(self,files,config,name):
            Runner.calls+=1;assert 'Poprawiona' in files['README.md']
            return {'exit_code':0,'cli_exit_code':0,'reason':None,'cleanup_confirmed':True,
              'log':json.dumps({'schema':'python-web-test.v1','tests_ok':True,'http_ok':True,'source_not_exposed':True,
                                'isolation':{k:True for k in ISOLATION_KEYS},'errors':[]})}
    app.dependency_overrides[get_runner]=Runner
    saved=client.post('/api/application-revisions',headers=OWNER_HEADERS,json=body)
    assert saved.status_code==200,saved.text
    revision=saved.json();assert revision['state']=='queued'
    assert len(provider.calls)==1
    assert task_repository.get(body['task_id']).status==TaskStatus.BLOCKED
    assert client.post('/api/application-revisions',headers=OWNER_HEADERS,json=body).json()['id']==revision['id']
    changed=body|{'expected_result':'Inne oczekiwanie tej samej poprawki.'}
    assert client.post('/api/application-revisions',headers=OWNER_HEADERS,json=changed).status_code==409
    result=client.post(f"/api/application-revisions/{revision['id']}/run",headers=OWNER_HEADERS)
    assert result.status_code==200,result.text
    data=result.json();assert data['state']=='awaiting_review' and data['test_state']=='passed'
    assert data['new_package_id']!=body['package_id'] and not data['accepted']
    assert body['description'] in str(provider.calls[-1]) and 'print' in str(provider.calls[-1])
    assert client.post(f"/api/application-revisions/{revision['id']}/run",headers=OWNER_HEADERS).json()==data
    assert len(provider.calls)==2 and Runner.calls==1
    with task_repository._session_factory() as s:
        previous,payload=read_package(s,body['task_id'],body['package_id'])
        assert previous.checksum==body['package_checksum'] and {f['path']:f['content'] for f in payload['files']}==FILES
        assert s.get(TaskAttempt,old['attempt_id']).verification_status=='rejected'
    assert task_repository.get(body['task_id']).status==TaskStatus.IN_PROGRESS
    assert task_repository.get(body['task_id']).progress==0
    assert client.get('/api/application-revisions',headers=OWNER_HEADERS).json()['revisions'][0]['id']==revision['id']
    assert client.post('/api/application-revisions',headers=OWNER_HEADERS,json=body|{'request_id':str(uuid4())}).status_code==409


def test_revision_rejects_bad_binding_auth_and_rolls_back(client,task_repository,generated,monkeypatch):
    body,old,_=generated
    for headers in ({},WORKER_HEADERS):
        assert client.post('/api/application-revisions',headers=headers,json=body).status_code in (401,403)
    assert client.post('/api/application-revisions',headers=OWNER_HEADERS,json=body|{'package_checksum':'f'*64}).status_code==409
    assert client.post('/api/application-revisions',headers=OWNER_HEADERS,json=body|{'confirm_revision':False}).status_code==422
    assert client.post('/api/application-revisions',headers=OWNER_HEADERS,json=body|{'evidence':[]}).status_code==422
    def failure(*args,**kwargs):raise ValueError('Kontekst nie mieści się w limicie.')
    monkeypatch.setattr(local_inference,'enqueue',failure)
    assert client.post('/api/application-revisions',headers=OWNER_HEADERS,json=body).status_code==409
    with task_repository._session_factory() as s:
        assert s.get(TaskAttempt,old['attempt_id']).status=='awaiting_review'
    assert task_repository.get(body['task_id']).status==TaskStatus.IN_PROGRESS
    assert client.get('/api/application-revisions',headers=OWNER_HEADERS).json()['revisions']==[]


def test_invalid_model_revision_never_runs_code(client,generated):
    body,old,provider=generated
    class Invalid:
        def __init__(self,c):pass
        def complete(self,m):return {'content':'not JSON','model':CONFIG['model'],'digest':CONFIG['digest'],'done_reason':'stop'}
    app.dependency_overrides[get_provider_factory]=lambda:Invalid
    saved=client.post('/api/application-revisions',headers=OWNER_HEADERS,json=body).json()
    response=client.post(f"/api/application-revisions/{saved['id']}/run",headers=OWNER_HEADERS)
    assert response.status_code==200,response.text
    assert response.json()['state']=='failed' and response.json()['new_package_id'] is None
    assert response.json()['test_run_id'] is None


@pytest.mark.skipif(os.environ.get('AIC_REVISION_PILOT')!='1',reason='Real Qwen/Docker pilot requires explicit script invocation')
def test_real_qwen_revision_pilot(client,generated,monkeypatch,task_repository):
    from app.services.local_ollama import OllamaProvider,configuration
    from app.services import package_runner,container_runner
    from app.models.local_inference import LocalInference
    body,old,_=generated
    # The generic department fixture describes an interior-design website.
    # This pilot is explicitly a calculator copy: make its current brief agree
    # with the source under revision before creating the revision packet.
    from app.models.task import Task
    from app.models.delegation import TaskDelegation
    with task_repository._session_factory() as s:
        task=s.get(Task,body['task_id']);delegation=s.get(TaskDelegation,task.id)
        task.title='Testowa kopia kalkulatora godzin i stawki'
        task.description='Mała polska aplikacja webowa. Formularz godzin i stawki wysyła GET /api/estimate?hours=8&rate=322 i pokazuje koszt 2576 zł. Zachowaj obliczenia i walidację błędów.'
        delegation.execution_brief=task.description
        delegation.completion_criterion='Formularz oblicza godziny razy stawka; 8 × 322 = 2576; nieujemne skończone liczby; błędne dane dają 400.'
        s.commit()
    monkeypatch.setattr(local_inference,'enabled_config',configuration)
    monkeypatch.setattr(package_runner,'configuration',container_runner.configuration)
    app.dependency_overrides[get_provider_factory]=lambda:OllamaProvider
    app.dependency_overrides[get_runner]=container_runner.ContainerRunner
    body=body|{'description':'Dodaj stan Obliczanie… podczas żądania fetch oraz wyłącz przycisk do zakończenia. Nie zmieniaj obliczeń API.',
        'expected_result':'8 i 322 nadal daje 2576 zł. Interfejs wyświetla Obliczanie… i przywraca przycisk po sukcesie lub błędzie. README ostrzega przed otwieraniem index.html z dysku.',
        'evidence':['Kontrola testowej kopii paczki: brak widocznego stanu oczekiwania.']}
    saved=client.post('/api/application-revisions',headers=OWNER_HEADERS,json=body)
    assert saved.status_code==200,saved.text
    response=client.post(f"/api/application-revisions/{saved.json()['id']}/run",headers=OWNER_HEADERS)
    data=response.json()
    with task_repository._session_factory() as s:
        inference=s.get(LocalInference,saved.json()['inference_id'])
        report={'response':data,'metrics':inference.metrics,'limits':inference.limits,
                'model':inference.model,'digest':inference.model_digest,
                'scope':'Isolated test database. Original production task 45 and package 5 unchanged.'}
    destination=Path(os.environ['AIC_REVISION_PILOT_OUTPUT'])
    (destination/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    assert response.status_code==200,response.text
    assert data['state']=='awaiting_review' and data['test_state']=='passed',data
    with task_repository._session_factory() as s:
        _,new=read_package(s,body['task_id'],data['new_package_id'])
        browser_source='\n'.join(f['content'] for f in new['files'] if f['path'].endswith(('.js','.html')))
        assert 'Obliczanie' in browser_source
        assert s.get(Artifact,body['package_id']).checksum==body['package_checksum']
    candidate=client.get(f"/api/package-runs/{data['test_run_id']}/candidate.zip",headers=OWNER_HEADERS)
    assert candidate.status_code==200,candidate.text
    (destination/'revised-candidate.zip').write_bytes(candidate.content)
