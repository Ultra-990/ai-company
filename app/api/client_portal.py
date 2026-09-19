from __future__ import annotations

from datetime import datetime, timedelta, timezone
from hashlib import sha256
import re
import secrets
from typing import Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response
from pydantic import BaseModel, ConfigDict, Field, model_validator
from typing import Annotated
from sqlalchemy import select, text, delete
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.auth import require_owner
from app.api.organization_os import get_organization_session
from app.models.client_portal import ClientShare, ClientPublicationRevision, ClientActivity
from app.models.project import Project
from app.services.client_feedback import publication_checksum, current_feedback

router = APIRouter(tags=["client-portal"])
client_router = APIRouter(tags=["client-view"])


class Milestone(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    title: str = Field(min_length=1, max_length=200)
    status: Literal["planned", "in_progress", "review", "completed", "blocked"] = "planned"
    key: str = Field(default="", max_length=80, pattern=r"^[a-zA-Z0-9_.-]*$")
    description: str = Field(default="", max_length=2000)
    deliverable: str = Field(default="", max_length=6000)
    acceptance_criteria: list[Annotated[str, Field(min_length=1, max_length=500)]] = Field(default_factory=list, max_length=12)
    review_note: str = Field(default="", max_length=2000)


class PublishedProject(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    title: str = Field(min_length=1, max_length=200)
    summary: str = Field(min_length=1, max_length=4000)
    progress: int = Field(default=0, ge=0, le=100, strict=True)
    status: Literal["planned", "in_progress", "review", "completed", "blocked"] = "planned"
    next_step: str = Field(min_length=1, max_length=1000)
    milestones: list[Milestone] = Field(default_factory=list, max_length=30)

    @model_validator(mode="after")
    def unique_stage_keys(self):
        keys = [stage.key for stage in self.milestones if stage.key]
        if len(set(keys)) != len(keys):
            raise ValueError("Klucze etapów muszą być niepowtarzalne.")
        return self


class CreateShare(PublishedProject):
    project_id: int = Field(ge=1)
    expires_in_days: int = Field(default=7, ge=1, le=30)


def utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def metadata(share: ClientShare) -> dict:
    return {"id": share.id, "project_id": share.project_id,
            "created_at": utc(share.created_at).isoformat(), "updated_at": utc(share.updated_at).isoformat(),
            "expires_at": utc(share.expires_at).isoformat(),
            "revoked": share.revoked_at is not None,
            "expired": utc(share.expires_at) <= datetime.now(timezone.utc)}


def commit(session: Session) -> None:
    try:
        session.commit()
    except SQLAlchemyError as exc:
        session.rollback()
        raise HTTPException(503, "Nie można zapisać publikacji.") from exc


def revision(session, share, kind):
    session.flush()
    session.add(ClientPublicationRevision(share_id=share.id, kind=kind, public_content=share.public_content))


def baseline(session, share):
    if session.scalar(select(ClientPublicationRevision.id).where(ClientPublicationRevision.share_id == share.id).limit(1)) is None:
        session.add(ClientPublicationRevision(share_id=share.id, kind="baseline", public_content=share.public_content, created_at=share.updated_at))


@router.post("/api/client-shares", status_code=201, dependencies=[Depends(require_owner)])
def create_share(payload: CreateShare, response: Response,
                 session: Session = Depends(get_organization_session)) -> dict:
    if session.get(Project, payload.project_id) is None:
        raise HTTPException(404, "Nie znaleziono projektu.")
    # Explicit allowlist: never serialize Project, Task, Agent or Artifact objects to clients.
    public = PublishedProject.model_validate(payload.model_dump(exclude={"project_id", "expires_in_days"}))
    token = secrets.token_urlsafe(32)
    share = ClientShare(project_id=payload.project_id, token_digest=sha256(token.encode()).hexdigest(),
                        public_content=public.model_dump_json(),
                        expires_at=datetime.now(timezone.utc) + timedelta(days=payload.expires_in_days))
    session.add(share); revision(session, share, "created"); commit(session)
    response.headers["Cache-Control"] = "no-store"
    return metadata(share) | {"token": token, "portal_path": "/client"}


@router.get("/api/client-shares", dependencies=[Depends(require_owner)])
def list_shares(response: Response, project_id: int = Query(ge=1),
                limit: int = Query(default=30, ge=1, le=100),
                session: Session = Depends(get_organization_session)) -> dict:
    response.headers["Cache-Control"] = "no-store"
    shares = session.scalars(select(ClientShare).where(ClientShare.project_id == project_id)
                             .order_by(ClientShare.id.desc()).limit(limit))
    return {"shares": [metadata(share) for share in shares]}


@router.put("/api/client-shares/{share_id}", dependencies=[Depends(require_owner)])
def publish_update(share_id: int, payload: PublishedProject, response: Response,
                   session: Session = Depends(get_organization_session)) -> dict:
    session.execute(text("BEGIN IMMEDIATE"))
    share = session.get(ClientShare, share_id)
    if share is None:
        raise HTTPException(404, "Nie znaleziono publikacji.")
    if share.revoked_at is not None or utc(share.expires_at) <= datetime.now(timezone.utc):
        raise HTTPException(409, "Dostęp został wycofany lub wygasł.")
    baseline(session, share)
    share.public_content = payload.model_dump_json()
    share.updated_at = datetime.now(timezone.utc)
    revision(session, share, "updated"); commit(session)
    response.headers["Cache-Control"] = "no-store"
    return metadata(share)


@router.post("/api/client-shares/{share_id}/revoke", dependencies=[Depends(require_owner)])
def revoke_share(share_id: int, response: Response,
                 session: Session = Depends(get_organization_session)) -> dict:
    session.execute(text("BEGIN IMMEDIATE"))
    share = session.get(ClientShare, share_id)
    if share is None:
        raise HTTPException(404, "Nie znaleziono publikacji.")
    if share.revoked_at is None:
        baseline(session, share)
        share.revoked_at = datetime.now(timezone.utc)
        revision(session, share, "revoked")
        commit(session)
    response.headers["Cache-Control"] = "no-store"
    return metadata(share)


def authorized_share(session, authorization):
    invalid = HTTPException(401, "Dostęp nieprawidłowy, wygasły lub wycofany.", headers={"WWW-Authenticate": "Bearer"})
    scheme, _, token = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not re.fullmatch(r"[A-Za-z0-9_-]{43}", token):
        raise invalid
    share = session.scalar(select(ClientShare).where(ClientShare.token_digest == sha256(token.encode()).hexdigest()))
    if share is None or share.revoked_at is not None or utc(share.expires_at) <= datetime.now(timezone.utc):
        raise invalid
    return share


@client_router.get("/api/client/overview")
def client_overview(response: Response, authorization: str | None = Header(default=None),
                    session: Session = Depends(get_organization_session)) -> dict:
    share = authorized_share(session, authorization)
    public = PublishedProject.model_validate_json(share.public_content)
    response.headers["Cache-Control"] = "no-store"
    return {"project": public.model_dump(), "updated_at": utc(share.updated_at).isoformat(),
            "expires_at": utc(share.expires_at).isoformat(), "source": "owner_published_snapshot",
            "publication_checksum": publication_checksum(share), "client_decisions": current_feedback(session, share)}


class ActivityInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["open_project", "view_workflow", "view_stage", "view_materials", "view_reviews"]
    stage_index: int | None = Field(default=None, ge=0, le=29, strict=True)
    publication_updated_at: datetime


@client_router.post("/api/client/activity")
def client_activity(payload: ActivityInput, response: Response,
                    authorization: str | None = Header(default=None),
                    session: Session = Depends(get_organization_session)) -> dict:
    # Authenticate again inside the write transaction; revocation wins before commit.
    session.execute(text("BEGIN IMMEDIATE"))
    share = authorized_share(session, authorization)
    response.headers["Cache-Control"] = "no-store"
    if utc(payload.publication_updated_at) != utc(share.updated_at):
        raise HTTPException(409, "Widok pochodzi z wcześniejszej publikacji.")
    public = PublishedProject.model_validate_json(share.public_content)
    stage_title = None
    if payload.kind == "view_stage":
        if payload.stage_index is None or payload.stage_index >= len(public.milestones):
            raise HTTPException(422, "Nie znaleziono opublikowanego etapu.")
        stage_title = public.milestones[payload.stage_index].title
    elif payload.stage_index is not None:
        raise HTTPException(422, "Indeks etapu dotyczy tylko otwarcia etapu.")
    now = datetime.now(timezone.utc)
    recent = session.scalar(select(ClientActivity).where(ClientActivity.share_id == share.id).order_by(ClientActivity.id.desc()).limit(1))
    # Navigation only, not heartbeats. Bound rapid or duplicated client requests.
    if recent and (now - utc(recent.created_at)).total_seconds() < 2:
        return {"recorded": False, "reason": "rate_limited"}
    session.add(ClientActivity(share_id=share.id, kind=payload.kind, stage_title=stage_title,
                               publication_updated_at=share.updated_at, created_at=now))
    session.flush()
    keep = select(ClientActivity.id).where(ClientActivity.share_id == share.id).order_by(ClientActivity.id.desc()).limit(1000)
    session.execute(delete(ClientActivity).where(ClientActivity.share_id == share.id, ClientActivity.id.not_in(keep)))
    commit(session)
    return {"recorded": True}


@router.get("/api/client-shares/{share_id}", dependencies=[Depends(require_owner)])
def read_publication(share_id: int, response: Response,
                     session: Session = Depends(get_organization_session)) -> dict:
    share = session.get(ClientShare, share_id)
    if share is None:
        raise HTTPException(404, "Nie znaleziono publikacji.")
    response.headers["Cache-Control"] = "no-store"
    return {"share": metadata(share), "project": PublishedProject.model_validate_json(share.public_content).model_dump()}


@router.get("/api/client-history", dependencies=[Depends(require_owner)])
def client_history_index(response: Response, before: int | None = Query(default=None, ge=1),
                         session: Session = Depends(get_organization_session)) -> dict:
    response.headers["Cache-Control"] = "no-store"
    query = select(ClientShare).order_by(ClientShare.id.desc()).limit(31)
    if before: query = query.where(ClientShare.id < before)
    shares = list(session.scalars(query))
    result = []
    for share in shares[:30]:
        public = PublishedProject.model_validate_json(share.public_content)
        last = session.scalar(select(ClientActivity).where(ClientActivity.share_id == share.id).order_by(ClientActivity.id.desc()).limit(1))
        result.append(metadata(share) | {"title": public.title, "status": public.status, "progress": public.progress,
                                        "last_activity_at": utc(last.created_at).isoformat() if last else None})
    return {"shares": result, "next_cursor": shares[29].id if len(shares) > 30 else None}


@router.get("/api/client-shares/{share_id}/history", dependencies=[Depends(require_owner)])
def share_history(share_id: int, response: Response, before_revision: int | None = Query(default=None, ge=1),
                  before_activity: int | None = Query(default=None, ge=1),
                  session: Session = Depends(get_organization_session)) -> dict:
    share = session.get(ClientShare, share_id)
    if share is None: raise HTTPException(404, "Nie znaleziono publikacji.")
    response.headers["Cache-Control"] = "no-store"
    versions = select(ClientPublicationRevision).where(ClientPublicationRevision.share_id == share_id).order_by(ClientPublicationRevision.id.desc()).limit(31)
    activity = select(ClientActivity).where(ClientActivity.share_id == share_id).order_by(ClientActivity.id.desc()).limit(51)
    if before_revision: versions = versions.where(ClientPublicationRevision.id < before_revision)
    if before_activity: activity = activity.where(ClientActivity.id < before_activity)
    revisions, events = list(session.scalars(versions)), list(session.scalars(activity))
    return {"share": metadata(share), "project": PublishedProject.model_validate_json(share.public_content).model_dump(),
            "revisions": [{"id": r.id, "kind": r.kind, "at": utc(r.created_at).isoformat(), "project": PublishedProject.model_validate_json(r.public_content).model_dump()} for r in revisions[:30]],
            "activities": [{"id": a.id, "kind": a.kind, "stage_title": a.stage_title, "at": utc(a.created_at).isoformat(), "publication_updated_at": utc(a.publication_updated_at).isoformat()} for a in events[:50]],
            "next_revision": revisions[29].id if len(revisions) > 30 else None,
            "next_activity": events[49].id if len(events) > 50 else None,
            "activity_identity": "access_code_not_verified_person"}
