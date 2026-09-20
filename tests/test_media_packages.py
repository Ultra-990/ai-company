import base64
from hashlib import sha256
import io
import json
import os
from uuid import uuid4
from zipfile import ZipFile

from PIL import Image
import pytest

from app.main import app
from app.api.package_runner import get_runner
from app.models.artifact import Artifact
from app.models.task import Task
from app.services import package_runner, media_packages
from tests.conftest import OWNER_HEADERS, WORKER_HEADERS
from tests.test_multifile_execution import FLAT, sources
from tests.test_package_acceptance import decision, post

MEDIA = FLAT | {'profile':media_packages.PROFILE, 'harness_checksum':'d'*64}


def png(color='red'):
    output=io.BytesIO();Image.new('RGB',(8,8),color).save(output,format='PNG')
    return base64.b64encode(output.getvalue()).decode()


def payload():
    return {'purpose':'Synthetic PNG package', 'files':sources('success'), 'images':{'static/image.png':png()}}


def save(client, repo, data=None, task_id=None):
    task_id = task_id or repo.create(title='Synthetic media package').id
    response=client.post(f'/api/tasks/{task_id}/workspace-media-packages',headers=OWNER_HEADERS,json=data or payload())
    assert response.status_code==201,response.text
    package=response.json()
    assert package['execution_profile']==media_packages.PROFILE
    return dict(task_id=task_id,package_id=package['artifact_id'],package_checksum=package['checksum'],
                request_id=str(uuid4()),confirm_execution=True)


@pytest.fixture
def fake(monkeypatch):
    monkeypatch.setattr(package_runner,'configuration',lambda:dict(FLAT))
    monkeypatch.setattr(package_runner,'media_configuration',lambda preview=False:dict(MEDIA))
    class Fake:
        calls=0;assets_ok=True;cleanup=True
        def run(self,files,config,name):
            Fake.calls+=1
            assert config==MEDIA
            assert files['static/image.png'].startswith('iVBOR')
            return {'exit_code':0,'cli_exit_code':0,'cleanup_confirmed':self.cleanup,'reason':None,
                'log':json.dumps({'schema':'python-web-media-test.v1','tests_ok':True,'http_ok':True,
                    'source_not_exposed':True,'assets_ok':self.assets_ok,
                    'isolation':{k:True for k in package_runner.ISOLATION_KEYS},'errors':[]})}
    old=app.dependency_overrides.get(get_runner);app.dependency_overrides[get_runner]=Fake
    yield Fake
    if old is None:app.dependency_overrides.pop(get_runner,None)
    else:app.dependency_overrides[get_runner]=old


def test_store_retry_inventory_and_binary_download(client,task_repository):
    data=payload();body=save(client,task_repository,data)
    retry=save(client,task_repository,data,body['task_id'])
    assert retry['package_id']==body['package_id']
    base=f"/api/tasks/{body['task_id']}/workspace-packages"
    listing=client.get(base,headers=OWNER_HEADERS).json()['packages']
    assert len(listing)==1
    entry=next(e for e in listing[0]['files'] if e['path'].endswith('.png'))
    assert entry['encoding']=='base64' and 'content' not in entry
    raw=base64.b64decode(data['images']['static/image.png'])
    assert entry['sha256']==sha256(raw).hexdigest() and entry['size_bytes']==len(raw)
    response=client.get(base+f"/{body['package_id']}/download",headers=OWNER_HEADERS)
    with ZipFile(io.BytesIO(response.content)) as archive:
        assert archive.read('static/image.png')==raw
    assert task_repository.get_required(body['task_id']).progress==0


def test_review_covers_png_and_new_image_requires_new_review(client,task_repository,fake):
    body=save(client,task_repository)
    run=client.post('/api/package-runs',headers=OWNER_HEADERS,json=body).json()
    assert run['state']=='passed',run
    base=f"/api/package-runs/{run['id']}"
    assert client.post(base+'/release',headers=OWNER_HEADERS).status_code==409
    assert post(client,run,decision(client,run)).status_code==200
    assert client.post(base+'/release',headers=OWNER_HEADERS).status_code==200
    zipped=client.get(base+'/released.zip',headers=OWNER_HEADERS)
    assert zipped.status_code==200,zipped.text[:300] if zipped.status_code!=200 else ''
    with ZipFile(io.BytesIO(zipped.content)) as archive:
        assert archive.read('sources/static/image.png')==base64.b64decode(png())
        assert 'unittest discover' in archive.read('CLIENT-START-HERE.md').decode()
    revised=save(client,task_repository,payload()|{'images':{'static/image.png':png('blue')}},body['task_id'])
    assert revised['package_id']!=body['package_id'] and revised['package_checksum']!=body['package_checksum']
    newer=client.post('/api/package-runs',headers=OWNER_HEADERS,json=revised).json()
    assert newer['state']=='passed'
    assert client.post(f"/api/package-runs/{newer['id']}/release",headers=OWNER_HEADERS).status_code==409
    assert fake.calls==2 and task_repository.get_required(body['task_id']).progress==0


@pytest.mark.parametrize('change',['image','report','scope','revoked','new_test','profile'])
def test_release_is_invalidated_by_changed_evidence(client,task_repository,fake,change,monkeypatch):
    body=save(client,task_repository);run=client.post('/api/package-runs',headers=OWNER_HEADERS,json=body).json()
    receipt=decision(client,run);assert post(client,run,receipt).status_code==200
    base=f"/api/package-runs/{run['id']}"
    assert client.post(base+'/release',headers=OWNER_HEADERS).status_code==200
    if change=='revoked':post(client,run,receipt|{'request_id':str(uuid4()),'accepted':False})
    elif change=='new_test':client.post('/api/package-runs',headers=OWNER_HEADERS,json=body|{'request_id':str(uuid4())})
    elif change=='profile':monkeypatch.setattr(package_runner,'media_configuration',lambda:MEDIA|{'harness_checksum':'e'*64})
    else:
        with task_repository._session_factory() as session:
            if change=='scope':session.get(Task,body['task_id']).description='Scope changed'
            elif change=='report':session.get(Artifact,run['report_id']).content='{}'
            else:
                row=session.get(Artifact,body['package_id']);data=json.loads(row.content)
                next(e for e in data['files'] if e['path'].endswith('.png'))['content']=png('blue')
                row.content=json.dumps(data)  # Does not possess the old checksum.
            session.commit()
    assert client.get(base+'/released.zip',headers=OWNER_HEADERS).status_code==409


@pytest.mark.parametrize('images',[{'../x.png':'x'},{'static/x.svg':'x'}, {'static/x.png':'x'},
    {'static/x.png':base64.b64encode(b'not PNG').decode()}, {'static/image.png':''}])
def test_bad_images_never_create_package(client,task_repository,images):
    task=task_repository.create(title='Rejected media')
    response=client.post(f'/api/tasks/{task.id}/workspace-media-packages',headers=OWNER_HEADERS,
        json=payload()|{'images':images})
    assert response.status_code in (409,422)
    assert client.get(f'/api/tasks/{task.id}/workspace-packages',headers=OWNER_HEADERS).json()['packages']==[]


def test_owner_only_and_text_editor_cannot_corrupt_images(client,task_repository):
    body=save(client,task_repository)
    for headers,status in (({},401),(WORKER_HEADERS,403)):
        assert client.post(f"/api/tasks/{body['task_id']}/workspace-media-packages",headers=headers,json=payload()).status_code==status
    response=client.post(f"/api/tasks/{body['task_id']}/workspace-packages/{body['package_id']}/edits",
        headers=OWNER_HEADERS,json={'request_id':str(uuid4()),'base_checksum':body['package_checksum'],
            'purpose':'Should require full binary import','changes':{'README.md':'New readme'},'removals':[]})
    assert response.status_code==409
    source=client.get(f"/api/tasks/{body['task_id']}/workspace-packages/{body['package_id']}/source",
        headers=OWNER_HEADERS,params={'path':'static/image.png'})
    assert source.status_code==409


def test_text_schema_cannot_activate_binary_runner(client,task_repository,fake):
    task=task_repository.create(title='Legacy text package with base64 string')
    data=payload()
    saved=client.post(f'/api/tasks/{task.id}/workspace-packages',headers=OWNER_HEADERS,
        json={'purpose':data['purpose'],'files':data['files']|data['images']})
    assert saved.status_code==201
    p=saved.json();assert p['execution_profile'] is None
    result=client.post('/api/package-runs',headers=OWNER_HEADERS,json={
        'task_id':task.id,'package_id':p['artifact_id'],'package_checksum':p['checksum'],
        'request_id':str(uuid4()),'confirm_execution':True})
    assert result.status_code==409 and fake.calls==0


def test_image_comparison_does_not_render_base64_diff(client,task_repository):
    first=save(client,task_repository)
    second=save(client,task_repository,payload()|{'images':{'static/image.png':png('blue')}},first['task_id'])
    compared=client.get(f"/api/tasks/{first['task_id']}/workspace-packages/{second['package_id']}/comparison",
        headers=OWNER_HEADERS,params={'base_id':first['package_id'],'path':'static/image.png'}).json()
    assert compared['counts']['modified']==1
    assert compared['detail']['available'] is False and compared['detail']['diff'] is None


@pytest.mark.parametrize('mutation',['oversized','too_many','total','collision','duplicate','huge_dimensions','corrupt_crc'])
def test_media_limits_and_integrity_before_storage(client,task_repository,mutation,monkeypatch):
    data=payload()
    if mutation=='oversized':monkeypatch.setattr(media_packages,'MAX_IMAGE',10)
    elif mutation=='total':monkeypatch.setattr(media_packages,'MAX_MEDIA',10)
    elif mutation=='too_many':data['images']={f'static/p{i}.png':png() for i in range(13)}
    elif mutation=='collision':data['files']['static']='collision'
    elif mutation=='duplicate':data['files']['static/image.png']=png()
    elif mutation=='huge_dimensions':
        output=io.BytesIO();Image.new('RGB',(4097,1)).save(output,format='PNG')
        data['images']['static/image.png']=base64.b64encode(output.getvalue()).decode()
    else:
        raw=bytearray(base64.b64decode(png()));raw[45]^=1
        data['images']['static/image.png']=base64.b64encode(raw).decode()
    task=task_repository.create(title='Synthetic invalid media')
    response=client.post(f'/api/tasks/{task.id}/workspace-media-packages',headers=OWNER_HEADERS,json=data)
    assert response.status_code in (409,422),response.text
    assert client.get(f'/api/tasks/{task.id}/workspace-packages',headers=OWNER_HEADERS).json()['packages']==[]


@pytest.mark.skipif(not os.environ.get('AIC_MEDIA_PACKAGE_BUNDLE'),reason='Explicit headless synthetic PNG browser pilot')
def test_real_media_browser_renders_archive_images(client,task_repository):
    import asyncio
    from scripts.check_media_package import request_from_bundle
    from scripts.compare_local_models import check_idle
    from scripts.upwork_web_case import BROWSER_CASES
    from tests.browser_multifile_probe import check
    check_idle()
    data,_=request_from_bundle(os.environ['AIC_MEDIA_PACKAGE_BUNDLE'])
    body=save(client,task_repository,data)
    async def inspect(evaluate,context,call,session):
        await call('Emulation.setDeviceMetricsOverride',{'width':1440,'height':1000,
            'deviceScaleFactor':1,'mobile':False},session)
        await asyncio.sleep(.2)
        for _ in range(40):
            images=await evaluate("[...document.querySelectorAll('[data-art] img')].map(i=>({width:i.naturalWidth,height:i.naturalHeight}))",context)
            if len(images)==3 and all(i['width']>0 for i in images):break
            await asyncio.sleep(.1)
        assert len(images)==3 and all(i['width']>0 and i['height']>0 for i in images),images
        # Return only equality, never megabytes of data URLs over DevTools.
        expected=['data:image/png;base64,'+v for v in data['images'].values()]
        assert await evaluate("(()=>{const expected="+json.dumps(expected)+";return [...document.querySelectorAll('[data-art] img')].every(i=>expected.includes(i.src))})()",context)
        assert await evaluate("document.querySelector('#visuals').dataset.scenePosition!==undefined",context)
    asyncio.run(check(client,body,OWNER_HEADERS,cases=BROWSER_CASES,expected_color=None,before_activation=inspect))


def test_missing_assets_or_cleanup_cannot_pass(client,task_repository,fake):
    body=save(client,task_repository);fake.assets_ok=False
    result=client.post('/api/package-runs',headers=OWNER_HEADERS,json=body).json()
    assert result['state']=='failed'
    fake.assets_ok=True;fake.cleanup=False
    result=client.post('/api/package-runs',headers=OWNER_HEADERS,json=body|{'request_id':str(uuid4())}).json()
    assert result['state']=='uncertain'


@pytest.mark.skipif(not os.environ.get('AIC_MEDIA_PACKAGE_BUNDLE'),reason='Explicit real synthetic PNG API pilot')
def test_real_media_package_api_release_and_preview(client,task_repository):
    from scripts.check_media_package import request_from_bundle
    from scripts.compare_local_models import check_idle
    check_idle()
    data,_=request_from_bundle(os.environ['AIC_MEDIA_PACKAGE_BUNDLE'])
    body=save(client,task_repository,data)
    run=client.post('/api/package-runs',headers=OWNER_HEADERS,json=body).json()
    assert run['state']=='passed',run
    assert run['result']['cleanup_confirmed'] is True
    base=f"/api/package-runs/{run['id']}"
    assert client.post(base+'/release',headers=OWNER_HEADERS).status_code==409
    assert post(client,run,decision(client,run)).status_code==200
    assert client.post(base+'/release',headers=OWNER_HEADERS).status_code==200
    zipped=client.get(base+'/released.zip',headers=OWNER_HEADERS)
    assert zipped.status_code==200
    with ZipFile(io.BytesIO(zipped.content)) as archive:
        for name,encoded in data['images'].items():assert archive.read('sources/'+name)==base64.b64decode(encoded)
    opened=client.post('/api/package-runs/preview',headers=OWNER_HEADERS,json=body|{'request_id':str(uuid4()),'path':'/'})
    assert opened.status_code==200,opened.text
    assert opened.json()['response']['body']==data['files']['index.html']
    assert len([v for v in opened.json()['assets'].values() if v.startswith('data:image/png;base64,')])==3
    calculated=client.post('/api/package-runs/preview',headers=OWNER_HEADERS,
        json=body|{'request_id':str(uuid4()),'path':'/api/estimate?service=landing&pages=3&rush=1'})
    assert calculated.status_code==200,calculated.text
    assert json.loads(calculated.json()['response']['body'])['total']==2125
    assert task_repository.get_required(body['task_id']).progress==0


@pytest.mark.skipif(not os.environ.get('AIC_MEDIA_PACKAGE_BUNDLE'),reason='Explicit synthetic broken PNG HTTP pilot')
def test_real_runner_rejects_wrong_image_mime(client,task_repository):
    from scripts.check_media_package import request_from_bundle
    from scripts.compare_local_models import check_idle
    check_idle()
    data,_=request_from_bundle(os.environ['AIC_MEDIA_PACKAGE_BUNDLE'])
    assert 'image/png' in data['files']['app.py']
    data['files']['app.py']=data['files']['app.py'].replace('image/png','text/plain')
    body=save(client,task_repository,data)
    run=client.post('/api/package-runs',headers=OWNER_HEADERS,json=body).json()
    assert run['state']=='failed' and run['result']['cleanup_confirmed'] is True,run
    assert 'Missing/changed public file' in run['result']['log']
    assert client.get(f"/api/package-runs/{run['id']}/candidate.zip",headers=OWNER_HEADERS).status_code==409
