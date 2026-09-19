import io
import json
from uuid import uuid4
from zipfile import ZipFile
import pytest
from app.main import app
from app.api.package_runner import get_runner
from app.services import package_runner as service
from app.services.container_runner import create_args
from app.models.package_run import PackageRun
from tests.conftest import OWNER_HEADERS, WORKER_HEADERS
from tests.test_agent_packets import assigned

FILES={'app.py':'print("app")','test_app.py':'# tests','index.html':'<!doctype html>','README.md':'Instructions'}
CONFIG={'profile':'python-web-v1','image':'sha256:'+'a'*64,'harness_checksum':'b'*64,'timeout_seconds':45}


@pytest.fixture(autouse=True)
def fake_runner(monkeypatch):
    monkeypatch.setattr(service,'configuration',lambda:dict(CONFIG))
    class Fake:
        calls=0
        cleanup_calls=[]
        def run(self,files,config,name):
            Fake.calls+=1
            assert files==FILES and config==CONFIG
            return {'exit_code':0,'cli_exit_code':0,'reason':None,'cleanup_confirmed':True,'log':json.dumps({
                'schema':'python-web-test.v1','tests_ok':True,'http_ok':True,'source_not_exposed':True,
                'isolation':{key:True for key in service.ISOLATION_KEYS},'errors':[]})}
        def cleanup(self,name):Fake.cleanup_calls.append(name);return True
    app.dependency_overrides[get_runner]=Fake
    yield Fake
    app.dependency_overrides.pop(get_runner,None)


def package(client):
    task=assigned(client)['tasks'][0]['id']
    response=client.post(f'/api/tasks/{task}/workspace-packages',headers=OWNER_HEADERS,json={'purpose':'Runner fixture','files':FILES})
    assert response.status_code==201,response.text
    p=response.json()
    return {'task_id':task,'package_id':p['artifact_id'],'package_checksum':p['checksum'],'request_id':str(uuid4()),'confirm_execution':True}


def test_run_is_versioned_and_candidate_is_not_acceptance(client,task_repository,fake_runner):
    body=package(client)
    result=client.post('/api/package-runs',headers=OWNER_HEADERS,json=body)
    assert result.status_code==200,result.text
    r=result.json();assert r['state']=='passed' and r['accepted'] is False
    assert client.post('/api/package-runs',headers=OWNER_HEADERS,json=body).json()==r
    assert fake_runner.calls==1
    assert task_repository.get(body['task_id']).progress==0
    download=client.get(f"/api/package-runs/{r['id']}/candidate.zip",headers=OWNER_HEADERS)
    assert download.status_code==200
    with ZipFile(io.BytesIO(download.content)) as z:
        assert z.read('sources/app.py').decode()==FILES['app.py']
        manifest=json.loads(z.read('delivery.json'))
        assert manifest['source_checksum']==body['package_checksum'] and not manifest['accepted']
        assert json.loads(z.read('test-report.json'))['run_id']==r['id']


def test_auth_checksum_and_command_injection(client,fake_runner):
    body=package(client)
    for headers,status in (({},401),(WORKER_HEADERS,403)):
        assert client.post('/api/package-runs',headers=headers,json=body).status_code==status
        assert client.get('/api/package-runs',headers=headers).status_code==status
        assert client.get('/api/package-runs/1/delivery-readiness',headers=headers).status_code==status
    assert client.get('/api/package-runs/99999/delivery-readiness',headers=OWNER_HEADERS).status_code==404
    for key in ('command','image','directory','network'):
        assert client.post('/api/package-runs',headers=OWNER_HEADERS,json=body|{key:'anything'}).status_code==422
    assert client.post('/api/package-runs',headers=OWNER_HEADERS,json=body|{'confirm_execution':False}).status_code==422
    assert client.post('/api/package-runs',headers=OWNER_HEADERS,json=body|{'package_checksum':'f'*64}).status_code==409
    assert fake_runner.calls==0


def test_failure_uncertain_slot_and_recovery(client,task_repository):
    body=package(client)
    class Failed:
        def run(self,*a):raise TimeoutError('secret internal exception')
        def cleanup(self,name):return True
    app.dependency_overrides[get_runner]=Failed
    r=client.post('/api/package-runs',headers=OWNER_HEADERS,json=body).json()
    assert r['state']=='uncertain' and 'secret' not in str(r)
    readiness=client.get(f"/api/package-runs/{r['id']}/delivery-readiness",headers=OWNER_HEADERS).json()
    assert readiness['ready'] is False and readiness['checks'][0]['passed'] is False
    assert client.get(f"/api/package-runs/{r['id']}/candidate.zip",headers=OWNER_HEADERS).status_code==409
    assert client.post('/api/package-runs',headers=OWNER_HEADERS,json=body|{'request_id':str(uuid4())}).status_code==409
    path=f"/api/package-runs/{r['id']}/reconcile"
    assert client.post(path,headers=OWNER_HEADERS).status_code==409
    from datetime import timedelta
    from app.models.task import utc_now
    with task_repository._session_factory() as s:
        s.get(PackageRun,r['id']).created_at=utc_now()-timedelta(seconds=120);s.commit()
    assert client.post(path,headers=OWNER_HEADERS).json()['state']=='interrupted'


def test_fixed_docker_profile_has_no_host_privileges():
    args=create_args('aic-package-'+'a'*32,'/private/sources',CONFIG)
    for required in ('--pull=never','--runtime=runc','--network=none','--read-only','--cap-drop=ALL',
                     '--security-opt=no-new-privileges:true','--pids-limit=64','--memory=512m','--cpus=1'):
        assert required in args
    assert '--privileged' not in args and '--gpus' not in args and '-p' not in args
    assert not any('docker.sock' in value for value in args)
    assert args[args.index('--user')+1]=='65534:65534'
    assert args[args.index('--mount')+1].endswith(',readonly')
    assert args[-4:]==['-I','-S','-B','/workspace/runner_harness.py']
