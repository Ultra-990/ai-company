import json
from uuid import uuid4
import pytest
from app.main import app
from app.api.package_runner import get_preview_runner
from app.services import application_preview as preview
from tests.conftest import OWNER_HEADERS, WORKER_HEADERS
from tests.test_package_runner import package, fake_runner, CONFIG, FILES


def test_preview_supplies_assets_while_package_get_is_metadata_only(client,preview_runner):
    original=package(client)
    files=FILES | {'app.js':'document.querySelector("form").addEventListener("submit",()=>{});',
                   'style.css':'body{color:navy}'}
    stored=client.post(f"/api/tasks/{original['task_id']}/workspace-packages",headers=OWNER_HEADERS,
                      json={'purpose':'Preview asset contract','files':files}).json()
    metadata=client.get(f"/api/tasks/{original['task_id']}/workspace-packages/{stored['artifact_id']}",headers=OWNER_HEADERS).json()
    assert all('content' not in f for f in metadata['files'])
    body=original | {'package_id':stored['artifact_id'],'package_checksum':stored['checksum'],'path':'/'}
    response=client.post('/api/package-runs/preview',headers=OWNER_HEADERS,json=body)
    assert response.status_code==200,response.text
    assert response.json()['assets']=={'app.js':files['app.js'],'style.css':files['style.css']}
    assert response.json()['source_checksum']==metadata['checksum']
    api=client.post('/api/package-runs/preview',headers=OWNER_HEADERS,
                    json=body|{'request_id':str(uuid4()),'path':'/api/estimate?hours=8&rate=322'})
    assert 'assets' not in api.json()


@pytest.fixture
def preview_runner(monkeypatch):
    calls=[]
    monkeypatch.setattr(preview,'preview_configuration',lambda:CONFIG | {'profile':'python-web-preview-v1'})
    class Fake:
        def __init__(self,path):self.path=path
        def run(self,files,config,name):
            calls.append(self.path)
            return {'exit_code':0,'cli_exit_code':0,'reason':None,'cleanup_confirmed':True,
                'log':json.dumps({'schema':'python-web-preview.v1','response':{
                'status':200,'body':'{"total":2576}','content_type':'application/json'}})}
    app.dependency_overrides[get_preview_runner]=lambda:Fake
    yield calls
    app.dependency_overrides.pop(get_preview_runner,None)


def test_preview_is_bound_and_not_a_test_pass(client,preview_runner):
    body=package(client)|{'path':'/api/estimate?hours=8&rate=322'}
    reply=client.post('/api/package-runs/preview',headers=OWNER_HEADERS,json=body)
    assert reply.status_code==200,reply.text
    assert json.loads(reply.json()['response']['body'])['total']==2576
    assert client.post('/api/package-runs/preview',headers=OWNER_HEADERS,json=body).json()==reply.json()
    assert len(preview_runner)==1
    run_id=reply.json()['run_id']
    assert client.get(f'/api/package-runs/{run_id}/candidate.zip',headers=OWNER_HEADERS).status_code==409
    assert client.post('/api/package-runs',headers=OWNER_HEADERS,json={k:v for k,v in body.items() if k!='path'}).status_code==409
    assert client.post('/api/package-runs/preview',headers=OWNER_HEADERS,json=body|{'path':'/'}).status_code==409
    assert client.get('/api/package-runs',headers=OWNER_HEADERS).json()['runs'][0]['state']=='previewed'


def test_preview_authorization_and_path_allowlist(client,preview_runner):
    body=package(client)
    for headers in ({},WORKER_HEADERS):
        assert client.post('/api/package-runs/preview',headers=headers,json=body).status_code in (401,403)
    for path in ('http://localhost:8000/api/tasks','//evil/x','/app.py','/api/../tasks','/api/x\r\nHost: evil','/api/x#fragment','/api/x?q=/etc/passwd'):
        assert client.post('/api/package-runs/preview',headers=OWNER_HEADERS,json=body|{'path':path}).status_code==409
    assert client.post('/api/package-runs/preview',headers=OWNER_HEADERS,json=body|{'package_checksum':'f'*64}).status_code==409
    assert client.post('/api/package-runs/preview',headers=OWNER_HEADERS,json=body|{'method':'POST'}).status_code==422
    assert preview_runner==[]


def test_frame_has_no_token_and_strict_sandbox(client):
    frame=client.get('/os/application-frame')
    assert frame.status_code==200
    csp=frame.headers['content-security-policy']
    for clause in ("sandbox allow-scripts","connect-src 'none'","form-action 'none'","frame-src 'none'"):
        assert clause in csp
    assert 'allow-same-origin' not in csp and 'Bearer' not in frame.text
    assert 'Otwórz aplikację w izolacji' in client.get('/static/organization-os/build.js').text


def test_preview_failures_do_not_return_forged_success(client,preview_runner):
    class Failed:
        def __init__(self,path):pass
        def run(self,*args):return {'exit_code':0,'cli_exit_code':0,'cleanup_confirmed':False,'log':'{}'}
    app.dependency_overrides[get_preview_runner]=lambda:Failed
    body=package(client)
    assert client.post('/api/package-runs/preview',headers=OWNER_HEADERS,json=body).status_code==409
    assert client.post('/api/package-runs/preview',headers=OWNER_HEADERS,json=body|{'request_id':str(uuid4())}).status_code==409
