"""Client summary tests with fake models/runners and isolated databases."""
import io
import json
from hashlib import sha256
from zipfile import ZipFile

from app.models.artifact import Artifact
from app.models.package_run import PackageRun
from app.models.work_order import WorkOrder
from sqlalchemy import select
from tests.conftest import OWNER_HEADERS
from tests.test_delivery_handoff import tested, released
from tests.test_local_inference import config_and_no_network
from tests.test_package_runner import fake_runner, FILES
from tests.test_application_revisions import generated
from tests.test_automatic_acceptance import simulation
from tests.test_application_quality import isolated_locks
from tests.test_acceptance_gate import cycle_passed
from tests.test_agent_packets import review


def test_technical_summary_matches_manifest_without_inventing_business_coverage(client, released):
    path = f"/api/package-runs/{released['id']}"
    handoff = client.get(path + '/handoff', headers=OWNER_HEADERS).json()
    assert handoff['schema'] == 'client-handoff.v2'
    summary = handoff['delivery_summary']
    assert summary['file_count'] == len(FILES)
    assert summary['source_bytes'] == sum(len(v.encode()) for v in FILES.values())
    assert summary['source_checksum'] == released['package_checksum']
    assert summary['verified_http_examples'] is None
    assert summary['recorded_test_profile_passed'] is True and summary['owner_accepted'] is True
    for key in ('business_scope_verified', 'visual_review_verified', 'full_security_audit_verified',
                'production_deployment_verified', 'client_accepted'):
        assert summary[key] is False
    assert all('content' not in f for f in summary['files'])
    with ZipFile(io.BytesIO(client.get(path + '/released.zip', headers=OWNER_HEADERS).content)) as archive:
        for name in ('DELIVERY-SUMMARY.md', 'DELIVERY-SUMMARY.pl.md'):
            text = archive.read(name).decode()
            assert text == handoff['guides'][name]
            assert sha256(text.encode()).hexdigest() == handoff['document_checksums'][name]
            for f in summary['files']:
                assert f['sha256'] in text and 'sources/' + f['path'] in text
        assert 'client-handoff.v2' in archive.read('handoff.json').decode()
    with ZipFile(io.BytesIO(client.get(path + '/candidate.zip', headers=OWNER_HEADERS).content)) as archive:
        assert 'DELIVERY-SUMMARY.md' not in archive.namelist()


def test_summary_does_not_copy_program_output_or_private_criteria(client, released, task_repository):
    with task_repository._session_factory() as s:
        run = s.get(PackageRun, released['id'])
        # Legitimate private diagnostic text within the existing report. It is
        # already in test-report.json but must not be copied into the new guides.
        run.result = run.result | {'private_diagnostic': 'PRIVATE-TRACE-NOT-FOR-GUIDE'}
        report = s.get(Artifact, run.report_id)
        saved = json.loads(report.content) | {'result': run.result}
        report.content = json.dumps(saved)
        report.checksum = sha256(report.content.encode()).hexdigest()
        source = s.get(Artifact, run.package_id)
        order = s.scalar(select(WorkOrder).where(WorkOrder.project_id == source.project_id))
        order.brief = order.brief | {'acceptance_criteria': ['PRIVATE-CRITERION-NOT-FOR-GUIDE']}
        s.commit()
    response = client.get(f"/api/package-runs/{released['id']}/handoff", headers=OWNER_HEADERS)
    assert response.status_code == 200, response.text
    assert 'PRIVATE-TRACE' not in response.text
    assert 'PRIVATE-CRITERION' not in response.text
    assert 'Sprawdzony zakres' not in response.text
    # No automatic test execution or inferred defect count.
    assert response.json()['delivery_summary']['verified_http_examples'] is None


def test_only_validated_selected_examples_are_counted_without_disclosing_details(client, generated, simulation):
    params, done = cycle_passed(client, generated, simulation)
    assert review(client, params['task_id'], True).status_code == 200
    path = f"/api/package-runs/{done['test_run_id']}"
    assert client.post(path + '/release', headers=OWNER_HEADERS).status_code == 200
    calls = (simulation[0].calls, len(simulation[1].calls), len(generated[2].calls))
    data = client.get(path + '/handoff', headers=OWNER_HEADERS).json()
    assert data['delivery_summary']['verified_http_examples'] == 1
    guide = data['guides']['DELIVERY-SUMMARY.md']
    assert '1 explicitly selected HTTP example(s)' in guide
    assert '/api/estimate' not in guide and '2576' not in guide and '330' not in guide
    assert not data['delivery_summary']['business_scope_verified']
    assert calls == (simulation[0].calls, len(simulation[1].calls), len(generated[2].calls))


def test_summary_is_deterministic_and_reuses_release_guard(client, released, task_repository):
    path = f"/api/package-runs/{released['id']}"
    first = client.get(path + '/handoff', headers=OWNER_HEADERS)
    assert client.get(path + '/handoff', headers=OWNER_HEADERS).json() == first.json()
    with task_repository._session_factory() as s:
        s.get(Artifact, released['release_id']).content = 'damaged'
        s.commit()
    assert client.get(path + '/handoff', headers=OWNER_HEADERS).status_code == 409
    assert client.get(path + '/released.zip', headers=OWNER_HEADERS).status_code == 409
