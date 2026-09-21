"""CPU contract tests; no model outputs or synthetic test fixtures enter training."""
import json
from pathlib import Path

import pytest

from scripts import train_vision_corpus as corpus


def test_schedule_covers_every_record_once_and_keeps_short_last_group():
    groups = corpus.schedule(71)
    assert len(groups) == 18 and len(groups[-1]) == 3
    assert sorted(i for group in groups for i in group) == list(range(71))
    assert groups == corpus.schedule(71)
    for invalid in (0, 1, 129, True):
        with pytest.raises(ValueError): corpus.schedule(invalid)
    plan = corpus.load_protocol()
    assert plan['automatic_promotion'] is False and plan['production_data_gate_changed'] is False


def prepared_fixture(tmp_path, monkeypatch, *, duplicate=False, family='fixture-train', image='a'*64, audit=True, split='train'):
    from scripts import learning_autopilot as intake
    from scripts import check_vision_training_inputs as inputs
    from scripts import vector_exam as exam
    bundle = tmp_path/'bundle'; bundle.mkdir()
    (bundle/'records.jsonl').write_text('fixture'); (bundle/'manifest.json').write_text('{}')
    rows = [{'id': 'same' if duplicate else f'row-{i}', 'family': family, 'split': split,
             'images': [{'sha256': image}]} for i in range(2)]
    monkeypatch.setattr(inputs, 'verify_bundle', lambda p: rows)
    monkeypatch.setattr(intake, 'cached_valid', lambda entry, expected: audit)
    state = tmp_path/'state.json'; state.write_text(json.dumps({'schema': 'learning-autopilot.v1',
        'entries': {'fixture': {'bundle': str(bundle), 'audit': {'path': 'fixture', 'sha256': 'c'*64}}}}))
    definition = {'data_split': 'validation', 'family': 'fixture-validation', 'cases': [{'id': i, 'kind': 'fixture'} for i in range(25)]}
    monkeypatch.setattr(exam, 'load_exam', lambda p: (definition, None, None))
    exam_path = tmp_path/'exam.json'; exam_path.write_text('{}')
    for i in range(25):
        folder = tmp_path/f'case-{i:02d}'; folder.mkdir()
        (folder/'request.json').write_text(json.dumps({'image': {'path': 'fixture', 'sha256': 'b'*64}}))
    return state, exam_path


@pytest.mark.parametrize('defect', ['duplicate', 'family', 'image', 'audit', 'split'])
def test_corpus_rejects_repeats_leakage_and_unreviewed_inputs(tmp_path, monkeypatch, defect):
    kwargs = {'duplicate': defect == 'duplicate', 'family': 'fixture-validation' if defect == 'family' else 'fixture-train',
              'image': 'b'*64 if defect == 'image' else 'a'*64, 'audit': defect != 'audit',
              'split': 'test' if defect == 'split' else 'train'}
    state, exam = prepared_fixture(tmp_path, monkeypatch, **kwargs)
    with pytest.raises(ValueError): corpus.prepare(state, exam)


def test_preflight_collects_all_verified_records_without_starting_training(tmp_path, monkeypatch):
    state, exam = prepared_fixture(tmp_path, monkeypatch)
    result = corpus.prepare(state, exam)
    assert len(result['entries']) == 2 and len(result['validation']) == 25
    assert result['training_started'] is False
    assert result['exam_sha256'] == corpus.digest(exam)


def assessment_fixture(tmp_path, monkeypatch):
    from scripts import vector_exam as exam
    adapter = tmp_path/'adapter'; adapter.mkdir(); (adapter/'adapter_model.safetensors').write_bytes(b'fixture')
    exam_path = tmp_path/'exam.json'; exam_path.write_text('{}')
    cases = [{'id': i, 'kind': 'attribute_restoration' if i < 24 else 'whole_recreation'} for i in range(25)]
    monkeypatch.setattr(exam, 'load_exam', lambda p: ({'cases': cases}, 'fixture', {}))
    monkeypatch.setattr(exam, 'score', lambda raw, *args: {'passed': raw == 'base'})
    data = {'exam': str(exam_path), 'exam_sha256': corpus.digest(exam_path),
            'validation': [{'request': {'image': {'path': 'fixture'}}} for _ in cases]}
    (tmp_path/'input.json').write_text(json.dumps(data))
    report = {'status': 'completed_pending_independent_scoring', 'input_sha256': corpus.digest(tmp_path/'input.json'),
              'adapter': str(adapter), 'adapter_sha256': corpus.digest(adapter/'adapter_model.safetensors'), 'results': []}
    for phase in ('base', 'adapter'):
        for i in range(25):
            report['results'].append({'phase': phase, 'id': i, 'content': phase,
                'response_sha256': corpus.sha256(phase.encode()).hexdigest(), 'stop_token_seen': True,
                'input_ids_sha256': 'i'*64, 'pixel_values_sha256': 'p'*64, 'prompt_sha256': 'm'*64})
    (tmp_path/'report.json').write_text(json.dumps(report)); return report


@pytest.mark.parametrize('defect', ['unmatched_pixels', 'missing_response', 'changed_response'])
def test_comparison_refuses_unmatched_or_changed_evidence(tmp_path, monkeypatch, defect):
    report = assessment_fixture(tmp_path, monkeypatch)
    if defect == 'unmatched_pixels': report['results'][0]['pixel_values_sha256'] = 'different'
    elif defect == 'missing_response': report['results'].pop()
    else: report['results'][0]['content'] = 'changed'
    (tmp_path/'report.json').write_text(json.dumps(report))
    with pytest.raises(ValueError): corpus.assess(tmp_path)


def test_a_regression_is_reported_without_promoting_adapter(tmp_path, monkeypatch):
    assessment_fixture(tmp_path, monkeypatch)
    result = corpus.assess(tmp_path)
    assert result['totals'] == {'base': {'attribute_restoration': 24, 'whole_recreation': 1},
                                'adapter': {'attribute_restoration': 0, 'whole_recreation': 0}}
    assert result['automatic_promotion'] is False and result['production_ready'] is False


@pytest.mark.parametrize('exit_code', [0, 1])
def test_run_scores_only_after_successful_worker_exit(tmp_path, monkeypatch, exit_code):
    from scripts import compare_local_models
    from types import SimpleNamespace
    monkeypatch.setattr(corpus, 'ROOT', tmp_path)
    monkeypatch.setattr(corpus, 'prepare', lambda *args: {'entries': [], 'schedule': []})
    monkeypatch.setattr(compare_local_models, 'check_idle', lambda: {'fixture': True})
    completed = []
    def worker(*args, **kwargs):
        completed.append('worker-exited')
        return SimpleNamespace(returncode=exit_code)
    monkeypatch.setattr(corpus.subprocess, 'run', worker)
    def assessment(out):
        assert completed == ['worker-exited']
        completed.append('scored')
        return {'totals': {'fixture': True}}
    monkeypatch.setattr(corpus, 'assess', assessment)
    monkeypatch.setattr(corpus.sys, 'argv', ['train_vision_corpus.py', '--state', 'fixture-state', '--exam', 'fixture-exam', '--run'])
    assert corpus.main() == exit_code
    assert completed == (['worker-exited', 'scored'] if exit_code == 0 else ['worker-exited'])
