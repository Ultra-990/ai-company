import copy
import json
from pathlib import Path

import pytest

from scripts.prepare_training_data import DatasetError, validate_dataset, export_dataset

SEED = Path(__file__).resolve().parents[1] / 'datasets/qwen/seed-candidates.jsonl'


def rows():
    return [json.loads(line) for line in SEED.read_text().splitlines()]


def raw(data):
    return ('\n'.join(json.dumps(row) for row in data)).encode()


def approved(row):
    row['review'].update(status='approved', reviewer='test-only-reviewer',
                         reviewed_on='2026-01-01', note='Synthetic unit-test fixture only.',
                         evidence=[{'kind': 'content_review', 'reference': 'fixture', 'sha256': 'a'*64}])
    return row


def test_seed_is_valid_but_not_training_ready():
    data, report = validate_dataset(SEED.read_bytes())
    assert len(data) == 6
    assert report['counts'] == {'train': 2, 'validation': 2, 'test': 2}
    assert report['reviews'] == {'pending': 6}
    assert not report['export_ready']
    assert len(report['blocking_reasons']) == 4


@pytest.mark.parametrize('wrapped_first', [False, True])
@pytest.mark.parametrize('wrapper', [lambda task: [task], lambda task: {'wrapper': [task]},
                                    lambda task: [{'wrapper': [task]}]])
def test_singleton_list_wrappers_cannot_conceal_cross_split_task(wrapper, wrapped_first):
    task = {'facts': {'weight': 73}, 'question': 'Read supplied weight.'}
    representations = [task, wrapper(task)]
    if wrapped_first:
        representations.reverse()
    examples = [rows()[0], rows()[2]]
    for row, payload, split in zip(examples, representations, ('train', 'test')):
        row['split'] = split
        row['messages'][1]['content'] = json.dumps(payload)
    with pytest.raises(DatasetError, match='same prompt crosses dataset splits'):
        validate_dataset(raw(examples))


@pytest.mark.parametrize('split', ['train', 'validation'])
@pytest.mark.parametrize('representation', ['reserialized', 'nested', 'article', 'lines', 'fenced'])
def test_reserved_review_cannot_be_hidden_by_json_format_or_wrapper(split, representation):
    from scripts.qwen_evaluation_catalog import load_reviewer_suite
    case = load_reviewer_suite()['cases'][0]
    payload = json.loads(case['brief'])
    if representation == 'nested': payload = {'new_task_wrapper': payload}
    elif representation == 'article': payload = {'draft': case['article'], 'instruction': 'Review this.'}
    elif representation == 'lines': payload = {'draft': payload['article_lines']}
    content = json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=True)
    if representation == 'fenced': content = '```json\n'+content+'\n```'
    row = rows()[0]; row.update(split=split, family='renamed-evaluation-family')
    row['messages'][1]['content'] = content
    with pytest.raises(DatasetError, match='evaluation brief reused'):
        validate_dataset(raw([row]))
    row['split'] = 'test'
    assert validate_dataset(raw([row]))[0][0]['split'] == 'test'


def test_related_training_article_is_not_a_reserved_exam_copy():
    from scripts.technical_review_curriculum import CASES
    row = rows()[0]; row.update(split='train', family=CASES[0]['family'])
    row['messages'][1]['content'] = json.dumps({'article': CASES[0]['article'], 'sources': CASES[0]['sources']})
    assert validate_dataset(raw([row]))[0][0]['split'] == 'train'


@pytest.mark.parametrize('split', ['train', 'validation'])
@pytest.mark.parametrize('reuse', ['family', 'prompt', 'nested'])
def test_evidence_calibration_holdout_cannot_enter_general_sft(split, reuse):
    from scripts.qwen_evaluation_catalog import load_evidence_calibration_reservations

    reserved = load_evidence_calibration_reservations()[0]
    row = rows()[0]
    row.update(split=split, family='renamed-evidence-calibration-family')
    if reuse == 'family':
        row['family'] = reserved['family']
    elif reuse == 'prompt':
        row['messages'][1]['content'] = reserved['brief']
    else:
        row['messages'][1]['content'] = json.dumps(
            {'renamed_wrapper': json.loads(reserved['brief'])}, ensure_ascii=False)
    with pytest.raises(DatasetError, match=(
            'reserved evaluation family' if reuse == 'family' else 'evaluation brief reused')):
        validate_dataset(raw([row]))


def test_unrelated_general_training_stays_allowed_after_evidence_reservation():
    row = rows()[0]
    row.update(split='train', family='unrelated-synthetic-evidence-task')
    row['messages'][1]['content'] = json.dumps({
        'facts': [{'id': 'X1', 'text': 'A fictional parcel is blue.'}],
        'question': 'Repeat the explicitly supplied color without inference.'})
    assert validate_dataset(raw([row]))[0][0]['family'] == row['family']


def test_evidence_calibration_holdout_remains_allowed_as_test_archive():
    from scripts.qwen_evaluation_catalog import load_evidence_calibration_reservations

    reserved = load_evidence_calibration_reservations()[0]
    row = rows()[0]
    row.update(split='test', family=reserved['family'])
    row['messages'][1]['content'] = reserved['brief']
    checked, _ = validate_dataset(raw([row]))
    assert checked[0]['split'] == 'test'


@pytest.mark.parametrize('change', [
    lambda r: r.update(version='unknown'),
    lambda r: r.update(extra='bad'),
    lambda r: r.update(split='training'),
    lambda r: r.update(skill=[]),
    lambda r: r['source'].update(privacy_checked='yes'),
    lambda r: r['messages'][1].update(role='tool'),
    lambda r: r['messages'][2].update(content=''),
    lambda r: r['review'].update(status='approved'),
    lambda r: approved(r)['source'].update(privacy_checked=False),
    lambda r: approved(r)['review'].update(reviewed_on='2999-01-01'),
    lambda r: approved(r)['review']['evidence'][0].update(sha256='bad'),
    lambda r: approved(r).update(skill='coding'),
    lambda r: approved(r).update(skill='repair'),
])
def test_invalid_metadata_is_rejected(change):
    data = rows()
    change(data[0])
    with pytest.raises(DatasetError):
        validate_dataset(raw(data))


def test_independent_code_evidence_required_but_not_executed():
    row = approved(rows()[0])
    row['skill'] = 'coding'
    row['review']['evidence'][0]['kind'] = 'independent_test'
    row['review']['evidence'][0]['reference'] = 'not-opened-or-executed.py'
    assert validate_dataset(raw([row]))[0][0]['skill'] == 'coding'


@pytest.mark.parametrize('kind', ['id', 'family', 'prompt', 'conversation'])
def test_leakage_and_duplicates_rejected(kind):
    data = rows()
    if kind == 'id':
        data[2]['id'] = data[0]['id']
    elif kind == 'family':
        data[2]['family'] = data[0]['family']
    elif kind == 'prompt':
        data[2]['messages'][1]['content'] = '  ' + data[0]['messages'][1]['content'].upper() + '  '
    else:
        data[1]['messages'] = copy.deepcopy(data[0]['messages'])
    with pytest.raises(DatasetError):
        validate_dataset(raw(data))


@pytest.mark.parametrize('split', ['validation', 'test'])
@pytest.mark.parametrize('representation', ['reserialized', 'nested', 'fenced'])
@pytest.mark.parametrize('reverse', [False, True])
def test_unregistered_task_cannot_cross_splits_by_reserialization(split, representation, reverse):
    first = rows()[0]
    second = copy.deepcopy(first)
    second.update(id='new-holdout', family='new-holdout', split=split)
    task = {'instruction': 'Return the fixture color.',
            'facts': [{'id': 'fixture', 'color': 'copper', 'count': 7}]}
    first['messages'][1]['content'] = json.dumps(task)
    payload = {'outer': {'renamed': task}} if representation == 'nested' else task
    content = json.dumps(payload, sort_keys=True, indent=2)
    if representation == 'fenced': content = '```json\n' + content + '\n```'
    second['messages'][1]['content'] = content
    second['messages'][2]['content'] = 'Changed answer cannot conceal the same task.'
    pair = [second, first] if reverse else [first, second]
    with pytest.raises(DatasetError, match='same prompt crosses'):
        validate_dataset(raw(pair))


def test_reserialized_task_cannot_cross_separate_batches(tmp_path):
    from scripts.prepare_training_data import load_batches
    first, second = rows()[0], rows()[2]
    task = {'facts': {'weight': 73}, 'question': 'Read the supplied weight.'}
    first['messages'][1]['content'] = json.dumps(task)
    second['messages'][1]['content'] = json.dumps({'renamed': task}, indent=2)
    a, b = tmp_path/'a.jsonl', tmp_path/'b.jsonl'
    a.write_bytes(raw([first])); b.write_bytes(raw([second]))
    with pytest.raises(DatasetError, match='same prompt crosses'):
        load_batches([a, b])


@pytest.mark.parametrize('change', ['number', 'key', 'list_order'])
def test_task_identity_preserves_meaningful_json_differences(change):
    first, second = rows()[0], rows()[2]
    task = {'facts': {'weight': 73}, 'steps': ['inspect', 'ship']}
    changed = copy.deepcopy(task)
    if change == 'number': changed['facts']['weight'] = 74
    elif change == 'key': changed['facts'] = {'volume': 73}
    else: changed['steps'].reverse()
    first['messages'][1]['content'] = json.dumps(task)
    second['messages'][1]['content'] = json.dumps(changed)
    assert len(validate_dataset(raw([first, second]))[0]) == 2


def test_reserialized_duplicate_in_same_split_rejected():
    first, second = rows()[0], rows()[1]
    task = {'question': 'Read count', 'count': 73}
    first['messages'][1]['content'] = json.dumps(task)
    second['messages'][1]['content'] = json.dumps(task, indent=2, sort_keys=True)
    second['messages'][2]['content'] = first['messages'][2]['content']
    with pytest.raises(DatasetError, match='duplicate example'):
        validate_dataset(raw([first, second]))


@pytest.mark.parametrize('data', [b'', b'null', b'{', b'{"id":1,"id":2}', b'NaN', b'\xff'])
def test_bad_input_rejected(data):
    with pytest.raises(DatasetError):
        validate_dataset(data)


def test_export_does_not_write_pending_data(tmp_path):
    before = set(tmp_path.iterdir())
    data, report = validate_dataset(SEED.read_bytes())
    with pytest.raises(DatasetError):
        export_dataset(data, report, tmp_path)
    assert set(tmp_path.iterdir()) == before


def test_forged_ready_report_cannot_bypass_approval(tmp_path):
    before = set(tmp_path.iterdir())
    data, report = validate_dataset(SEED.read_bytes())
    report['export_ready'] = True
    with pytest.raises(DatasetError):
        export_dataset(data, report, tmp_path)
    assert set(tmp_path.iterdir()) == before


def ready_rows():
    result = []
    from scripts.prepare_training_data import MINIMUMS
    for split, count in MINIMUMS.items():
        for i in range(count):
            row = approved(rows()[0])
            row.update(id=f'{split}-{i}', family=f'{split}-{i}', split=split)
            row['messages'][1]['content'] = f'Synthetic fixture {split} {i}'
            result.append(row)
    return result


def test_export_separates_splits_and_never_overwrites(tmp_path, monkeypatch):
    from scripts import prepare_training_data as module
    monkeypatch.setattr(module, 'WORKSPACES', tmp_path)
    data, report = validate_dataset(raw(ready_rows()))
    first = export_dataset(data, report, tmp_path)
    second = export_dataset(data, report, tmp_path)
    assert first != second
    for split, count in module.MINIMUMS.items():
        exported = [json.loads(line) for line in (first / f'{split}.jsonl').read_text().splitlines()]
        assert len(exported) == count
        assert all(f'fixture {split} ' in row['messages'][1]['content'] for row in exported)
    manifest = json.loads((first / 'manifest.json').read_text())
    assert not manifest['training_started']
    assert manifest['input_sha256'] == report['sha256']


def test_export_rejects_outside_root_and_symlink(tmp_path, monkeypatch):
    from scripts import prepare_training_data as module
    base = tmp_path / 'allowed'
    base.mkdir()
    outside = tmp_path / 'outside'
    outside.mkdir()
    (base / 'link').symlink_to(outside, target_is_directory=True)
    monkeypatch.setattr(module, 'WORKSPACES', base)
    data, report = validate_dataset(raw(ready_rows()))
    for root in (outside, base / 'link'):
        with pytest.raises(DatasetError):
            export_dataset(data, report, root)
    assert not list(outside.iterdir())


def test_batches_share_one_leakage_gate_and_count_approved(tmp_path):
    from scripts.prepare_training_data import load_batches
    first, second = tmp_path/'first.jsonl', tmp_path/'second.jsonl'
    data=rows()
    first.write_bytes(raw([approved(data[0])]))
    second.write_bytes(raw(data[1:]))
    combined,report=load_batches([first,second])
    assert len(combined)==6 and report['approved_counts']=={'train':1,'validation':0,'test':0}
    assert report['missing_approved']=={'train':199,'validation':25,'test':50}
    assert len(report['batches'])==2 and not report['export_ready']
    data[2]['family']=data[0]['family']
    second.write_bytes(raw(data[2:]))
    with pytest.raises(DatasetError,match='family crosses'):
        load_batches([first,second])


def test_duplicate_batch_and_combined_size_rejected(tmp_path,monkeypatch):
    from scripts import prepare_training_data as module
    first,second=tmp_path/'first.jsonl',tmp_path/'second.jsonl'
    first.write_bytes(raw(rows()[:1]));second.write_bytes(raw(rows()[1:2]))
    with pytest.raises(DatasetError,match='duplicate batch'):
        module.load_batches([first,first])
    monkeypatch.setattr(module,'MAX_BYTES',max(first.stat().st_size,second.stat().st_size)+1)
    with pytest.raises(DatasetError,match='combined dataset'):
        module.load_batches([first,second])
