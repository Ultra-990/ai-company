"""Version-bound client decisions and owner acknowledgment, without execution rights."""
import json
from datetime import datetime, timezone
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.api.auth import require_owner
from app.api.client_portal import authorized_share, PublishedProject, commit
from app.api.organization_os import get_organization_session
from app.models.audit import AuditEvent
from app.models.client_portal import ClientShare, ClientFeedback
from app.services.client_feedback import publication_checksum, receipt

client_router = APIRouter(tags=['client-decisions'])
owner_router = APIRouter(tags=['client-decisions-owner'], dependencies=[Depends(require_owner)])


class ClientDecision(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    request_id: UUID
    publication_checksum: str = Field(pattern=r'^[0-9a-f]{64}$')
    stage_index: int = Field(ge=0, le=29, strict=True)
    decision: Literal['accepted', 'changes_requested']
    comment: str = Field(min_length=3, max_length=4000)
    confirmed: bool = Field(strict=True)

    @field_validator('comment')
    @classmethod
    def valid_text(cls, value):
        try: value.encode('utf-8')
        except UnicodeEncodeError as exc: raise ValueError('Nieprawidłowy tekst UTF-8.') from exc
        if '\x00' in value: raise ValueError('Tekst zawiera niedozwolony znak NUL.')
        return value


class OwnerReply(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    reply: str = Field(min_length=3, max_length=2000)

    @field_validator('reply')
    @classmethod
    def valid_text(cls, value):
        return ClientDecision.valid_text(value)


@client_router.post('/api/client/feedback')
def submit_decision(payload: ClientDecision, response: Response, authorization: str | None = Header(default=None),
                    session: Session = Depends(get_organization_session)):
    response.headers['Cache-Control'] = 'no-store'
    session.execute(text('BEGIN IMMEDIATE'))
    share = authorized_share(session, authorization)
    if not payload.confirmed: raise HTTPException(422, 'Potwierdź sprawdzenie wskazanej wersji etapu.')
    existing = session.scalar(select(ClientFeedback).where(ClientFeedback.share_id == share.id, ClientFeedback.request_id == str(payload.request_id)))
    if existing:
        if (existing.publication_checksum, existing.stage_index, existing.decision, existing.comment) != (
            payload.publication_checksum, payload.stage_index, payload.decision, payload.comment):
            raise HTTPException(409, 'Ten identyfikator wysłania dotyczy innej decyzji. Nie nadpisano jej.')
        return receipt(existing) | {'replayed': True}
    if payload.publication_checksum != publication_checksum(share):
        raise HTTPException(409, 'Publikacja została zmieniona. Zamknij okno, odśwież projekt i sprawdź nową wersję.')
    project = PublishedProject.model_validate_json(share.public_content)
    if payload.stage_index >= len(project.milestones): raise HTTPException(422, 'Nie znaleziono etapu.')
    stage = project.milestones[payload.stage_index]
    if stage.status != 'review': raise HTTPException(409, 'Ten etap nie został udostępniony do odbioru.')
    if payload.decision == 'accepted' and not stage.deliverable:
        raise HTTPException(409, 'Nie udostępniono rezultatu tego etapu. Możesz zgłosić prośbę o uzupełnienie.')
    duplicate = session.scalar(select(ClientFeedback.id).where(ClientFeedback.share_id == share.id,
        ClientFeedback.publication_checksum == payload.publication_checksum, ClientFeedback.stage_index == payload.stage_index))
    if duplicate: raise HTTPException(409, 'Dla tej wersji etapu zapisano już decyzję. Odśwież projekt, aby ją zobaczyć.')
    row = ClientFeedback(share_id=share.id, request_id=str(payload.request_id), publication_checksum=payload.publication_checksum,
                         stage_index=payload.stage_index, stage_title=stage.title, stage_snapshot=stage.model_dump_json(),
                         decision=payload.decision, comment=payload.comment)
    session.add(row);session.flush()
    session.add(AuditEvent(event_type='client_feedback', operation='submit', decision=payload.decision, allowed=True,
                          reason=f'client_code; share={share.id}; feedback={row.id}; version={payload.publication_checksum}; no_task_changes'))
    commit(session)
    return receipt(row) | {'replayed': False}


def history(session, share_id, before):
    query=select(ClientFeedback).where(ClientFeedback.share_id == share_id).order_by(ClientFeedback.id.desc()).limit(31)
    if before: query=query.where(ClientFeedback.id < before)
    rows=list(session.scalars(query))
    return {'feedback': [receipt(r) | {'stage_snapshot': json.loads(r.stage_snapshot)} for r in rows[:30]],
            'next_cursor': rows[29].id if len(rows)>30 else None}


@client_router.get('/api/client/feedback')
def client_feedback_history(response: Response, before: int | None = Query(default=None, ge=1),
                            authorization: str | None = Header(default=None), session: Session = Depends(get_organization_session)):
    response.headers['Cache-Control']='no-store'
    share=authorized_share(session, authorization)
    return history(session, share.id, before)


@owner_router.get('/api/client-shares/{share_id}/feedback')
def owner_feedback_history(share_id: int, response: Response, before: int | None = Query(default=None, ge=1),
                           session: Session = Depends(get_organization_session)):
    response.headers['Cache-Control']='no-store'
    if session.get(ClientShare,share_id) is None: raise HTTPException(404,'Nie znaleziono publikacji.')
    return history(session, share_id, before)


@owner_router.post('/api/client-feedback/{feedback_id}/acknowledge')
def acknowledge(feedback_id: int, payload: OwnerReply, response: Response,
                session: Session = Depends(get_organization_session)):
    response.headers['Cache-Control']='no-store'
    session.execute(text('BEGIN IMMEDIATE'))
    row=session.get(ClientFeedback,feedback_id)
    if row is None: raise HTTPException(404,'Nie znaleziono decyzji.')
    if row.acknowledged_at:
        if row.owner_reply != payload.reply: raise HTTPException(409,'Odpowiedź została już zapisana. Nie zmieniono historii.')
        return receipt(row)
    row.owner_reply=payload.reply;row.acknowledged_at=datetime.now(timezone.utc)
    session.add(AuditEvent(event_type='client_feedback',operation='acknowledge',decision='acknowledged',allowed=True,
                          reason=f'owner; feedback={row.id}; no_task_changes'))
    commit(session)
    return receipt(row)
