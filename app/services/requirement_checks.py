"""Version-bound owner observations, not inferred coverage or client acceptance."""
import json
from hashlib import sha256

from sqlalchemy import select

from app.models.artifact import Artifact, ArtifactType
from app.models.audit import AuditEvent
from app.models.package_run import PackageRun
from app.models.task import Task
from app.models.work_order import WorkOrder
from app.services.work_orders import fingerprint
from app.services.workspace_packages import read_package, canonical_json, PackageIntegrityError

SCHEMA = 'requirement-check.v1'


def digest(text):
    return sha256(text.encode('utf-8')).hexdigest()


def context(session, task_id, package_id):
    try:
        artifact, package = read_package(session, task_id, package_id)
    except PackageIntegrityError as exc:
        raise ValueError('Naruszona integralność paczki. Weryfikacja wymagań jest wstrzymana.') from exc
    order = session.scalar(select(WorkOrder).where(WorkOrder.project_id == artifact.project_id))
    task = session.get(Task, task_id)
    if (not order or task_id not in order.task_ids or not task
            or task.project_id != order.project_id or task.plan_id != order.plan_id
            or artifact.plan_id != order.plan_id):
        raise ValueError('Paczka nie należy do zlecenia z kryteriami odbioru.')
    criteria = order.brief.get('acceptance_criteria')
    if (not isinstance(criteria, list) or not 1 <= len(criteria) <= 20
            or any(not isinstance(c, str) or not c.strip() for c in criteria)):
        raise ValueError('Zlecenie nie ma poprawnej listy kryteriów.')
    return artifact, fingerprint(order.brief), [
        {'id': digest(canonical_json({'index': i, 'text': criterion})), 'text': criterion}
        for i, criterion in enumerate(criteria)]


def record_name(package_id, criterion_id):
    return f'organization-os.requirement.{package_id}.{criterion_id}'


def latest(session, task_id, package_id, criterion_id):
    return session.scalar(select(Artifact).where(
        Artifact.task_id == task_id, Artifact.name == record_name(package_id, criterion_id))
        .order_by(Artifact.id.desc()).limit(1))


def decode(record):
    if (record.artifact_type != ArtifactType.REPORT or not record.content
            or digest(record.content) != record.checksum):
        raise ValueError('Naruszona integralność zapisu weryfikacji.')
    data = json.loads(record.content)
    if not isinstance(data, dict) or data.get('schema') != SCHEMA:
        raise ValueError('Nieprawidłowy zapis weryfikacji.')
    return data


def report_reference(session, task_id, package_id, source_checksum, report_id):
    if report_id is None:
        return None
    artifact = session.get(Artifact, report_id)
    run = session.scalar(select(PackageRun).where(PackageRun.report_id == report_id,
        PackageRun.task_id == task_id, PackageRun.package_id == package_id))
    if (not artifact or not run or run.state not in {'passed', 'failed'}
            or run.package_checksum != source_checksum or artifact.task_id != task_id
            or artifact.artifact_type != ArtifactType.TEST_RESULT
            or not artifact.content or digest(artifact.content) != artifact.checksum):
        raise ValueError('Dowód musi być spójnym raportem testów dokładnie tej paczki.')
    data = json.loads(artifact.content)
    if (not isinstance(data, dict) or data.get('schema') != 'package-run-report.v1'
            or data.get('run_id') != run.id or data.get('task_id') != task_id
            or data.get('package_id') != package_id or data.get('source_checksum') != source_checksum
            or data.get('state') != run.state or data.get('profile') != run.profile):
        raise ValueError('Raport testów nie odpowiada tej wersji.')
    return {'id': artifact.id, 'checksum': artifact.checksum, 'run_id': run.id, 'state': run.state}


def matrix(session, task_id, package_id):
    package, scope_checksum, criteria = context(session, task_id, package_id)
    counts = dict(not_checked=0, passed=0, failed=0, stale=0, invalid=0)
    for criterion in criteria:
        record = latest(session, task_id, package_id, criterion['id'])
        criterion.update(state='not_checked', assessment_id=record.id if record else None,
                         observed_result='', test_report=None, previous_id=None)
        if record:
            try:
                data = decode(record)
                if (data.get('task_id') != task_id or data.get('package_id') != package_id
                        or data.get('criterion_id') != criterion['id']
                        or data.get('state') not in {'passed', 'failed', 'not_checked'}
                        or not isinstance(data.get('observed_result'), str)):
                    raise ValueError('Nieprawidłowe przypisanie weryfikacji.')
                if data.get('source_checksum') != package.checksum or data.get('scope_checksum') != scope_checksum:
                    criterion['state'] = 'stale'
                else:
                    reference = report_reference(session, task_id, package_id, package.checksum,
                                                 (data.get('test_report') or {}).get('id'))
                    if reference != data.get('test_report'):
                        raise ValueError('Zmieniony dowód weryfikacji.')
                    criterion.update(state=data['state'], observed_result=data['observed_result'],
                                     test_report=reference, previous_id=data.get('previous_id'))
            except (ValueError, TypeError, AttributeError):
                criterion['state'] = 'invalid'
        counts[criterion['state']] += 1
    reports = []
    runs = session.scalars(select(PackageRun).where(PackageRun.task_id == task_id,
        PackageRun.package_id == package_id, PackageRun.state.in_(['passed', 'failed']))
        .order_by(PackageRun.id.desc()).limit(20))
    for run in runs:
        try:
            reference = report_reference(session, task_id, package_id, package.checksum, run.report_id)
            if reference:
                reports.append(reference)
        except (ValueError, TypeError):
            continue  # Never offer a corrupt or mismatched report as evidence.
    return {'task_id': task_id, 'package_id': package_id, 'source_checksum': package.checksum,
            'scope_checksum': scope_checksum, 'criteria': criteria, 'counts': counts,
            'available_reports': reports,
            'all_manually_confirmed': counts['passed'] == len(criteria),
            'automatic_coverage_verified': False, 'client_accepted': False,
            'note': 'Oceny właściciela dotyczą tej paczki i zakresu. Powiązanie raportu nie dowodzi pokrycia kryterium testem. Nie zmieniają odbioru zadania ani klienta.'}


def save(session, task_id, package_id, data):
    """Caller holds BEGIN IMMEDIATE; append only, optimistic concurrency and replay."""
    package, scope_checksum, criteria = context(session, task_id, package_id)
    if data['source_checksum'] != package.checksum or data['scope_checksum'] != scope_checksum:
        raise ValueError('Zmieniła się wersja lub zakres. Odśwież kryteria przed zapisem.')
    criterion = next((c for c in criteria if c['id'] == data['criterion_id']), None)
    if not criterion:
        raise ValueError('Kryterium nie należy do tego zakresu.')
    reference = report_reference(session, task_id, package_id, package.checksum, data['test_report_id'])
    payload = {k: data[k] for k in ('criterion_id', 'source_checksum', 'scope_checksum',
                                  'previous_id', 'state', 'observed_result')}
    payload.update(schema=SCHEMA, task_id=task_id, package_id=package_id,
                   criterion_text=criterion['text'], test_report=reference, method='owner_observation')
    content = canonical_json(payload)
    current = latest(session, task_id, package_id, criterion['id'])
    if current:
        decode(current)  # Do not silently cover up corrupt historical evidence.
        if current.content == content:
            return {'assessment_id': current.id, 'replayed': True}
    if data['previous_id'] != (current.id if current else None):
        raise ValueError('Inna karta zmieniła ocenę. Odśwież i porównaj wynik przed zapisem.')
    record = Artifact(task_id=task_id, project_id=package.project_id, plan_id=package.plan_id,
        artifact_type=ArtifactType.REPORT, name=record_name(package_id, criterion['id']),
        description='Ręczna weryfikacja kryterium dla konkretnej wersji, nie automatyczny test ani odbiór klienta.',
        content=content, checksum=digest(content), created_by='owner')
    session.add(record)
    session.flush()
    session.add(AuditEvent(event_type='requirement_check', operation='record', allowed=True,
        decision=data['state'], reason=f'owner; task={task_id}; package={package_id}; assessment={record.id}'))
    return {'assessment_id': record.id, 'replayed': False}


def history(session, task_id, package_id, criterion_id, before=None):
    package, scope_checksum, criteria = context(session, task_id, package_id)
    if not any(c['id'] == criterion_id for c in criteria):
        raise LookupError('Brak kryterium w aktualnym zakresie.')
    query = select(Artifact).where(Artifact.task_id == task_id,
        Artifact.name == record_name(package_id, criterion_id)).order_by(Artifact.id.desc())
    if before is not None:
        query = query.where(Artifact.id < before)
    rows = list(session.scalars(query.limit(21)))
    entries = []
    for record in rows[:20]:
        item = {'id': record.id, 'created_at': record.created_at.isoformat(),
                'state': 'invalid', 'observed_result': '', 'matches_current_scope': False}
        try:
            data = decode(record)
            if (data.get('task_id') != task_id or data.get('package_id') != package_id
                    or data.get('criterion_id') != criterion_id
                    or data.get('state') not in {'passed', 'failed', 'not_checked'}
                    or not isinstance(data.get('observed_result'), str)):
                raise ValueError('Nieprawidłowa historia.')
            item.update(state=data['state'], observed_result=data['observed_result'],
                        matches_current_scope=data.get('scope_checksum') == scope_checksum
                        and data.get('source_checksum') == package.checksum)
        except (ValueError, TypeError):
            pass
        entries.append(item)
    return {'entries': entries, 'next_cursor': rows[19].id if len(rows) > 20 else None,
            'note': 'Historia deklaracji właściciela. Nie weryfikuje ponownie historycznych dowodów; aktualny stan jest na liście wymagań.'}
