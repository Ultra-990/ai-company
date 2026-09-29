from copy import deepcopy
import json
from pathlib import Path
import shutil
import tempfile

import pytest

from scripts import brand_full_exam as exam
from scripts import verify_brand_package as verifier


def test_frozen_brand_cases_are_distinct_reserved_and_restore_context():
    briefs = [exam.definition(c) for c in exam.CASES]
    assert len({b['family'] for b in briefs}) == 3
    assert all(b['split'] == 'test' and b['synthetic'] and not b['printer_specifications_supplied'] for b in briefs)
    assert all(b['contacts'][1].endswith('.example') for b in briefs)
    previous = deepcopy(exam.brand.BRIEF)
    with pytest.raises(RuntimeError):
        with exam.exercise_context(briefs[1]):
            assert exam.brand.BRIEF == briefs[1]
            raise RuntimeError('test only')
    assert exam.brand.BRIEF == previous
    with pytest.raises(ValueError):
        with exam.exercise_context(briefs[0] | {'restaurant_name': 'mutated'}): pass


@pytest.fixture
def compared(tmp_path, monkeypatch):
    b = exam.brand
    monkeypatch.setattr(b, 'ROOT', tmp_path)
    monkeypatch.setattr(b.school, 'check_idle', lambda: {})
    monkeypatch.setattr(b, 'configuration', lambda: {'model': 'fixture', 'digest': 'f'*64})
    calls = []
    def run(*, sampling_profile, matched_exam_budget):
        assert matched_exam_budget
        calls.append((b.BRIEF['family'], sampling_profile))
        out = Path(tempfile.mkdtemp(dir=tmp_path)); code = out/'implementation'; code.mkdir()
        for name in ('brand_school.py', 'render_school_svg.py', 'vector_structured_source.py', 'vector_school_contract.py'):
            shutil.copyfile(Path(b.__file__).parent/name, code/name)
        shutil.copyfile(Path(b.__file__).resolve().parents[1]/'app/services/local_ollama.py', code/'local_ollama.py')
        b.school.save(out/'plan-request.json', {'system': 'fixture', 'user': 'fixture', 'format': {}})
        report = {'brief': deepcopy(b.BRIEF), 'model': 'fixture', 'digest': 'f'*64, 'status': 'failed', 'elapsed_seconds': 1,
            'config': {'sampling_profile': sampling_profile, 'think': sampling_profile == 'qwen-deliberate-trial.v1',
                'num_ctx': 16384, 'num_predict': 8192, 'num_thread': 4, 'timeout_seconds': 180},
            'artifacts': {str(p.relative_to(out)): b.school.checksum(p) for p in out.rglob('*') if p.is_file()}}
        b.school.save(out/'report.json', report)
        return out, report
    monkeypatch.setattr(b, 'run', run)
    out, report = exam.run()
    assert len(calls) == 6
    assert [p for _, p in calls] == [exam.ARMS[a] for a in ('baseline', 'deliberate', 'deliberate', 'baseline', 'baseline', 'deliberate')]
    return out, report


def test_comparison_reports_failures_without_qualifying_service(compared):
    out, _ = compared
    result = exam.assess(out)
    assert result['technical_scores'] == {'baseline': 0, 'deliberate': 0}
    assert result['integrity_verified'] and not result['autonomy_qualified']


@pytest.mark.parametrize('fault', ['budget', 'code', 'duplicate', 'score', 'brief'])
def test_comparison_rejects_unequal_conditions_even_with_rebound_reports(compared, fault):
    out, report = compared; b = exam.brand
    result = report['cases'][0]['arms']['deliberate']; package = Path(result['package'])
    value = verifier.read(package/'report.json')
    if fault == 'score': report['scores']['deliberate'] = 1
    elif fault == 'duplicate': report['cases'][1]['arms']['deliberate'] = deepcopy(result)
    else:
        if fault == 'budget': value['config']['num_predict'] = 4096
        elif fault == 'brief': value['brief']['restaurant_name'] = 'Teacher replacement'
        else:
            path = package/'implementation/brand_school.py'; path.write_text('altered implementation')
            value['artifacts']['implementation/brand_school.py'] = b.school.checksum(path)
        b.school.save(package/'report.json', value); result['report_sha256'] = b.school.checksum(package/'report.json')
    b.school.save(out/'report.json', report)
    with pytest.raises(ValueError): exam.assess(out)


@pytest.mark.parametrize('fault', [None, 'hint', 'author', 'extra_call', 'feedback'])
def test_brand_correction_replay_protects_author_and_complete_feedback(tmp_path, monkeypatch, fault):
    b = exam.brand
    monkeypatch.setattr(b, 'ROOT', tmp_path)
    monkeypatch.setattr(b.school, 'check_idle', lambda: {})
    answers = iter(['bad', 'good'])
    class Provider:
        def __init__(self, config): pass
        def complete(self, messages): return {'model': 'fixture', 'digest': 'f'*64, 'content': next(answers)}
    monkeypatch.setattr(b, 'OllamaProvider', Provider)
    def validate(raw):
        if raw == 'bad': raise ValueError('A real synthetic test diagnostic')
        return raw
    b.validated_call(tmp_path, 'logo-a', 'fixed', 'brief', {}, {'model': 'fixture', 'digest': 'f'*64}, validate)
    if fault:
        name = 'logo-a-revision-1-request.json'
        if fault == 'author': name = 'logo-a-revision-1-response.json'
        elif fault == 'feedback': name = 'logo-a-feedback.json'
        value = verifier.read(tmp_path/name)
        if fault == 'hint': value['user'] += 'Extra coordinates from teacher.'
        elif fault == 'author': value['model'] = 'different'
        elif fault == 'feedback': value['error'] = 'Another diagnosis'
        else: name = 'logo-a-revision-2-request.json'
        b.school.save(tmp_path/name, value)
    report = {'model': 'fixture', 'digest': 'f'*64, 'artifacts': {p.name: b.school.checksum(p) for p in tmp_path.iterdir()}}
    if fault:
        with pytest.raises(ValueError): verifier.chain(tmp_path, 'logo-a', report)
    else:
        raw, checked = verifier.chain(tmp_path, 'logo-a', report)
        assert raw == 'good' and checked['corrections'] == ['logo-a'] and checked['requests'] == 2
