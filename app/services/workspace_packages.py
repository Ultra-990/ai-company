"""Immutable source packages. No execution, extraction or host filesystem access."""
from __future__ import annotations

import io
import json
import re
from datetime import timezone
from hashlib import sha256
from zipfile import ZIP_STORED, ZipFile, ZipInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.artifact import Artifact, ArtifactType
from app.models.audit import AuditEvent
from app.models.task import Task
from app.services.application_layout import execution_profile

PACKAGE_NAME = "organization-os.workspace.v1"
MEDIA_PACKAGE_NAME = 'organization-os.workspace-media.v1'
MAX_FILES = 100
MAX_FILE_BYTES = 256 * 1024
MAX_TOTAL_BYTES = 1024 * 1024


class PackageNotFound(LookupError):
    pass


class PackageIntegrityError(RuntimeError):
    pass


def canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def validate_files(files: dict[str, str]) -> list[dict]:
    if not isinstance(files, dict) or not 1 <= len(files) <= MAX_FILES:
        raise ValueError("Paczka wymaga od 1 do 100 plików.")
    result = []
    total = 0
    folded = set()
    for path, content in sorted(files.items()):
        if not isinstance(path, str) or not re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_./-]{0,199}", path):
            raise ValueError("Niedozwolona ścieżka pliku.")
        parts = path.split("/")
        if any(not part or part.startswith(".") for part in parts):
            raise ValueError("Ścieżki względne nie mogą zawierać ukrytych lub pustych segmentów.")
        key = path.casefold()
        if key in folded:
            raise ValueError("Ścieżki nie mogą różnić się tylko wielkością liter.")
        folded.add(key)
        if not isinstance(content, str) or "\x00" in content:
            raise ValueError("Dozwolone są wyłącznie tekstowe pliki bez bajtów NUL.")
        try:
            raw = content.encode("utf-8")
        except UnicodeEncodeError as exc:
            raise ValueError("Treść musi być poprawnym UTF-8.") from exc
        total += len(raw)
        if len(raw) > MAX_FILE_BYTES or total > MAX_TOTAL_BYTES:
            raise ValueError("Limit: 256 KiB na plik i 1 MiB na paczkę.")
        result.append(dict(path=path, content=content, size_bytes=len(raw), sha256=sha256(raw).hexdigest()))
    for key in folded:
        parts = key.split("/")
        if any("/".join(parts[:i]) in folded for i in range(1, len(parts))):
            raise ValueError("Plik nie może być jednocześnie katalogiem.")
    return result


def create_package(session: Session, task_id: int, files: dict[str, str], purpose: str, *, commit: bool = True) -> Artifact:
    task = session.get(Task, task_id)
    if task is None:
        raise PackageNotFound("Nie znaleziono zadania.")
    if not purpose.strip() or len(purpose) > 2000:
        raise ValueError("Podaj cel paczki (1–2000 znaków).")
    entries = validate_files(files)
    content = canonical_json(dict(schema=PACKAGE_NAME, task_id=task_id, purpose=purpose.strip(), files=entries))
    artifact = Artifact(
        task_id=task.id, project_id=task.project_id, plan_id=task.plan_id,
        artifact_type=ArtifactType.SOURCE_CODE, name=PACKAGE_NAME,
        content=content, checksum=sha256(content.encode()).hexdigest(), created_by="owner",
        description=purpose.strip(),
    )
    session.add(artifact)
    session.flush()
    session.add(AuditEvent(
        event_type="workspace_package", operation="create", decision="stored",
        allowed=True, reason=f"owner; task={task_id}; artifact={artifact.id}; sha256={artifact.checksum}",
    ))
    if commit:
        session.commit()
    return artifact


def read_package(session: Session, task_id: int, artifact_id: int) -> tuple[Artifact, dict]:
    artifact = session.scalar(select(Artifact).where(
        Artifact.id == artifact_id, Artifact.task_id == task_id,
        Artifact.name.in_([PACKAGE_NAME, MEDIA_PACKAGE_NAME]), Artifact.artifact_type == ArtifactType.SOURCE_CODE,
    ))
    if artifact is None:
        raise PackageNotFound("Nie znaleziono paczki dla tego zadania.")
    content = artifact.content or ""
    if sha256(content.encode()).hexdigest() != artifact.checksum:
        raise PackageIntegrityError("Niezgodna suma kontrolna paczki.")
    try:
        payload = json.loads(content)
        entries = payload["files"]
        files = {entry["path"]: entry["content"] for entry in entries}
        validator = validate_files
        if artifact.name == MEDIA_PACKAGE_NAME:
            from app.services.media_packages import validate
            validator = validate
        if (payload["schema"] != artifact.name or payload["task_id"] != task_id
                or len(files) != len(entries) or validator(files) != entries):
            raise ValueError("Niezgodny manifest.")
    except (ValueError, TypeError, KeyError, AttributeError) as exc:
        raise PackageIntegrityError("Nieprawidłowy manifest paczki.") from exc
    return artifact, payload


def package_summary(artifact: Artifact, payload: dict) -> dict:
    from app.services.execution_profiles import capabilities
    entries = payload["files"]
    profile = execution_profile({entry['path']:entry['content'] for entry in entries},
                                media=payload['schema'] == MEDIA_PACKAGE_NAME)
    created_at = artifact.created_at
    # SQLite returns naive datetimes; this model always writes UTC.
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    return dict(
        artifact_id=artifact.id, task_id=artifact.task_id, checksum=artifact.checksum,
        created_at=created_at.astimezone(timezone.utc).isoformat(), purpose=payload["purpose"],
        file_count=len(entries), total_bytes=sum(entry["size_bytes"] for entry in entries),
        files=[{k: v for k, v in entry.items() if k != "content"} for entry in entries],
        execution_status="not_executed", review_status="not_reviewed",
        execution_profile=profile, capabilities=capabilities(profile),
    )


def package_zip(payload: dict) -> bytes:
    """Deterministic, uncompressed archive; never extracts or executes files."""
    output = io.BytesIO()
    with ZipFile(output, "w", compression=ZIP_STORED) as archive:
        for entry in payload["files"]:
            info = ZipInfo(entry["path"], date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            from app.services.media_packages import bytes_of
            archive.writestr(info, bytes_of(entry))
    return output.getvalue()
