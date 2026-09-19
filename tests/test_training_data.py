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
