"""Read-only gate for explicitly selected HTTP plans. Never invokes a runner/model."""
from sqlalchemy import select

from app.models.artifact import Artifact, ArtifactType
from app.models.local_inference import LocalInference
from app.models.package_run import PackageRun
from app.services import acceptance_cases, automatic_acceptance, application_preview
from app.services.workspace_packages import PackageIntegrityError


def selected(session, task_id):
    # Import lazily: quality execution also uses the shared owner-review service.
    from app.services import application_quality as quality
    rows = session.scalars(select(Artifact).where(Artifact.task_id == task_id,
        Artifact.name.like(quality.NAME + ':request:%')).order_by(Artifact.id.desc()))
    for row in rows:
        try:
            _, data = quality.load_receipt(session, row.id)
            params = data['input']
            if not isinstance(params, dict):
                raise ValueError('Nieprawidłowe dane cyklu kontroli.')
            if (params.get('acceptance_plan_id') is None) != (params.get('acceptance_plan_checksum') is None):
                raise ValueError('Niekompletne powiązanie planu kontroli.')
            if params.get('acceptance_plan_id') is not None:
                if type(params['acceptance_plan_id']) is not int or not params.get('acceptance_plan_checksum'):
                    raise ValueError('Niekompletne powiązanie planu kontroli.')
                return row, data
        except (KeyError, TypeError, AttributeError) as exc:
            raise ValueError('Nie można potwierdzić wybranego planu: niespójny zapis cyklu.') from exc
    return None


def require_current(session, task_id, package_id, checksum, selection=None):
    """Most recently selected plan remains binding; a plan-less cycle cannot erase it.

    No selection means the legacy workflow. Merely creating a draft plan is not
    selection. A selected cycle must finish with these exact sources and evidence.
    """
    from app.services import application_quality as quality, package_runner
    selection = selection or selected(session, task_id)
    if selection is None:
        return None
    row, data = selection
    params = data['input']
    try:
        acceptance_cases.read(session, task_id, package_id, params['acceptance_plan_id'], params['acceptance_plan_checksum'])
        if application_preview.preview_configuration() != data.get('acceptance_preview_profile'):
            raise ValueError('Profil kontroli HTTP zmienił się. Potrzebne ponowne testy wybranego planu.')
        final = quality.named(session, quality.NAME + f':result:{row.id}')
        if not final or final.task_id != task_id or final.artifact_type != ArtifactType.REPORT:
            raise ValueError(f'Wybrany plan HTTP w cyklu #{row.id} nie ma zakończonego wyniku. Otwórz Budowę i testy.')
        result = quality.read_json(final)
        if (not isinstance(result, dict) or result.get('state') != 'passed'
                or result.get('final_package_id') != package_id or type(result.get('test_run_id')) is not int):
            raise ValueError(f'Cykl #{row.id} nie potwierdza wybranego planu HTTP dla tej paczki. Dokończ kontrolę i poprawki.')
        tested, _, _ = package_runner.validated_candidate(session, result['test_run_id'])
        if (tested.task_id != task_id or tested.package_id != package_id or tested.package_checksum != checksum
                or tested.profile != data['test_profile'] or tested.profile != package_runner.configuration()):
            raise ValueError('Test cyklu nie potwierdza tej wersji w bieżącym profilu.')
        if type(params.get('max_repairs')) is not int or not 1 <= params['max_repairs'] <= 2:
            raise ValueError('Nieprawidłowy limit zapisanego cyklu.')
        index = next((i for i in range(params['max_repairs'] + 1)
            if tested.request_id == quality.operation_id(params['request_id'], 'test', i)), None)
        if index is None:
            raise ValueError('Wykonanie testów nie należy do wybranego cyklu.')
        evidence, cases = automatic_acceptance.read_saved(session, cycle_id=row.id, index=index,
            task_id=task_id, package_id=package_id, checksum=checksum,
            plan_id=params['acceptance_plan_id'], plan_checksum=params['acceptance_plan_checksum'],
            preview_profile=data['acceptance_preview_profile'])
        if cases['state'] != 'passed':
            raise ValueError('Nie wszystkie przypadki wybranego planu HTTP zostały zaliczone.')
        return {'cycle_id': row.id, 'plan_id': params['acceptance_plan_id'],
                'plan_checksum': params['acceptance_plan_checksum'], 'result_id': evidence.id,
                'result_checksum': evidence.checksum, 'case_count': len(cases['cases'])}
    except (LookupError, PackageIntegrityError, KeyError, TypeError, AttributeError) as exc:
        raise ValueError('Brak spójnych dowodów wybranego planu HTTP. Sprawdź zakres, wersję i raporty w Budowie i testach.') from exc


def require_attempt(session, task_id, attempt):
    choice = selected(session, task_id)
    if choice is None:
        return None
    origin = session.scalar(select(LocalInference).where(LocalInference.attempt_id == attempt.id,
                                                       LocalInference.task_id == task_id))
    metrics = origin.metrics if origin and isinstance(origin.metrics, dict) else {}
    if type(metrics.get('package_id')) is not int or not metrics.get('package_checksum'):
        raise ValueError('Wybrany plan HTTP wymaga powiązania odbieranej próby z paczką źródeł.')
    # Ensure the attested attempt contains exactly the tested package, not merely
    # a matching metadata pointer to a different model response.
    from app.services.application_profile import parse_sources
    from app.services.workspace_packages import read_package
    try:
        source, payload = read_package(session, task_id, metrics['package_id'])
        if (source.checksum != metrics['package_checksum']
                or parse_sources(attempt.result_content) != {f['path']: f['content'] for f in payload['files']}):
            raise ValueError('Odbierana próba różni się od paczki sprawdzanej przez plan HTTP.')
    except PackageIntegrityError as exc:
        raise ValueError('Niespójna paczka odbieranej próby.') from exc
    return require_current(session, task_id, metrics['package_id'], metrics['package_checksum'], choice)
