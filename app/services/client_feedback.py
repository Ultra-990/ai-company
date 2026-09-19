"""Publication fingerprints and allowlisted client receipts. No task side effects."""
from datetime import timezone
from hashlib import sha256

from sqlalchemy import select
from app.models.client_portal import ClientFeedback


def timestamp(value):
    return (value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)).isoformat()


def publication_checksum(share):
    return sha256((timestamp(share.updated_at) + '\n' + share.public_content).encode('utf-8')).hexdigest()


def receipt(row):
    return {'id': row.id, 'publication_checksum': row.publication_checksum, 'stage_index': row.stage_index,
            'stage_title': row.stage_title, 'decision': row.decision, 'comment': row.comment,
            'created_at': timestamp(row.created_at), 'owner_reply': row.owner_reply,
            'acknowledged_at': timestamp(row.acknowledged_at) if row.acknowledged_at else None,
            'identity': 'access_code_not_verified_person'}


def current_feedback(session, share):
    return [receipt(r) for r in session.scalars(select(ClientFeedback).where(
        ClientFeedback.share_id == share.id, ClientFeedback.publication_checksum == publication_checksum(share)
    ).order_by(ClientFeedback.stage_index).limit(30))]
