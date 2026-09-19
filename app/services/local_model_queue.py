"""A durable single-slot rehearsal of model dispatch. No HTTP, code or model calls.

Production inference is deliberately unavailable until the resource gate and
the runner have been configured and validated after the Vast.ai rental ends.
"""
from typing import Protocol

from sqlalchemy import func, select, text

from app.models.audit import AuditEvent
from app.models.local_model_job import LocalModelJob
from app.models.task import utc_now
from app.services.agent_packets import export_prompt


class SimulationProvider(Protocol):
    simulation_only: bool

    def complete(self, messages: list[dict]) -> str: ...


class FixtureProvider:
    simulation_only = True

    def complete(self, messages):
        return ('SYMULACJA — to nie jest rezultat pracy Qwen. '
                'Instrukcja została przekazana atrapie wykonawcy, a odpowiedź '
                'zapisana w kolejce próbnej. Nie wykonano zadania ani testów produktu.')


def summary(job):
    return {name: getattr(job, name) for name in (
        'id', 'task_id', 'packet_id', 'packet_checksum', 'state', 'mode',
        'attempts', 'result_content', 'error_code', 'created_at', 'started_at', 'finished_at',
    )} | {'model_invoked': False, 'task_changed': False}


def audit(session, job, operation):
    session.add(AuditEvent(event_type='local_model_queue', operation=operation,
        decision=job.state, allowed=True,
        reason=f'owner; job={job.id}; task={job.task_id}; mode=simulation; model_invoked=false'))


def enqueue(session, task_id, packet_id, packet_checksum, request_id):
    """Caller starts BEGIN IMMEDIATE. No Task mutation, no implicit execution."""
    existing = session.scalar(select(LocalModelJob).where(LocalModelJob.request_id == request_id))
    if existing:
        if (existing.task_id, existing.packet_id, existing.packet_checksum) != (task_id, packet_id, packet_checksum):
            raise ValueError('Identyfikator żądania jest przypisany do innej instrukcji.')
        return summary(existing)
    existing = session.scalar(select(LocalModelJob).where(LocalModelJob.packet_id == packet_id))
    if existing:
        if existing.task_id != task_id or existing.packet_checksum != packet_checksum:
            raise ValueError('Niezgodne powiązanie instrukcji.')
        return summary(existing)
    prompt = export_prompt(session, task_id, packet_id)
    if prompt['packet_checksum'] != packet_checksum:
        raise ValueError('Niezgodna wersja instrukcji.')
    count = session.scalar(select(func.count()).select_from(LocalModelJob).where(LocalModelJob.state.in_(['queued', 'running'])))
    if count >= 50:
        raise ValueError('Kolejka próbna mieści do 50 oczekujących pozycji.')
    job = LocalModelJob(request_id=request_id, task_id=task_id, packet_id=packet_id,
                        packet_checksum=packet_checksum, state='queued', mode='simulation', attempts=0)
    session.add(job); session.flush(); audit(session, job, 'enqueue')
    return summary(job)


def cancel(session, job_id):
    job = session.get(LocalModelJob, job_id)
    if not job:
        raise LookupError('Nie znaleziono pozycji kolejki.')
    if job.state == 'cancelled':
        return summary(job)
    if job.state != 'queued':
        raise ValueError('Anulować można tylko pozycję oczekującą. Nie przerywamy procesu przez zmianę statusu.')
    job.state = 'cancelled'; job.finished_at = utc_now(); audit(session, job, 'cancel')
    return summary(job)


def fail(session, job, code, state='failed'):
    job.state = state; job.error_code = code; job.finished_at = utc_now()
    job.result_content = None
    audit(session, job, 'finish')


def reserve(session):
    session.execute(text('BEGIN IMMEDIATE'))
    session.expire_all()
    if session.scalar(select(LocalModelJob.id).where(LocalModelJob.state == 'running').limit(1)):
        session.rollback()
        raise ValueError('Jedna pozycja jest już wykonywana. Nie uruchomiono drugiej.')
    job = session.scalar(select(LocalModelJob).where(LocalModelJob.state == 'queued').order_by(LocalModelJob.id).limit(1))
    if not job:
        session.rollback(); return None, None
    try:
        if job.mode != 'simulation':
            raise ValueError('Live mode unavailable')
        prompt = export_prompt(session, job.task_id, job.packet_id)
        if prompt['packet_checksum'] != job.packet_checksum:
            raise ValueError('Stale checksum')
    except (ValueError, LookupError):
        fail(session, job, 'instruction_not_current', 'stale')
        session.commit(); return job, None
    job.state = 'running'; job.attempts += 1; job.started_at = utc_now()
    audit(session, job, 'reserve'); session.commit()
    return job, prompt


def run_next(session, provider: SimulationProvider):
    if getattr(provider, 'simulation_only', False) is not True:
        raise ValueError('Inferencja jest wyłączona. Dozwolony wyłącznie adapter symulacyjny.')
    job, prompt = reserve(session)
    if job is None:
        return {'job': None, 'model_invoked': False}
    if prompt is None:
        return {'job': summary(job), 'model_invoked': False}
    job_id = job.id
    # No database write lock while the provider responds. No retries.
    result = None; error = None
    try:
        result = provider.complete(prompt['messages'])
        if not isinstance(result, str) or not result.strip() or len(result) > 32000 or '\x00' in result:
            raise ValueError('Invalid output')
        result = result.strip(); result.encode('utf-8')
    except TimeoutError:
        error = 'provider_timeout'
    except Exception:
        error = 'provider_failed_or_invalid_output'
    session.execute(text('BEGIN IMMEDIATE')); session.expire_all()
    job = session.get(LocalModelJob, job_id)
    if not job or job.state != 'running':
        session.rollback(); raise ValueError('Stan kolejki zmienił się. Odpowiedź nie została zapisana.')
    try:
        current = export_prompt(session, job.task_id, job.packet_id)
        if current['packet_checksum'] != job.packet_checksum:
            raise ValueError('Stale checksum')
    except (ValueError, LookupError):
        fail(session, job, 'instruction_changed_during_run', 'stale')
    else:
        if error:
            fail(session, job, error)
        else:
            job.state = 'simulation_complete'; job.result_content = result
            job.finished_at = utc_now(); audit(session, job, 'finish')
    session.commit()
    return {'job': summary(job), 'model_invoked': False}
