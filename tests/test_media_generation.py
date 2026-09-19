import json
from io import BytesIO
from uuid import uuid4
from types import SimpleNamespace
import pytest
from PIL import Image, ImageDraw
from sqlalchemy import select, func
from app.main import app
from app.api.media_generation import get_provider
from app.models.artifact import Artifact
from app.models.media_generation import MediaGeneration
from app.models.local_inference import LocalInference
from app.services import media_generation as service
from app.services.comfyui_provider import ComfyProvider, ComfyFailure, ComfyRejected, graph
from scripts.check_comfyui_generation import workflow as smoke_workflow, PROMPT
from tests.conftest import OWNER_HEADERS, WORKER_HEADERS


def png():
    image = Image.new('RGB', (768, 512), 'white')
    ImageDraw.Draw(image).rectangle((100, 100, 500, 400), fill='blue')
    out = BytesIO(); image.save(out, format='PNG'); return out.getvalue()


class Provider:
    def __init__(self):
        self.calls = 0; self.jobs = {}; self.fail_prepare = False; self.fail_submit = False
        self.ready = True; self.invalid = False; self.wrong_binding = False; self.error = False
    def prepare(self):
        if self.fail_prepare: raise ComfyFailure('busy')
    def submit(self, prompt_id, workflow):
        self.calls += 1; self.jobs[prompt_id] = workflow
        if self.fail_submit: raise TimeoutError()
    def history(self, prompt_id):
        if not self.ready: return None
        workflow = self.jobs[prompt_id]
        return {'prompt': [0, 'wrong' if self.wrong_binding else prompt_id, workflow],
            'status': {'status_str': 'error' if self.error else 'success', 'completed': not self.error},
            'outputs': {'10': {'images': [{'filename': prompt_id + '_00001_.png', 'subfolder': 'AI-Company', 'type': 'output'}]}}}
    def image(self, prompt_id, entry):
        return b'not PNG' if self.invalid else png()


@pytest.fixture
def provider(monkeypatch):
    p = Provider(); app.dependency_overrides[get_provider] = lambda: p
    monkeypatch.setattr(service, 'load_settings', lambda: SimpleNamespace(safety=SimpleNamespace(emergency_stop=False)))
    yield p
    app.dependency_overrides.pop(get_provider, None)


def payload(**extra):
    return dict(request_id=str(uuid4()), prompt='A cobalt sphere on an ivory pedestal', seed=42, confirm=True) | extra


def url(task, job=None):
    return f'/api/tasks/{task.id}/images' + (f'/{job}' if job else '')


def start(client, task, body=None):
    r = client.post(url(task), headers=OWNER_HEADERS, json=body or payload())
    assert r.status_code == 200, r.text
    return r.json()


def finish(client, task, job):
    r = client.post(url(task, job['id']) + '/refresh', headers=OWNER_HEADERS)
    assert r.status_code == 200, r.text
    return r.json()


def test_same_profile_as_real_smoke():
    assert graph(PROMPT, 20260913, 'local-smoke') == smoke_workflow()


def test_generate_persist_download_review_without_task_completion(client, approved_task, task_repository, provider):
    before = task_repository.get_required(approved_task.id)
    job = start(client, approved_task); assert job['state'] == 'queued'
    done = finish(client, approved_task, job); assert done['state'] == 'succeeded'
    root = url(approved_task, job['id'])
    report = client.get(root + '/report', headers=OWNER_HEADERS).json()
    assert report['checks']['metadata_removed'] and report['workflow_checksum'] == job['workflow_checksum']
    assert not report['visual_reviewed'] and not report['published'] and 'image_base64' not in report
    r = client.get(root + '/download', headers=OWNER_HEADERS)
    assert r.status_code == 200 and r.headers['content-type'] == 'image/png'
    assert r.headers['cache-control'] == 'no-store'
    with Image.open(BytesIO(r.content)) as image: assert image.size == (768, 512) and not image.info
    review = dict(checksum=report['artifact_checksum'], decision='accepted', reason='Sprawdzono obraz i brief.')
    r = client.post(root + '/review', headers=OWNER_HEADERS, json=review)
    assert r.status_code == 200 and r.json()['review'] == 'accepted'
    assert client.post(root + '/review', headers=OWNER_HEADERS, json=review).status_code == 200
    assert client.post(root + '/review', headers=OWNER_HEADERS, json=review | {'decision':'rejected'}).status_code == 409
    assert finish(client, approved_task, job)['artifact_id'] == done['artifact_id']
    after = task_repository.get_required(approved_task.id)
    assert (before.status, before.progress, before.approval_status) == (after.status, after.progress, after.approval_status)
    assert provider.calls == 1
    with task_repository._session_factory() as s:
        assert s.scalar(select(func.count()).select_from(Artifact).where(Artifact.name == service.ARTIFACT_NAME)) == 1


def test_idempotency_and_timeout_recovery_never_resubmits(client, approved_task, provider):
    provider.fail_submit = True
    body = payload(); job = start(client, approved_task, body)
    assert job['state'] == 'uncertain'
    assert start(client, approved_task, body)['id'] == job['id']
    assert client.post(url(approved_task), headers=OWNER_HEADERS, json=body | {'seed': 43}).status_code == 409
    assert client.post(url(approved_task), headers=OWNER_HEADERS, json=payload()).status_code == 409
    provider.ready = False
    assert finish(client, approved_task, job)['state'] == 'uncertain'
    provider.ready = True
    assert finish(client, approved_task, job)['state'] == 'succeeded'
    assert provider.calls == 1


@pytest.mark.parametrize('field', ['invalid', 'wrong_binding'])
def test_invalid_output_holds_slot_without_artifact(client, approved_task, provider, field):
    setattr(provider, field, True)
    job = start(client, approved_task)
    result = finish(client, approved_task, job)
    assert result['state'] == 'uncertain' and result['artifact_id'] is None
    assert client.get(url(approved_task, job['id']) + '/download', headers=OWNER_HEADERS).status_code == 404


def test_preflight_and_execution_failures_recorded(client, approved_task, provider):
    provider.fail_prepare = True
    assert start(client, approved_task)['state'] == 'failed' and provider.calls == 0
    provider.fail_prepare = False; provider.error = True
    job = start(client, approved_task)
    assert finish(client, approved_task, job)['state'] == 'failed'


def test_explicit_graph_rejection_does_not_hold_slot(client, approved_task, provider, monkeypatch):
    def reject(*args): raise ComfyRejected('comfy_graph_rejected')
    monkeypatch.setattr(provider, 'submit', reject)
    result = start(client, approved_task)
    assert result['state'] == 'failed' and result['error_code'] == 'comfy_graph_rejected'
    assert result['finished_at'] is not None


def test_preflight_rejects_missing_weights_before_submit(monkeypatch):
    monkeypatch.setattr('app.services.local_ollama.ensure_idle', lambda: None)
    provider = ComfyProvider()
    def response(path):
        if path == '/queue': return {'queue_running':[], 'queue_pending':[]}
        if path == '/system_stats': return {'system':{'comfyui_version':'0.35.0'}}
        return {'UNETLoader':{'input':{'required':{'unet_name':[[]]}}}}
    monkeypatch.setattr(provider, 'request', response)
    with pytest.raises(ComfyFailure, match='comfy_models_missing'): provider.prepare()


def test_context_change_forbids_acceptance(client, approved_task, task_repository, provider):
    job = start(client, approved_task)
    with task_repository._session_factory() as s:
        from app.models.task import Task
        s.get(Task, approved_task.id).title = 'Zmieniony zakres'; s.commit()
    finish(client, approved_task, job)
    root = url(approved_task, job['id'])
    report = client.get(root + '/report', headers=OWNER_HEADERS).json()
    assert report['context_changed']
    assert client.post(root + '/review', headers=OWNER_HEADERS, json=dict(checksum=report['artifact_checksum'], decision='accepted', reason='Sprawdzono wynik')).status_code == 409


def test_approval_emergency_stop_and_rbac(client, approved_task, task_repository, provider, monkeypatch):
    task = task_repository.create(title='Niezaakceptowane')
    assert client.post(url(task), headers=OWNER_HEADERS, json=payload()).status_code == 409
    for headers, status in (({}, 401), (WORKER_HEADERS, 403)):
        assert client.post(url(approved_task), headers=headers, json=payload()).status_code == status
        for suffix in ('', '/1/report', '/1/download'):
            assert client.get(url(approved_task) + suffix, headers=headers).status_code == status
        assert client.post(url(approved_task, 1)+'/refresh', headers=headers).status_code == status
    monkeypatch.setattr(service, 'load_settings', lambda: SimpleNamespace(safety=SimpleNamespace(emergency_stop=True)))
    assert client.post(url(approved_task), headers=OWNER_HEADERS, json=payload()).status_code == 409
    assert provider.calls == 0


@pytest.mark.parametrize('extra', [{'workflow':{}}, {'url':'http://external'}, {'seed':True}, {'seed':-1}, {'prompt':'  '}, {'prompt':'x'*2001}, {'confirm':False}])
def test_no_arbitrary_workflow_or_limits(client, approved_task, provider, extra):
    assert client.post(url(approved_task), headers=OWNER_HEADERS, json=payload(**extra)).status_code == 422
    assert provider.calls == 0


def test_cross_task_and_tamper_protection(client, approved_task, task_repository, provider):
    job = start(client, approved_task); done = finish(client, approved_task, job)
    other = task_repository.create(title='Inne')
    for suffix in ('/download','/report'):
        assert client.get(url(other, job['id'])+suffix, headers=OWNER_HEADERS).status_code == 404
    with task_repository._session_factory() as s:
        s.get(Artifact, done['artifact_id']).content += ' '; s.commit()
    assert client.get(url(approved_task, job['id'])+'/download', headers=OWNER_HEADERS).status_code == 409


def test_submitting_crash_can_recover_known_prompt(client, approved_task, task_repository, provider):
    job = start(client, approved_task)
    with task_repository._session_factory() as s:
        s.get(MediaGeneration, job['id']).state = 'submitting'; s.commit()
    assert finish(client, approved_task, job)['state'] == 'succeeded'


@pytest.mark.parametrize('entry', [
    {'filename':'../secret.png','subfolder':'AI-Company','type':'output'},
    {'filename':'x_00001_.png','subfolder':'../','type':'output'},
    {'filename':'x_00001_.png','subfolder':'AI-Company','type':'input'},
])
def test_provider_never_reads_arbitrary_paths(entry):
    with pytest.raises(ComfyFailure): ComfyProvider().image(str(uuid4()), entry)


def test_media_page_and_discovery(client):
    r = client.get('/os/media')
    assert r.status_code == 200 and 'Grafika projektowa' in r.text
    assert "img-src 'self' blob:" in r.headers['content-security-policy']
    assert client.get('/os/legacy').text != r.text
    assert '/os/media' in client.get('/static/organization-os/navigation-search.js').text


def test_additive_migration_repeatable(tmp_path):
    from sqlalchemy import create_engine, text, inspect
    from app.db.migrations import migrate_media_generation_schema
    engine = create_engine(f'sqlite:///{tmp_path / "old-media.db"}')
    with engine.begin() as conn:
        conn.execute(text('CREATE TABLE media_generations (id INTEGER PRIMARY KEY)'))
        conn.execute(text('INSERT INTO media_generations (id) VALUES (7)'))
    migrate_media_generation_schema(engine)
    migrate_media_generation_schema(engine)
    assert {'project_id', 'plan_id'} <= {c['name'] for c in inspect(engine).get_columns('media_generations')}
    with engine.connect() as conn:
        assert conn.execute(text('SELECT id FROM media_generations')).scalar() == 7
    engine.dispose()
