import json
from pathlib import Path

from scripts import learning_autopilot as auto


def fixture(tmp_path, monkeypatch):
    monkeypatch.setattr(auto, 'ROOT', tmp_path)
    monkeypatch.setattr(auto, 'sources', lambda: [('vector', Path('/fixture/review'))])
    rows = [{'id': 'one', 'family': 'fixture-family'}]
    exports = []
    def export():
        out = tmp_path/str(len(exports)); exports.append(out); return out
    monkeypatch.setattr(auto, 'collect', lambda *args: (rows, export))
    monkeypatch.setattr(auto, 'verify_bundle', lambda path: rows)
    monkeypatch.setattr(auto, 'audit', lambda path: {'path': 'fixture-proof', 'sha256': '0'*64})
    monkeypatch.setattr(auto, 'cached_valid', lambda entry, rows: bool(entry))
    return rows, exports


def test_automatic_intake_is_idempotent_and_never_claims_training(tmp_path, monkeypatch):
    _, exports = fixture(tmp_path, monkeypatch)
    first = auto.cycle(); second = auto.cycle()
    assert len(exports) == 1
    assert first['counts'] == second['counts'] == {'train': 1, 'validation': 0, 'test': 0}
    assert second['missing'] == {'train': 199, 'validation': 25, 'test': 50}
    assert second['training_started'] is False and second['automatic_weight_training_available'] is False
    assert second['model_promotion_enabled'] is False
    assert json.loads((tmp_path/'state.json').read_text()) == second


def test_revoked_review_is_removed_even_when_audit_was_cached(tmp_path, monkeypatch):
    fixture(tmp_path, monkeypatch); auto.cycle()
    def rejected(*args): raise ValueError('Review revoked')
    monkeypatch.setattr(auto, 'collect', rejected)
    result = auto.cycle()
    assert result['counts']['train'] == 0 and result['entries'] == {}
    assert result['errors'][0]['detail'] == 'Review revoked'


def test_cpu_audit_failure_does_not_count_an_export_as_usable_data(tmp_path, monkeypatch):
    fixture(tmp_path, monkeypatch)
    def failed(path): raise RuntimeError('audit failed')
    monkeypatch.setattr(auto, 'audit', failed)
    result = auto.cycle()
    assert result['counts']['train'] == 0 and len(result['errors']) == 1


def test_duplicate_experiences_are_not_counted_twice(tmp_path, monkeypatch):
    fixture(tmp_path, monkeypatch)
    monkeypatch.setattr(auto, 'sources', lambda: [('vector', Path('/one')), ('vector', Path('/two'))])
    result = auto.cycle()
    assert result['counts']['train'] == 1
    assert result['errors'] == []
    assert result['skipped'][0]['reason'] == 'duplicate_already_intaken'


def test_mixed_replayed_batch_keeps_only_new_exact_records(tmp_path, monkeypatch):
    fixture(tmp_path, monkeypatch)
    rows = {'/one': [{'id': 'one', 'family': 'fixture-family'}],
            '/mixed': [{'id': 'one', 'family': 'fixture-family'},
                       {'id': 'two', 'family': 'fixture-family'}]}
    monkeypatch.setattr(auto, 'collect', lambda kind, path:
                        (rows[str(path)], lambda path=path: path))
    monkeypatch.setattr(auto, 'verify_bundle', lambda path: rows[str(path)])
    monkeypatch.setattr(auto, 'sources', lambda: [('vector', Path('/one')),
                                                   ('vector', Path('/mixed'))])
    result = auto.cycle()
    assert result['counts']['train'] == 2
    assert result['errors'] == []
    assert result['skipped'][-1] == {'source': 'vector:/mixed',
                                      'reason': 'duplicate_rows_removed', 'count': 1}


def test_replay_with_only_private_report_path_change_is_equivalent():
    left = {'id': 'one', 'source': {'report': '/a', 'report_sha256': 'a', 'kind': 'synthetic'},
            'messages': ['same']}
    right = {'id': 'one', 'source': {'report': '/b', 'report_sha256': 'b', 'kind': 'synthetic'},
             'messages': ['same']}
    assert auto.equivalent_experience(left, right)
    right['messages'] = ['changed']
    assert not auto.equivalent_experience(left, right)


def test_complete_replayed_batch_is_skipped_without_poisoning_snapshot(tmp_path, monkeypatch):
    fixture(tmp_path, monkeypatch)
    first = auto.cycle()
    assert first['counts']['train'] == 1
    monkeypatch.setattr(auto, 'sources', lambda: [
        ('vector', Path('/one')), ('vector', Path('/one-replay'))])
    result = auto.cycle()
    assert result['counts']['train'] == 1
    assert result['errors'] == []
    assert result['skipped'][-1]['reason'] == 'duplicate_already_intaken'


def test_cycle_limits_new_cpu_audits_without_losing_previous_progress(tmp_path, monkeypatch):
    fixture(tmp_path, monkeypatch)
    sources = [('vector', Path('/'+str(i))) for i in range(3)]
    monkeypatch.setattr(auto, 'sources', lambda: sources)
    def rows(path): return [{'id': str(path), 'family': 'fixture'}]
    monkeypatch.setattr(auto, 'collect', lambda kind, path: (rows(path), lambda: path))
    monkeypatch.setattr(auto, 'verify_bundle', rows)
    assert auto.cycle()['counts']['train'] == 2
    assert auto.cycle()['counts']['train'] == 3


def test_practice_discovery_batches_at_most_sixteen_conversations(tmp_path, monkeypatch):
    monkeypatch.setattr(auto.vector.school, 'ROOT', tmp_path)
    monkeypatch.setattr(auto.interior.school, 'ROOT', tmp_path/'other')
    monkeypatch.setattr(auto.product, 'ROOT', tmp_path/'products')
    for index in range(19):
        path = tmp_path/'practice-fixture'/f'case-{index:03d}'; path.mkdir(parents=True)
        (path/'experience.json').write_text('{}')
    groups = auto.sources()
    assert [kind for kind, _ in groups] == ['vector_batch', 'vector_batch']
    assert [len(paths) for _, paths in groups] == [16, 3]
    assert len(set(path for _, paths in groups for path in paths)) == 19
    # An alphabetically earlier new series must not reshuffle completed groups
    # and invalidate their processor audits.
    other = tmp_path/'practice-earlier'/'case-000'; other.mkdir(parents=True)
    (other/'experience.json').write_text('{}')
    assert auto.sources()[1:] == groups


def test_product_intake_discovers_reviews_and_skips_rejected_layouts(tmp_path, monkeypatch):
    monkeypatch.setattr(auto.vector.school, 'ROOT', tmp_path/'vectors')
    monkeypatch.setattr(auto.interior.school, 'ROOT', tmp_path/'interiors')
    monkeypatch.setattr(auto.product, 'ROOT', tmp_path)
    folder = tmp_path/'visual-revision-fixture'; folder.mkdir()
    review = folder/'learning-review.json'; review.write_text('{"decision":"needs_visual_revision"}')
    assert auto.sources() == [('product', review)]
    assert auto.collect('product', review) == ([], None)
