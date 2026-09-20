"""Version-bound owner review for multifile candidates, separate from Task progress."""
import json
from hashlib import sha256

from sqlalchemy import select

from app.models.artifact import Artifact, ArtifactType
from app.models.audit import AuditEvent
from app.models.package_run import PackageRun
from app.models.task import Task, TaskStatus
from app.services.workspace_packages import canonical_json

NAME = 'organization-os.package-review.v1'
RELEASE = 'organization-os.release.'


def read_record(row):
    if (not row or row.artifact_type != ArtifactType.REPORT or row.created_by != 'owner'
            or sha256((row.content or '').encode()).hexdigest() != row.checksum):
        raise ValueError('Niespójny zapis odbioru lub wydania paczki.')
    try:
        data = json.loads(row.content)
        if not isinstance(data, dict):
            raise ValueError('Nieprawidłowy zapis decyzji.')
        return data
    except (TypeError, json.JSONDecodeError) as exc:
        raise ValueError('Nieprawidłowy zapis decyzji.') from exc


def context(session, run_id):
    from app.services import package_runner as runner
    run, package, report = runner.validated_candidate(session, run_id)
    if run.profile.get('profile') not in (runner.MULTIFILE_PROFILE, runner.MEDIA_PROFILE):
        raise ValueError('Ten odbiór dotyczy profilu wielomodułowego. Dla płaskiego użyj odbioru zadania.')
    latest = next((r.id for r in session.scalars(select(PackageRun).where(
        PackageRun.package_id == run.package_id).order_by(PackageRun.id.desc()))
        if 'request_path' not in r.profile), None)
    config = runner.media_configuration() if run.profile.get('profile') == runner.MEDIA_PROFILE else runner.multifile_configuration()
    if latest != run.id or config != run.profile:
        raise ValueError('Odbiór wymaga najnowszego zaliczonego testu w aktualnym profilu.')
    from app.services.acceptance_gate import selected
    if selected(session, run.task_id) is not None:
        raise ValueError('Zadanie ma wybrany plan HTTP starego cyklu. Nie można go ominąć odbiorem paczki; integracja tego planu z profilem wielomodułowym jest wymagana.')
    task = session.get(Task, run.task_id)
    if not task:
        raise LookupError('Brak zadania.')
    if task.status == TaskStatus.CANCELLED:
        raise ValueError('Anulowane zadanie nie może otrzymać zatwierdzonego wydania.')
    scope = {key: getattr(task, key) for key in ('title', 'description', 'project_id', 'plan_id', 'stages')}
    binding = dict(run_id=run.id, task_id=run.task_id, package_id=run.package_id,
                   source_checksum=run.package_checksum, report_id=report.id,
                   report_checksum=report.checksum, profile=run.profile, scope=scope)
    return run, package, report, binding, sha256(canonical_json(binding).encode()).hexdigest()


def latest_review(session, run):
    return session.scalar(select(Artifact).where(Artifact.task_id == run.task_id,
        Artifact.name.like(NAME + ':' + str(run.id) + ':%')).order_by(Artifact.id.desc()).limit(1))


def approved(session, run_id):
    run, package, report, binding, digest = context(session, run_id)
    review = latest_review(session, run)
    if not review:
        raise ValueError('Najpierw odbierz tę wersję paczki w Budowie i testach.')
    data = read_record(review)
    if (data.get('schema') != NAME or data.get('binding') != binding
            or data.get('context_checksum') != digest or data.get('accepted') is not True):
        raise ValueError('Brak aktualnego odbioru tej wersji albo odbiór został wycofany.')
    return run, package, report, review, data


def review_context(session, run_id):
    run, _, _, binding, digest = context(session, run_id)
    review = latest_review(session, run)
    decision = read_record(review) if review else None
    return dict(binding=binding, context_checksum=digest,
                accepted=bool(decision and decision.get('schema') == NAME
                              and decision.get('binding') == binding
                              and decision.get('context_checksum') == digest
                              and decision.get('accepted') is True),
                review_id=review.id if review else None,
                note='Odbiór paczki nie zamyka zadania, nie publikuje i nie potwierdza odbioru klienta.')


def review(session, run_id, *, request_id, context_checksum, accepted, criteria, evidence):
    """Caller owns write transaction. Retrying an old receipt never reaccepts a revoked result."""
    run, _, _, binding, digest = context(session, run_id)
    if digest != context_checksum:
        raise ValueError('Zmieniły się źródła, testy lub zakres. Wczytaj formularz odbioru ponownie.')
    name = NAME + ':' + str(run.id) + ':' + request_id
    data = dict(schema=NAME, binding=binding, context_checksum=digest, accepted=accepted,
                criteria=criteria, evidence=evidence, client_accepted=False, deployed=False)
    row = session.scalar(select(Artifact).where(Artifact.name == name))
    if row:
        if row.task_id != run.task_id or read_record(row) != data:
            raise ValueError('UUID wskazuje inną decyzję odbioru.')
    else:
        raw = canonical_json(data)
        row = Artifact(task_id=run.task_id, project_id=binding['scope']['project_id'],
            plan_id=binding['scope']['plan_id'], artifact_type=ArtifactType.REPORT,
            name=name, content=raw, checksum=sha256(raw.encode()).hexdigest(), created_by='owner',
            description='Jawna decyzja właściciela o konkretnej paczce i raporcie; bez zmiany Task.')
        session.add(row); session.flush()
        session.add(AuditEvent(event_type='package_review', operation='review', allowed=True,
            decision='accepted' if accepted else 'rejected', reason=f'owner; run={run.id}; review={row.id}'))
    current = latest_review(session, run)
    return dict(review_id=row.id, run_id=run.id, recorded_accepted=accepted,
                current=current.id == row.id, task_changed=False, client_accepted=False, deployed=False)


def validated_release(session, run_id):
    run, package, report, review, data = approved(session, run_id)
    row = session.scalar(select(Artifact).where(Artifact.task_id == run.task_id,
        Artifact.name == RELEASE + str(run.id) + '.review.' + str(review.id)))
    if not row:
        raise ValueError('Najpierw przygotuj wydanie po aktualnym odbiorze.')
    payload = read_record(row)
    expected = release_data(run, review, data)
    if payload != expected or row.task_attempt_id is not None:
        raise ValueError('Wydanie nie odpowiada bieżącej decyzji właściciela.')
    return run, package, report, row, payload


def release_data(run, review, data):
    # Internal criteria/evidence are not automatically copied to client materials.
    return dict(schema='owner-package-release.v1', run_id=run.id,
                source_checksum=run.package_checksum, review_id=review.id,
                review_checksum=review.checksum, context_checksum=data['context_checksum'],
                owner_accepted=True, client_accepted=False, deployed=False)


def release(session, run_id):
    run, _, _, review, data = approved(session, run_id)
    name = RELEASE + str(run.id) + '.review.' + str(review.id)
    row = session.scalar(select(Artifact).where(Artifact.task_id == run.task_id, Artifact.name == name))
    if row:
        validated_release(session, run_id)
    else:
        payload = release_data(run, review, data)
        raw = canonical_json(payload)
        row = Artifact(task_id=run.task_id, project_id=review.project_id, plan_id=review.plan_id,
            artifact_type=ArtifactType.REPORT, name=name, content=raw,
            checksum=sha256(raw.encode()).hexdigest(), created_by='owner',
            description='Wydanie konkretnej paczki odebranej przez właściciela; bez publikacji.')
        session.add(row); session.flush()
        session.add(AuditEvent(event_type='package_release', operation='prepare', allowed=True,
            decision='owner_accepted', reason=f'owner; run={run.id}; release={row.id}; review={review.id}'))
    return dict(release_id=row.id, **release_data(run, review, data))


def readiness(session, run_id, result):
    try:
        run, _, _, review, _ = approved(session, run_id)
    except (ValueError, LookupError) as exc:
        result['checks'].append(dict(key='package_review', passed=False, message=str(exc)))
        return result
    result['checks'].append(dict(key='package_review', passed=True,
        message='Właściciel odebrał dokładnie tę paczkę, aktualny zakres i najnowszy test.'))
    row = session.scalar(select(Artifact).where(Artifact.task_id == run.task_id,
        Artifact.name == RELEASE + str(run.id) + '.review.' + str(review.id)))
    if row:
        try:
            validated_release(session, run_id)
        except ValueError as exc:
            result['checks'].append(dict(key='release', passed=False, message=str(exc)))
            return result
        result['release_id'] = row.id
    result['ready'] = True
    result['checks'].append(dict(key='release', passed=bool(row),
        message='Wydanie gotowe do pobrania.' if row else 'Można przygotować wydanie; nie wysłano go klientowi.'))
    return result
