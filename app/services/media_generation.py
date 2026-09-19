"""One durable image slot; immutable result artifacts, explicit owner review."""
import base64
from hashlib import sha256
from io import BytesIO
import json
from uuid import uuid4

from PIL import Image, ImageStat
from sqlalchemy import select, text
from app.core.config import load_settings
from app.models.artifact import Artifact, ArtifactType
from app.models.audit import AuditEvent
from app.models.local_inference import LocalInference
from app.models.media_generation import MediaGeneration
from app.models.task import Task, TaskStatus, ApprovalStatus, utc_now
from app.services.comfyui_provider import graph, PROFILE, MAX_IMAGE, ComfyRejected

ACTIVE = ('submitting', 'queued', 'uncertain')
ARTIFACT_NAME = 'organization-os.generated-image.v1'


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def digest(value):
    return sha256(canonical(value).encode()).hexdigest()


def assert_enabled():
    if load_settings().safety.emergency_stop:
        raise ValueError('Emergency Stop: nie uruchomiono generatora.')


def busy(session):
    return session.scalar(select(MediaGeneration.id).where(MediaGeneration.state.in_(ACTIVE)).limit(1)) is not None


def context(task):
    return digest({k: getattr(task, k) for k in ('id', 'title', 'description', 'project_id',
        'plan_id', 'status', 'approval_status', 'assigned_agent')})


def eligible(session, task_id):
    task = session.get(Task, task_id)
    if task is None:
        raise LookupError('Nie znaleziono zadania.')
    if task.approval_status != ApprovalStatus.APPROVED or task.status not in (TaskStatus.PENDING, TaskStatus.IN_PROGRESS):
        raise ValueError('Najpierw zatwierdź zadanie do pracy. Zadanie nie może być zablokowane ani zamknięte.')
    return task


def summary(run):
    return {k: getattr(run, k) for k in ('id', 'request_id', 'task_id', 'prompt_id', 'state',
        'inputs', 'workflow_checksum', 'artifact_id', 'error_code', 'review', 'review_reason',
        'created_at', 'finished_at')} | {'task_completed': False, 'published': False}


def audit(session, run, operation):
    session.add(AuditEvent(event_type='media_generation', operation=operation, decision=run.state,
        allowed=True, reason=f'owner; job={run.id}; task={run.task_id}; review={run.review}; publication=false'))


def get_run(session, task_id, job_id):
    run = session.scalar(select(MediaGeneration).where(MediaGeneration.id == job_id, MediaGeneration.task_id == task_id))
    if run is None:
        raise LookupError('Nie znaleziono generowania dla tego zadania.')
    return run


def submit(session, task_id, request_id, prompt, seed, provider):
    assert_enabled()
    inputs = {'profile': PROFILE, 'prompt': prompt, 'seed': seed, 'width': 768, 'height': 512, 'steps': 8}
    # SQLite write reservation coordinates with local_inference.execute as well.
    session.execute(text('BEGIN IMMEDIATE'))
    existing = session.scalar(select(MediaGeneration).where(MediaGeneration.request_id == request_id))
    if existing:
        if existing.task_id != task_id or existing.inputs != inputs:
            raise ValueError('Identyfikator żądania został już użyty z inną treścią.')
        result = summary(existing); session.rollback(); return result
    task = eligible(session, task_id)
    if busy(session) or session.scalar(select(LocalInference.id).where(LocalInference.state.in_(['running', 'uncertain'])).limit(1)):
        raise ValueError('Slot lokalnego modelu jest zajęty lub wymaga sprawdzenia.')
    prompt_id = str(uuid4())
    workflow = graph(prompt, seed, 'AI-Company/' + prompt_id)
    run = MediaGeneration(request_id=request_id, task_id=task_id, project_id=task.project_id,
        plan_id=task.plan_id, prompt_id=prompt_id,
        state='submitting', inputs=inputs, context_checksum=context(task), workflow_checksum=digest(workflow))
    session.add(run); session.flush(); audit(session, run, 'reserve'); session.commit()
    # Durable reservation BEFORE any HTTP, never hold DB write lock during inference.
    try:
        provider.prepare()
        assert_enabled()
        session.expire_all()
        if context(eligible(session, task_id)) != run.context_checksum:
            raise ValueError('context_changed')
    except Exception as exc:
        known = {'comfy_busy', 'ollama_busy', 'comfy_version_changed', 'comfy_unavailable_or_invalid', 'comfy_models_missing'}
        run.state = 'failed'; run.error_code = str(exc) if str(exc) in known else 'preflight_failed'; run.finished_at = utc_now()
        audit(session, run, 'finish'); session.commit(); return summary(run)
    try:
        provider.submit(prompt_id, workflow)
        state, error = 'queued', None
    except ComfyRejected:
        state, error = 'failed', 'comfy_graph_rejected'
    except Exception:
        # The request may have reached ComfyUI. Keep the slot; do not POST twice.
        state, error = 'uncertain', 'submission_uncertain'
    session.rollback()
    session.execute(text('BEGIN IMMEDIATE')); session.expire_all()
    run = get_run(session, task_id, run.id)
    if run.state == 'submitting':
        run.state, run.error_code = state, error
        if state == 'failed': run.finished_at = utc_now()
    audit(session, run, 'submit'); session.commit()
    return summary(run)


def validate_image(raw):
    if not isinstance(raw, bytes) or not 0 < len(raw) <= MAX_IMAGE:
        raise ValueError('image_size')
    with Image.open(BytesIO(raw)) as img:
        if img.format != 'PNG' or img.size != (768, 512) or getattr(img, 'n_frames', 1) != 1:
            raise ValueError('image_format')
        img.load()
        rgb = img.convert('RGB')
        if max(ImageStat.Stat(rgb).stddev) < 1:
            raise ValueError('image_uniform')
        # Remove embedded ComfyUI prompt/workflow metadata from downloadable image.
        clean = BytesIO(); rgb.save(clean, format='PNG')
    result = clean.getvalue()
    if len(result) > MAX_IMAGE:
        raise ValueError('image_size')
    return result


def refresh(session, task_id, job_id, provider):
    run = get_run(session, task_id, job_id)
    if run.state not in ACTIVE:
        return summary(run)
    expected = graph(run.inputs['prompt'], run.inputs['seed'], 'AI-Company/' + run.prompt_id)
    try:
        history = provider.history(run.prompt_id)
        if history is None:
            return summary(run)  # Absent history is NOT proof of failure/idle.
        submitted = history['prompt']
        if submitted[1] != run.prompt_id or digest(submitted[2]) != run.workflow_checksum or digest(expected) != run.workflow_checksum:
            raise ValueError('history_binding')
        status = history['status']
        if status.get('status_str') == 'error':
            outcome, error, result = 'failed', 'comfy_execution_failed', None
        elif status.get('status_str') == 'success' and status.get('completed') is True:
            try:
                entries = history['outputs']['10']['images']
                if len(entries) != 1:
                    raise ValueError('image_count')
                raw = provider.image(run.prompt_id, entries[0])
                image = validate_image(raw)
                result = {'profile': PROFILE, 'task_id': task_id, 'job_id': job_id,
                    'prompt_id': run.prompt_id, 'inputs': run.inputs, 'workflow': expected,
                    'workflow_checksum': run.workflow_checksum, 'source_sha256': sha256(raw).hexdigest(),
                    'image_sha256': sha256(image).hexdigest(), 'image_base64': base64.b64encode(image).decode(),
                    'checks': {'png_dimensions': True, 'nonuniform': True, 'metadata_removed': True},
                    'visual_reviewed': False, 'client_accepted': False, 'published': False}
                outcome, error = 'succeeded', None
            except Exception:
                # Comfy finished, but retrieval may succeed on next explicit refresh.
                outcome, error, result = 'uncertain', 'image_retrieval_or_validation_failed', None
        else:
            return summary(run)
    except Exception:
        outcome, error, result = 'uncertain', 'history_unavailable_or_invalid', None
    session.rollback()
    session.execute(text('BEGIN IMMEDIATE')); session.expire_all()
    run = get_run(session, task_id, job_id)
    if run.state not in ACTIVE:
        data = summary(run); session.rollback(); return data
    if result is not None:
        task = session.get(Task, task_id)
        result['context_changed'] = task is None or context(task) != run.context_checksum
        content = canonical(result)
        artifact = Artifact(task_id=task_id, project_id=run.project_id, plan_id=run.plan_id,
            artifact_type=ArtifactType.OTHER, name=ARTIFACT_NAME, created_by='local-comfyui',
            uri=f'media-job:{job_id}', content=content, checksum=sha256(content.encode()).hexdigest(),
            description='Grafika lokalna — kontrola techniczna, odbiór wizualny wymagany; bez publikacji.')
        session.add(artifact); session.flush(); run.artifact_id = artifact.id
    run.state, run.error_code = outcome, error
    if outcome in ('failed', 'succeeded'):
        run.finished_at = utc_now()
    audit(session, run, 'refresh'); session.commit()
    return summary(run)


def read_result(session, task_id, job_id):
    run = get_run(session, task_id, job_id)
    artifact = session.get(Artifact, run.artifact_id) if run.artifact_id else None
    if artifact is None:
        raise LookupError('Obraz nie jest jeszcze zapisany.')
    try:
        if (artifact.task_id != task_id or artifact.name != ARTIFACT_NAME or artifact.uri != f'media-job:{job_id}'
                or sha256((artifact.content or '').encode()).hexdigest() != artifact.checksum):
            raise ValueError()
        result = json.loads(artifact.content)
        image = base64.b64decode(result['image_base64'], validate=True)
        if (result['job_id'] != job_id or result['task_id'] != task_id or result['prompt_id'] != run.prompt_id
                or result['workflow_checksum'] != run.workflow_checksum
                or digest(result['workflow']) != run.workflow_checksum or sha256(image).hexdigest() != result['image_sha256']):
            raise ValueError()
    except (ValueError, KeyError, TypeError) as exc:
        raise ValueError('Naruszona integralność obrazu lub raportu.') from exc
    return {k: v for k, v in result.items() if k != 'image_base64'} | {'artifact_checksum': artifact.checksum}, image


def review(session, task_id, job_id, checksum, decision, reason):
    session.execute(text('BEGIN IMMEDIATE'))
    run = get_run(session, task_id, job_id)
    result, _ = read_result(session, task_id, job_id)
    if result['artifact_checksum'] != checksum:
        raise ValueError('Wersja wyniku zmieniła się. Wczytaj ponownie.')
    if run.review != 'pending':
        if run.review == decision and run.review_reason == reason:
            data = summary(run); session.rollback(); return data
        raise ValueError('Ten obraz ma już decyzję właściciela.')
    if decision == 'accepted' and context(eligible(session, task_id)) != run.context_checksum:
        raise ValueError('Kontekst zadania zmienił się. Wygeneruj nową wersję dla aktualnego zakresu.')
    run.review, run.review_reason = decision, reason
    audit(session, run, 'review'); session.commit()
    return summary(run)
