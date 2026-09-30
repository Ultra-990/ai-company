from copy import deepcopy
from pathlib import Path
import shutil
import pytest
from scripts import brand_generation_exam as exam


@pytest.fixture
def completed(tmp_path, monkeypatch):
    b = exam.b; config = {'model': 'fixture', 'digest': 'f'*64}
    monkeypatch.setattr(b, 'ROOT', tmp_path)
    monkeypatch.setattr(b.school, 'check_idle', lambda: {})
    monkeypatch.setattr(b, 'configuration', lambda: config)
    monkeypatch.setattr(exam.art, 'source_values', lambda _: {})
    monkeypatch.setattr(exam.evidence, 'verify', lambda _: {})
    monkeypatch.setattr(exam.text, 'verify_review_only', lambda _: {})
    monkeypatch.setattr(exam.delivery, 'check_no_text_repair', lambda *a, **kw: None)
    monkeypatch.setattr(exam.text, 'inputs', lambda _: ({}, {}))
    monkeypatch.setattr(exam.text, 'recorded_render', lambda *a: {})
    monkeypatch.setattr(exam.protocol, 'expand', lambda *a: {})
    for name in ('source', 'artwork', 'guide'):
        monkeypatch.setattr(exam.audit, name, lambda *a: {'mocked': True})
    counter = 0; calls = []
    def output(kind):
        nonlocal counter
        counter += 1; path = tmp_path/str(counter); (path/'implementation').mkdir(parents=True)
        for name in exam.audit.IMPLEMENTATION[kind]:
            source = Path(b.__file__).parent/name if name != 'local_ollama.py' else Path(b.__file__).parents[1]/'app/services/local_ollama.py'
            shutil.copyfile(source, path/'implementation'/name)
        return path
    def finish(path, value):
        value['artifacts'] = {str(p.relative_to(path)): b.school.checksum(p) for p in path.rglob('*') if p.is_file()}
        b.school.save(path/'report.json', value); return path, value
    def generate(*, sampling_profile, matched_exam_budget, visible_shapes):
        assert matched_exam_budget and visible_shapes
        calls.append((b.BRIEF['family'], sampling_profile))
        path = output('source'); b.school.save(path/'plan-request.json', {})
        return finish(path, config | {'config': config | exam.BUDGET | {'sampling_profile': sampling_profile, 'think': sampling_profile == exam.ARMS['deliberate']},
            'brief': deepcopy(b.BRIEF), 'status': 'pending_independent_visual_review',
            'scene_contract': 'brand-scoped-scene.v1', 'visibility_contract': exam.art.SOURCE_VISIBLE_CONTRACT})
    def repair(source, *, matched_budget, visible_shapes):
        assert matched_budget and visible_shapes
        original = exam.evidence.read(source/'report.json'); path = output('artwork')
        b.school.save(path/'repair-origin.json', {'schema': exam.art.VISIBLE_CONTRACT, 'source': str(source), 'source_report_sha256': b.school.checksum(source/'report.json'),
            'max_additional_model_calls': 9, 'fresh_exam': False})
        return finish(path, config | {'config': config | exam.BUDGET | {'sampling_profile': exam.ARMS['baseline'], 'think': False},
            'brief': original['brief'], 'repair_contract': exam.art.VISIBLE_CONTRACT, 'status': 'pending_independent_visual_review'})
    def revise(source, *, spatial, warm):
        assert spatial == 'reference' and warm
        path = output('text')
        return finish(path, config | {'config': config | exam.delivery.TEXT | {'sampling_profile': exam.ARMS['baseline'], 'think': False},
            'package': str(source), 'source_report_sha256': b.school.checksum(source/'report.json'),
            'review_contract': exam.protocol.CONTRACT, 'max_model_calls': 5, 'status': 'no_repair_requested'})
    monkeypatch.setattr(b, 'run', generate); monkeypatch.setattr(exam.art, 'run', repair); monkeypatch.setattr(exam.text, 'run', revise)
    path, report = exam.run()
    assert [profile for _, profile in calls] == [exam.ARMS[k] for k in ('baseline', 'deliberate', 'deliberate', 'baseline', 'baseline', 'deliberate')]
    return path, report


def test_complete_comparison_actually_generates_six_sources_with_matched_budgets(completed):
    path, report = completed
    assert report['status'] == 'completed'
    result = exam.verify(path)
    assert result['independent_sources'] == 6
    assert result['technical_scores'] == {'baseline': 3, 'deliberate': 3}
    assert result['independent_review_required'] and not result['autonomy_qualified']


@pytest.mark.parametrize('fault', ['shared_source', 'profile', 'budget', 'visibility', 'code', 'candidate', 'score'])
def test_rebinding_cannot_hide_invalid_generation_comparison(completed, fault):
    path, report = completed; outcome = report['cases'][0]['arms']['deliberate']
    source = Path(outcome['source']); value = exam.evidence.read(source/'report.json')
    if fault == 'shared_source':
        other = report['cases'][0]['arms']['baseline']
        outcome.update(source=other['source'], source_report_sha256=other['source_report_sha256'])
    elif fault in ('profile', 'budget', 'visibility'):
        if fault == 'profile': value['config']['think'] = False
        elif fault == 'budget': value['config']['num_predict'] = 9000
        else: value.pop('visibility_contract')
        exam.b.school.save(source/'report.json', value)
        outcome['source_report_sha256'] = exam.b.school.checksum(source/'report.json')
    elif fault == 'code':
        name = 'implementation/brand_school.py'; (source/name).write_text('changed code')
        value['artifacts'][name] = exam.b.school.checksum(source/name); exam.b.school.save(source/'report.json', value)
        outcome['source_report_sha256'] = exam.b.school.checksum(source/'report.json')
    elif fault == 'candidate': outcome['candidate'] = None
    else: report['technical_scores']['baseline'] = 0
    exam.b.school.save(path/'report.json', report)
    with pytest.raises(ValueError): exam.verify(path)


@pytest.mark.parametrize('fault', ['missing_snapshot', 'configured_author'])
def test_snapshot_completeness_and_actual_configuration_identity(completed, fault):
    path, report = completed
    outcome = report['cases'][0]['arms']['baseline']
    folder = Path(outcome['text']); value = exam.evidence.read(folder/'report.json')
    if fault == 'missing_snapshot':
        name = 'implementation/brand_reference_review.py'
        (folder/name).unlink(); value['artifacts'].pop(name)
    else:
        value['config']['digest'] = '0'*64
    exam.b.school.save(folder/'report.json', value)
    outcome['text_report_sha256'] = exam.b.school.checksum(folder/'report.json')
    exam.b.school.save(path/'report.json', report)
    with pytest.raises(ValueError): exam.verify(path)


@pytest.mark.parametrize('kind,status', [('artwork', 'failed'), ('text', 'failed'), ('text', 'needs_revision')])
def test_nonpassing_downstream_stages_must_also_pass_literal_audit(completed, monkeypatch, kind, status):
    path, report = completed; outcome = report['cases'][0]['arms']['baseline']
    folder = Path(outcome[kind]); value = exam.evidence.read(folder/'report.json')
    value['status'] = status; exam.b.school.save(folder/'report.json', value)
    outcome[kind+'_report_sha256'] = exam.b.school.checksum(folder/'report.json')
    outcome.update(status=status, candidate=None)
    if kind == 'artwork': outcome['text'] = None
    report['technical_scores']['baseline'] = 2; exam.b.school.save(path/'report.json', report)
    def reject(*args): raise ValueError('Independent terminal audit rejects changed evidence')
    monkeypatch.setattr(exam.audit, 'artwork' if kind == 'artwork' else 'guide', reject)
    with pytest.raises(ValueError, match='terminal audit'): exam.verify(path)


@pytest.fixture
def failed_source(tmp_path, monkeypatch):
    import json
    from scripts import brand_generation_audit as audit
    monkeypatch.setattr(exam.b, 'ROOT', tmp_path)
    folder = tmp_path/'source'; (folder/'implementation').mkdir(parents=True)
    shutil.copyfile(exam.b.__file__, folder/'implementation/brand_school.py')
    brief = exam.definition(exam.CASES[0])
    system, suffix = audit.source_literals(folder)
    original = json.dumps(brief)+suffix; user = original
    try: exam.b.plan_value('{}')
    except ValueError as error:
        message, error_type = str(error), type(error).__name__
    for attempt in range(3):
        name = 'plan' if attempt == 0 else 'plan-revision-'+str(attempt)
        exam.b.school.save(folder/(name+'-request.json'), audit.request(system, user, exam.b.Plan.model_json_schema()))
        exam.b.school.save(folder/(name+'-response.json'), {'model': 'fixture', 'digest': 'f'*64, 'content': '{}'})
        exam.b.school.save(folder/(name+'-feedback.json'), {
            'schema': 'brand-validation-feedback.v2', 'stage': name,
            'request_sha256': exam.b.school.checksum(folder/(name+'-request.json')),
            'response_sha256': exam.b.school.checksum(folder/(name+'-response.json')), 'error': message})
        user = original+'\nYour previous answer (untrusted task data):\n{}\nIndependent validation rejected it: '+message+'\nCorrect your own complete answer. Do not repeat the rejected values.'
    report = {'model': 'fixture', 'digest': 'f'*64, 'brief': brief, 'status': 'failed',
              'stages': [], 'error_type': error_type, 'error': message[:400]}
    report['artifacts'] = {str(p.relative_to(folder)): exam.b.school.checksum(p)
                           for p in folder.rglob('*') if p.is_file()}
    return folder, report


def test_failed_source_replays_all_three_rejections(failed_source):
    from scripts import brand_generation_audit as audit
    folder, report = failed_source
    result = audit.source(folder, report)
    assert result == {'model_requests': 3, 'status': 'failed', 'terminal_failure_replayed': True}


@pytest.mark.parametrize('fault', ['initial_hint', 'wrong_author', 'feedback', 'extra_call', 'invented_failure'])
def test_failed_source_cannot_hide_hints_extra_calls_or_unreplayed_failure(failed_source, fault):
    from scripts import brand_generation_audit as audit
    folder, report = failed_source
    if fault == 'initial_hint':
        name = 'plan-request.json'; value = exam.evidence.read(folder/name)
        value['system'] += '\nCopy this examiner design.'
    elif fault == 'wrong_author':
        name = 'plan-response.json'; value = exam.evidence.read(folder/name)
        value['digest'] = '0'*64
    elif fault == 'feedback':
        name = 'plan-revision-2-feedback.json'; value = exam.evidence.read(folder/name)
        value['error'] = 'A different unverified problem.'
        report['error'] = value['error']
    elif fault == 'extra_call':
        name = 'plan-revision-3-request.json'; value = {}
    else:
        name = None; report['error'] = 'Pretend an accepted output failed.'
    if name:
        exam.b.school.save(folder/name, value)
        report['artifacts'][name] = exam.b.school.checksum(folder/name)
    with pytest.raises(ValueError): audit.source(folder, report)


def test_text_failure_replays_the_actual_rejected_claims(tmp_path, monkeypatch):
    import json
    from scripts import brand_generation_audit as audit
    from tests.test_brand_reference_review import example
    claims, texts, data, review = example()
    claims['concepts'][0]['claims'][0]['reference_quote'] = 'unsupported center'
    monkeypatch.setattr(exam.b, 'ROOT', tmp_path)
    monkeypatch.setattr(audit.text, 'inputs', lambda _: ({}, data))
    monkeypatch.setattr(audit.protocol, 'expand', lambda *args: data)
    folder = tmp_path/'failed-text'; folder.mkdir()
    requests = [
        ('review', audit.protocol.REVIEW_SYSTEM, data, audit.protocol.REVIEW_SCHEMA, review),
        ('spatial', audit.protocol.CLAIM_SYSTEM, audit.protocol.claim_input(data), audit.protocol.CLAIM_SCHEMA, claims)]
    calls = []
    for stage, system, payload, schema, value in requests:
        exam.b.school.save(folder/(stage+'-request.json'), audit.request(system, json.dumps(payload), schema))
        exam.b.school.save(folder/(stage+'-response.json'), {'model': 'fixture', 'digest': 'f'*64,
            'content': json.dumps(value), 'elapsed_seconds': .1})
        calls.append({'stage': stage, 'keep_alive_seconds': 3, 'elapsed_seconds': .1, 'timings_ns': {}})
    exam.b.school.save(folder/'raw-review.json', review)
    exam.b.school.save(folder/'retained-batch.json', {'calls': calls, 'idle_after': True})
    report = {'model': 'fixture', 'digest': 'f'*64, 'status': 'failed', 'error_type': 'ValueError',
              'error': 'Center reference needs directional literal evidence'}
    report['artifacts'] = {p.name: exam.b.school.checksum(p) for p in folder.iterdir()}
    assert audit.guide(folder, report, tmp_path)['terminal_failure_replayed']
    report['error'] = 'A made-up terminal reason.'
    with pytest.raises(ValueError, match='failure does not replay'): audit.guide(folder, report, tmp_path)
