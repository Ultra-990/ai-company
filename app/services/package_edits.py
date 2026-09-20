"""Immutable, replay-safe multi-file edits. Source is data, never imported."""
import json
from hashlib import sha256

from sqlalchemy import select

from app.models.artifact import Artifact, ArtifactType
from app.services.workspace_packages import (
    PackageIntegrityError, canonical_json, create_package, package_summary,
    read_package, validate_files,
)

SCHEMA = 'organization-os.package-edit.v1'


def protected_test(path):
    parts = path.lower().split('/')
    name = parts[-1]
    return (name in {'test.py', 'tests.py'} or any(p in {'test', 'tests', '__tests__'} for p in parts[:-1])
            or name.startswith(('test_', 'conftest.')) or name.endswith('_test.py')
            or '.test.' in name or '.spec.' in name)


def assemble(base, changes, removals):
    if not changes and not removals:
        raise ValueError('Podaj przynajmniej jedną zmianę.')
    if len(set(removals)) != len(removals) or set(changes) & set(removals):
        raise ValueError('Plik nie może być jednocześnie zmieniany i usuwany; usunięcia muszą być unikalne.')
    if changes:
        validate_files(changes)
    for path in set(changes) | set(removals):
        if path in base and protected_test(path):
            raise ValueError('Istniejące testy są chronione. Dodaj nowe przypadki w osobnym pliku; nie osłabiaj starego testu.')
    if set(removals) - set(base):
        raise ValueError('Nie można usunąć pliku, którego nie ma w wersji bazowej.')
    merged = {path: source for path, source in base.items() if path not in removals}
    merged.update(changes)
    validate_files(merged)
    if merged == base:
        raise ValueError('Brak rzeczywistych zmian. Nie utworzono pustej wersji.')
    return merged


def revise(session, task_id, package_id, *, request_id, base_checksum, changes, removals, purpose):
    """Caller holds BEGIN IMMEDIATE; source version + receipt + audit are atomic."""
    base, manifest = read_package(session, task_id, package_id)
    from app.services.media_packages import NAME as MEDIA_NAME
    if manifest['schema'] == MEDIA_NAME:
        raise ValueError('Dla paczki z PNG zapisz nową kompletną wersję przez import źródeł i obrazów. Nie edytuj obrazów jako tekstu.')
    if base.checksum != base_checksum:
        raise ValueError('Wersja bazowa ma inną sumę. Wczytaj właściwą paczkę.')
    payload = dict(task_id=task_id, package_id=package_id, base_checksum=base_checksum,
                   changes=changes, removals=sorted(removals), purpose=purpose.strip())
    signature = sha256(canonical_json(payload).encode()).hexdigest()
    name = SCHEMA + ':' + request_id
    receipt = session.scalar(select(Artifact).where(Artifact.name == name))
    if receipt:
        if (receipt.task_id != task_id or receipt.artifact_type != ArtifactType.REPORT
                or not receipt.content or sha256(receipt.content.encode()).hexdigest() != receipt.checksum):
            raise PackageIntegrityError('Niespójny zapis wcześniejszej zmiany.')
        try:
            saved = json.loads(receipt.content)
            if (saved['schema'] != SCHEMA or saved['input_hash'] != signature
                    or saved['base_id'] != package_id or saved['base_checksum'] != base_checksum):
                raise ValueError('Ten identyfikator zapisu wskazuje inne zmiany.')
            artifact, content = read_package(session, task_id, saved['package_id'])
            if artifact.checksum != saved['package_checksum']:
                raise PackageIntegrityError('Niezgodna suma nowej wersji.')
        except (KeyError, TypeError, json.JSONDecodeError) as exc:
            raise PackageIntegrityError('Nieprawidłowe potwierdzenie zmiany.') from exc
    else:
        old = {entry['path']: entry['content'] for entry in manifest['files']}
        files = assemble(old, changes, removals)
        artifact = create_package(session, task_id, files, purpose, commit=False)
        _, content = read_package(session, task_id, artifact.id)
        saved = dict(schema=SCHEMA, input_hash=signature, base_id=package_id, base_checksum=base_checksum,
                     package_id=artifact.id, package_checksum=artifact.checksum,
                     changed_paths=sorted(path for path in changes if old.get(path) != changes[path]),
                     removed_paths=sorted(removals))
        raw = canonical_json(saved)
        receipt = Artifact(task_id=task_id, project_id=artifact.project_id, plan_id=artifact.plan_id,
                           artifact_type=ArtifactType.REPORT, name=name, content=raw,
                           checksum=sha256(raw.encode()).hexdigest(), created_by='owner',
                           description='Zmiana źródeł na podstawie wskazanej wersji. Bez wykonania, testów i odbioru.')
        session.add(receipt)
        session.flush()
    return dict(package=package_summary(artifact, content), base_id=package_id,
                base_checksum=base_checksum, receipt_id=receipt.id,
                changed_paths=saved['changed_paths'], removed_paths=saved['removed_paths'],
                executed=False, tests_inherited=False, accepted=False)
