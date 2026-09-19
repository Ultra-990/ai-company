"""Owner-only source package storage, deliberately without a run endpoint."""
from __future__ import annotations
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.api.auth import require_owner
from app.api.organization_os import get_organization_session
from app.models.artifact import Artifact, ArtifactType
from app.models.task import Task
from app.services.package_edits import revise, protected_test
from app.services.workspace_packages import (
    PACKAGE_NAME, PackageIntegrityError, PackageNotFound, create_package,
    package_summary, package_zip, read_package,
)

router = APIRouter(prefix="/api/tasks", tags=["workspace-packages"], dependencies=[Depends(require_owner)])
MAX_REQUEST_BYTES = 8 * 1024 * 1024  # Includes JSON escaping; source limit is 1 MiB.


class PackageRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    purpose: str = Field(min_length=1, max_length=2000)
    files: dict[str, str] = Field(min_length=1, max_length=100)


class EditRequest(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=False)
    request_id: UUID
    base_checksum: str = Field(pattern=r'^[0-9a-f]{64}$')
    purpose: str = Field(min_length=1, max_length=2000)
    changes: dict[str, str] = Field(default_factory=dict, max_length=100)
    removals: list[str] = Field(default_factory=list, max_length=100)


async def edit_payload(request: Request) -> EditRequest:
    raw = bytearray()
    async for chunk in request.stream():
        if len(raw) + len(chunk) > MAX_REQUEST_BYTES:
            raise HTTPException(413, 'Żądanie przekracza 8 MiB.')
        raw.extend(chunk)
    try:
        return EditRequest.model_validate_json(raw)
    except ValidationError as exc:
        raise HTTPException(422, 'Oczekiwane: request_id, base_checksum, purpose, changes i removals.') from exc


async def bounded_payload(request: Request) -> PackageRequest:
    raw = bytearray()
    async for chunk in request.stream():
        if len(raw) + len(chunk) > MAX_REQUEST_BYTES:
            raise HTTPException(413, "Żądanie przekracza 8 MiB.")
        raw.extend(chunk)
    try:
        return PackageRequest.model_validate_json(raw)
    except ValidationError as exc:
        # Never echo potentially sensitive source content in error responses.
        raise HTTPException(422, "Oczekiwany JSON: purpose oraz files (mapa ścieżka → tekst).") from exc


@router.post("/{task_id}/workspace-packages", status_code=201,
             openapi_extra={"requestBody": {"required": True, "content": {
                 "application/json": {"schema": PackageRequest.model_json_schema()}
             }}})
def store_package(
    task_id: int,
    payload: PackageRequest = Depends(bounded_payload),
    session: Session = Depends(get_organization_session),
) -> dict:
    try:
        artifact = create_package(session, task_id, payload.files, payload.purpose)
        _, content = read_package(session, task_id, artifact.id)
        return package_summary(artifact, content)
    except PackageNotFound as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except SQLAlchemyError as exc:
        session.rollback()
        raise HTTPException(503, "Nie można zapisać paczki.") from exc


def checked_package(session: Session, task_id: int, artifact_id: int):
    try:
        return read_package(session, task_id, artifact_id)
    except PackageNotFound as exc:
        raise HTTPException(404, str(exc)) from exc
    except PackageIntegrityError as exc:
        raise HTTPException(409, str(exc)) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(503, "Nie można odczytać paczki.") from exc


@router.get("/{task_id}/workspace-packages")
def list_packages(task_id: int, response: Response,
                  limit: int = Query(default=20, ge=1, le=50),
                  before: int | None = Query(default=None, ge=1),
                  session: Session = Depends(get_organization_session)) -> dict:
    """Newest first, bounded and cursor-paginated; never returns source contents."""
    response.headers["Cache-Control"] = "no-store"
    try:
        if session.get(Task, task_id) is None:
            raise HTTPException(404, "Nie znaleziono zadania.")
        query = select(Artifact.id).where(
            Artifact.task_id == task_id, Artifact.name == PACKAGE_NAME,
            Artifact.artifact_type == ArtifactType.SOURCE_CODE,
        )
        if before is not None:
            query = query.where(Artifact.id < before)
        ids = list(session.scalars(query.order_by(Artifact.id.desc()).limit(limit + 1)))
        items = [package_summary(*checked_package(session, task_id, id_)) for id_ in ids[:limit]]
        return {"packages": items, "next_cursor": ids[limit - 1] if len(ids) > limit else None}
    except SQLAlchemyError as exc:
        raise HTTPException(503, "Nie można odczytać listy paczek.") from exc


@router.get("/{task_id}/workspace-packages/{artifact_id}")
def get_package(task_id: int, artifact_id: int, response: Response,
                session: Session = Depends(get_organization_session)) -> dict:
    artifact, payload = checked_package(session, task_id, artifact_id)
    response.headers["Cache-Control"] = "no-store"
    return package_summary(artifact, payload)


@router.get("/{task_id}/workspace-packages/{artifact_id}/download")
def download_package(task_id: int, artifact_id: int,
                     session: Session = Depends(get_organization_session)) -> Response:
    _, payload = checked_package(session, task_id, artifact_id)
    return Response(package_zip(payload), media_type="application/zip", headers={
        "Content-Disposition": f'attachment; filename="task-{task_id}-package-{artifact_id}.zip"',
        "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff",
    })


@router.get('/{task_id}/workspace-packages/{artifact_id}/multifile-inspection')
def inspect_multifile_package(task_id: int, artifact_id: int, response: Response,
                              session: Session = Depends(get_organization_session)) -> dict:
    from app.services.multifile_profile import inspect_sources
    artifact, payload = checked_package(session, task_id, artifact_id)
    response.headers['Cache-Control'] = 'no-store'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    return inspect_sources({entry['path']: entry['content'] for entry in payload['files']}) | {
        'task_id': task_id, 'package_id': artifact_id, 'package_checksum': artifact.checksum,
    }


@router.get('/{task_id}/workspace-packages/{artifact_id}/source')
def source_file(task_id: int, artifact_id: int, response: Response,
                path: str = Query(min_length=1, max_length=200),
                session: Session = Depends(get_organization_session)):
    artifact, payload = checked_package(session, task_id, artifact_id)
    entry = next((entry for entry in payload['files'] if entry['path'] == path), None)
    if entry is None:
        raise HTTPException(404, 'Nie znaleziono pliku w tej paczce.')
    response.headers['Cache-Control'] = 'no-store'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    return dict(task_id=task_id, package_id=artifact_id, package_checksum=artifact.checksum,
                **entry, protected_test=protected_test(path))


@router.post('/{task_id}/workspace-packages/{artifact_id}/edits',
             openapi_extra={'requestBody': {'required': True, 'content': {
                 'application/json': {'schema': EditRequest.model_json_schema()}}}})
def edit_package(task_id: int, artifact_id: int, response: Response,
                 payload: EditRequest = Depends(edit_payload),
                 session: Session = Depends(get_organization_session)):
    response.headers['Cache-Control'] = 'no-store'
    try:
        session.execute(text('BEGIN IMMEDIATE'))
        result = revise(session, task_id, artifact_id, **(payload.model_dump() | {'request_id': str(payload.request_id)}))
        session.commit()
        return result
    except PackageNotFound as exc:
        session.rollback()
        raise HTTPException(404, str(exc)) from exc
    except (ValueError, PackageIntegrityError) as exc:
        session.rollback()
        raise HTTPException(409, str(exc)) from exc
    except SQLAlchemyError as exc:
        session.rollback()
        raise HTTPException(503, 'Niepewny zapis zmiany. Ponów z tym samym request_id i treścią.') from exc


@router.get("/{task_id}/workspace-packages/{artifact_id}/comparison")
def compare_packages(task_id: int, artifact_id: int, response: Response,
                     base_id: int = Query(ge=1),
                     path: str | None = Query(default=None, min_length=1, max_length=200),
                     session: Session = Depends(get_organization_session)) -> dict:
    from app.services.package_comparison import compare
    response.headers['Cache-Control'] = 'no-store'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    try:
        return compare(session, task_id, artifact_id, base_id, path)
    except PackageNotFound as exc:
        raise HTTPException(404, str(exc)) from exc
    except PackageIntegrityError as exc:
        raise HTTPException(409, str(exc)) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(503, 'Nie można porównać paczek. Spróbuj ponownie.') from exc
