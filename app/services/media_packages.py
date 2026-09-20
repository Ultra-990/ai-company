"""Immutable Python sources plus bounded PNG data; no execution or filesystem input."""
import base64
import binascii
from hashlib import sha256
import io
import re

from PIL import Image

NAME = 'organization-os.workspace-media.v1'
PROFILE = 'python-web-media-v1'
MAX_IMAGE = 4_000_000
MAX_MEDIA = 12_000_000


def is_image(path):
    return isinstance(path, str) and path.startswith('static/') and path.endswith('.png')


def image_bytes(content):
    if not isinstance(content, str) or len(content) > (MAX_IMAGE + 2) // 3 * 4:
        raise ValueError('PNG przekracza limit 4 MB.')
    try:
        raw = base64.b64decode(content, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise ValueError('Obraz musi mieć poprawne kodowanie base64.') from exc
    if not raw or len(raw) > MAX_IMAGE or base64.b64encode(raw).decode() != content:
        raise ValueError('Nieprawidłowy rozmiar lub kodowanie PNG.')
    try:
        with Image.open(io.BytesIO(raw)) as image:
            if image.format != 'PNG' or image.width > 4096 or image.height > 4096 or getattr(image, 'n_frames', 1) != 1:
                raise ValueError('Dozwolone są pojedyncze PNG do 4096×4096.')
            image.verify()
    except (OSError, SyntaxError, Image.DecompressionBombError) as exc:
        raise ValueError('Nieprawidłowy PNG.') from exc
    return raw


def validate(files):
    from app.services.workspace_packages import validate_files
    from app.services.multifile_profile import require_sources
    if not isinstance(files, dict) or not 8 <= len(files) <= 100:
        raise ValueError('Paczka z mediami wymaga źródeł Python i PNG.')
    images = {k: v for k, v in files.items() if is_image(k)}
    sources = {k: v for k, v in files.items() if not is_image(k)}
    if not 1 <= len(images) <= 12:
        raise ValueError('Dozwolone jest od 1 do 12 obrazów PNG.')
    # Validate every path and collision together without changing text-package limits.
    validate_files({name: 'path check' for name in files})
    require_sources(sources)
    entries = validate_files(sources)
    total = 0
    for name, content in sorted(images.items()):
        if not re.fullmatch(r'static/(?:[A-Za-z0-9_-]+/)*[A-Za-z0-9_-]+\.png', name):
            raise ValueError('PNG musi mieć prostą ścieżkę pod static/.')
        raw = image_bytes(content)
        total += len(raw)
        if total > MAX_MEDIA:
            raise ValueError('Łączny limit obrazów wynosi 12 MB.')
        entries.append(dict(path=name, content=content, encoding='base64', media_type='image/png',
                            size_bytes=len(raw), sha256=sha256(raw).hexdigest()))
    return sorted(entries, key=lambda e: e['path'])


def bytes_of(entry):
    return base64.b64decode(entry['content'], validate=True) if entry.get('encoding') == 'base64' else entry['content'].encode()


def create(session, task_id, files, images, purpose):
    from app.models.artifact import Artifact, ArtifactType
    from app.models.audit import AuditEvent
    from app.models.task import Task
    from app.services.workspace_packages import canonical_json, PackageNotFound
    task = session.get(Task, task_id)
    if task is None:
        raise PackageNotFound('Nie znaleziono zadania.')
    if set(files) & set(images) or any(not is_image(k) for k in images) or any(is_image(k) for k in files):
        raise ValueError('Źródła i obrazy muszą być rozdzielone i mieć unikalne ścieżki.')
    if not purpose.strip() or len(purpose) > 2000:
        raise ValueError('Podaj cel paczki (1–2000 znaków).')
    entries = validate(files | images)
    raw = canonical_json(dict(schema=NAME, task_id=task_id, purpose=purpose.strip(), files=entries))
    from sqlalchemy import select
    digest = sha256(raw.encode()).hexdigest()
    existing = session.scalar(select(Artifact).where(Artifact.task_id==task_id,
        Artifact.name==NAME, Artifact.artifact_type==ArtifactType.SOURCE_CODE, Artifact.checksum==digest))
    if existing:
        if existing.content != raw:
            raise ValueError('Niespójny zapis wcześniejszej wersji.')
        return existing
    artifact = Artifact(task_id=task_id, project_id=task.project_id, plan_id=task.plan_id,
        name=NAME, artifact_type=ArtifactType.SOURCE_CODE, content=raw,
        checksum=digest, created_by='owner', description=purpose.strip())
    session.add(artifact); session.flush()
    session.add(AuditEvent(event_type='workspace_package', operation='create', allowed=True,
        decision='stored', reason=f'owner; task={task_id}; artifact={artifact.id}; media=true; sha256={artifact.checksum}'))
    return artifact
