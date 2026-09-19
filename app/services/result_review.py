"""Shared review operation; caller owns transaction and documentation refresh."""
import json
from hashlib import sha256
from sqlalchemy import select, func
from app.models.task import Task, TaskAttempt, TaskStatus, TaskTransitionError, utc_now
from app.models.artifact import Artifact, ArtifactType
from app.models.audit import AuditEvent


def apply_review(session, task_id, *, attempt_id, result_checksum, accepted, reason, evidence, reviewer_role='owner'):
    if reviewer_role not in {'owner','automated_qa'} or (reviewer_role=='automated_qa' and accepted):
        raise ValueError('Automatyczna kontrola może kierować wynik do poprawy, nie udawać odbioru właściciela.')
    normalized=[item.strip() for item in evidence]
    if not reason.strip() or not normalized or not all(normalized):
        raise ValueError('Odbiór wymaga uzasadnienia i dowodów kontroli')
    task=session.get(Task,task_id)
    if task is None:raise LookupError(f'Nie znaleziono zadania {task_id}')
    attempt=session.get(TaskAttempt,attempt_id)
    latest=session.scalar(select(func.max(TaskAttempt.id)).where(TaskAttempt.task_id==task_id))
    if (not attempt or attempt.task_id!=task_id or latest!=attempt_id or
        attempt.status!='awaiting_review' or task.status is not TaskStatus.IN_PROGRESS):
        raise TaskTransitionError('Wskazana próba nie oczekuje na odbiór')
    checksum=sha256((attempt.result_content or '').encode()).hexdigest()
    if not attempt.result_content or result_checksum!=checksum or attempt.result_checksum!=checksum:
        raise TaskTransitionError('Wersja lub integralność wyniku nie zgadza się')
    acceptance_proof = None
    if accepted:
        from app.services.acceptance_gate import require_attempt
        try:
            acceptance_proof = require_attempt(session, task_id, attempt)
        except (ValueError, LookupError) as exc:
            raise TaskTransitionError(str(exc)) from exc
    decision='accepted' if accepted else 'rejected'
    attempt.status='completed' if accepted else 'blocked'
    attempt.verification_status=decision;attempt.verification_reason=reason.strip();attempt.verified_at=utc_now()
    attempt.error_summary=None if accepted else reason.strip()
    task.transition_to(TaskStatus.COMPLETED if accepted else TaskStatus.BLOCKED)
    record=json.dumps({'reviewer_role':reviewer_role,'decision':decision,'attempt_id':attempt_id,
        'result_checksum':checksum,'reason':reason.strip(),'evidence':normalized,
        'review_method':'owner_attestation' if reviewer_role=='owner' else 'automatic_test_feedback',
        **({'acceptance_proof':acceptance_proof} if acceptance_proof else {})},ensure_ascii=False,sort_keys=True)
    session.add(Artifact(task_id=task_id,task_attempt_id=attempt_id,project_id=task.project_id,plan_id=task.plan_id,
        artifact_type=ArtifactType.REPORT,name='Odbiór wyniku zadania',content=record,
        checksum=sha256(record.encode()).hexdigest(),created_by=reviewer_role))
    session.add(AuditEvent(event_type='task_acceptance',operation='review_result',decision=decision,allowed=True,
        reason=f'task_id={task_id}; attempt_id={attempt_id}; reviewer_role={reviewer_role}; {reason.strip()}'))
    return task
