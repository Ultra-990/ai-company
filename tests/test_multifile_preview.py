import json
import os
from uuid import uuid4

import pytest

from app.services import multifile_preview as preview
from scripts.check_multifile_isolation import sources

from app.main import app
from app.api.package_runner import get_preview_runner
from app.services import application_preview
from app.services.package_runner import ISOLATION_KEYS
from tests.conftest import OWNER_HEADERS


def preview_sources():
    files = sources('success')
    files['app.py'] = '''import os,json
from pathlib import Path
from http.server import BaseHTTPRequestHandler,HTTPServer
from modules.logic import total
class Handler(BaseHTTPRequestHandler):
 def do_GET(self):
  if self.path not in ('/','/health','/api/total'):self.send_error(404);return
  if self.path=='/':body=Path('/workspace/index.html').read_bytes();kind='text/html'
  else:body=json.dumps({'status':'ok'} if self.path=='/health' else {'total':total(8,322)}).encode();kind='application/json'
  self.send_response(200);self.send_header('Content-Type',kind);self.end_headers();self.wfile.write(body)
if __name__=='__main__':HTTPServer((os.environ['HOST'],int(os.environ['PORT'])),Handler).serve_forever()
'''
    files['index.html'] = '<!doctype html><html><head><link rel="stylesheet" href="/static/site.css"></head><body><button id="calculate">Oblicz</button><output id="result"></output><script src="/static/app.js"></script></body></html>'
    files['static/app.js'] = "document.querySelector('#calculate').onclick=async()=>{const r=await fetch('/api/total');document.querySelector('#result').textContent=(await r.json()).total;};"
    return files


def test_staging_request_is_server_owned_and_readonly(tmp_path):
    folder = tmp_path / 'sources'
    folder.mkdir(mode=0o700)
    runner = preview.MultifilePreviewRunner('/api/total')
    runner.stage_sources(folder, preview_sources())
    assert json.loads((folder / 'preview_request.json').read_text()) == {'path': '/api/total'}
    assert (folder / 'preview_request.json').stat().st_mode & 0o777 == 0o444
    assert (folder / 'modules/logic.py').read_text() == preview_sources()['modules/logic.py']


def test_client_cannot_supply_control_file_or_arbitrary_path(tmp_path):
    folder = tmp_path / 'sources'
    folder.mkdir(mode=0o700)
    with pytest.raises(ValueError):
        preview.MultifilePreviewRunner('http://127.0.0.1:8000/api/tasks')
    with pytest.raises(ValueError):
        preview.MultifilePreviewRunner('/').stage_sources(folder, preview_sources() | {'preview_request.json': '{}'})
    assert list(folder.iterdir()) == []


@pytest.fixture
def api_preview(monkeypatch):
    config = {'profile':preview.PROFILE,'image':'test-image','harness_checksum':'a'*64,'stateless':True}
    monkeypatch.setattr(application_preview, 'preview_configuration', lambda: {'profile':'python-web-preview-v1'})
    monkeypatch.setattr(preview, 'certified_configuration', lambda: dict(config))
    class Fake:
        calls = 0
        schema = 'python-web-multifile-preview.v1'
        isolation = {key:True for key in ISOLATION_KEYS}
        def __init__(self,path):self.path=path
        def run(self,files,settings,name):
            Fake.calls += 1
            assert settings == config | {'request_path':self.path}
            return dict(exit_code=0, cli_exit_code=0, cleanup_confirmed=True, reason=None,
                        log=json.dumps({'schema':self.schema,'isolation':self.isolation,'errors':[],
                             'response':{'status':200,'body':'<!doctype html>','content_type':'text/html'}}))
    previous=app.dependency_overrides.get(get_preview_runner)
    app.dependency_overrides[get_preview_runner]=lambda:Fake
    yield Fake
    if previous is None:app.dependency_overrides.pop(get_preview_runner,None)
    else:app.dependency_overrides[get_preview_runner]=previous


def test_api_assets_binding_and_replay(client,task_repository,api_preview):
    from tests.test_multifile_execution import package
    body=package(client,task_repository,preview_sources())
    response=client.post('/api/package-runs/preview',headers=OWNER_HEADERS,json=body)
    assert response.status_code==200,response.text
    assert response.json()['assets']=={k:v for k,v in preview_sources().items() if k in {'static/app.js','static/site.css'}}
    assert response.json()['source_checksum']==body['package_checksum']
    assert client.post('/api/package-runs/preview',headers=OWNER_HEADERS,json=body).json()==response.json()
    assert api_preview.calls==1
    assert client.get(f"/api/package-runs/{response.json()['run_id']}/candidate.zip",headers=OWNER_HEADERS).status_code==409


@pytest.mark.parametrize('damage',['schema','isolation'])
def test_preview_requires_own_schema_and_full_isolation(client,task_repository,api_preview,damage):
    from tests.test_multifile_execution import package
    body=package(client,task_repository,preview_sources())
    if damage=='schema':api_preview.schema='python-web-preview.v1'
    else:api_preview.isolation={'non_root':True}
    assert client.post('/api/package-runs/preview',headers=OWNER_HEADERS,json=body).status_code==409


@pytest.mark.skipif(os.environ.get('AIC_MULTIFILE_API_PILOT') != '1', reason='Explicit real Docker only')
def test_real_multifile_preview_pilot():
    from app.services.package_runner import ISOLATION_KEYS
    for path in ('/', '/api/total'):
        config = preview.preview_configuration() | {'request_path': path}
        result = preview.MultifilePreviewRunner(path).run(preview_sources(), config, 'aic-package-' + uuid4().hex)
        assert result['cleanup_confirmed'] and result['exit_code'] == 0, result
        report = json.loads(result['log'])
        assert report['schema'] == 'python-web-multifile-preview.v1'
        assert set(report['isolation']) == ISOLATION_KEYS and all(v is True for v in report['isolation'].values())
        assert report['errors'] == []
        if path == '/':
            assert 'static/app.js' in report['response']['body']
        else:
            assert json.loads(report['response']['body']) == {'total': 2576}


@pytest.mark.skipif(os.environ.get('AIC_MULTIFILE_BROWSER_PILOT') != '1', reason='Explicit real Chrome + Docker pilot only')
def test_real_multifile_browser(client,task_repository):
    import asyncio
    from tests.test_multifile_execution import package
    from tests.browser_multifile_probe import check
    body=package(client,task_repository,preview_sources())
    asyncio.run(check(client,body,OWNER_HEADERS))
