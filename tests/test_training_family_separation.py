"""Training-only reservations must apply across imports, files and future suites."""
from hashlib import sha256
import json

import pytest

from scripts import qwen_evaluation_catalog as catalog
from scripts import training_family_registry as registry
from scripts.prepare_training_data import DatasetError, load_batches, validate_dataset
from tests.test_training_data import rows, raw


FAMILIES = ('rowerownia-query-parser-development','service-crema-responsive-nav-copy-development')


@pytest.mark.parametrize('family',FAMILIES)
@pytest.mark.parametrize('split', ['validation', 'test'])
def test_training_only_family_cannot_be_imported_as_a_separate_eval_batch(tmp_path, split,family):
    row = rows()[0]
    row.update(family=family, split=split)
    path = tmp_path / 'evaluation.jsonl'
    path.write_bytes(raw([row]))
    with pytest.raises(DatasetError, match='training-only family'):
        load_batches([path])
    row['split'] = 'train'
    assert validate_dataset(raw([row]))[0][0]['family'] == family


@pytest.mark.parametrize('loader,path_attr,hash_attr', [
    ('load_suite', 'SUITE', 'CHECKSUM'),
    ('load_role_suite', 'ROLE_SUITE', 'ROLE_CHECKSUM'),
    ('load_reviewer_suite', 'REVIEWER_SUITE', 'REVIEWER_CHECKSUM'),
])
def test_even_correctly_pinned_new_exam_cannot_use_training_family(
        tmp_path, monkeypatch, loader, path_attr, hash_attr):
    suite = getattr(catalog, loader)()
    suite['cases'][0]['family'] = FAMILIES[1]
    payload = json.dumps(suite).encode()
    path = tmp_path / 'future-suite.json'
    path.write_bytes(payload)
    monkeypatch.setattr(catalog, path_attr, path)
    monkeypatch.setattr(catalog, hash_attr, sha256(payload).hexdigest())
    with pytest.raises(ValueError, match='training-only family'):
        getattr(catalog, loader)()


def test_calibration_reservations_also_enforce_training_exclusion(monkeypatch):
    from scripts import evidence_calibration_data as evidence
    cases = evidence.cases()
    next(case for case in cases if case['split'] == 'test')['family'] = FAMILIES[1]
    payload = json.dumps(cases, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()
    monkeypatch.setattr(evidence, 'cases', lambda: cases)
    monkeypatch.setattr(catalog, 'EVIDENCE_CURRICULUM_CHECKSUM', sha256(payload).hexdigest())
    with pytest.raises(ValueError, match='training-only family'):
        catalog.load_evidence_calibration_reservations()


def test_missing_registry_blocks_dataset_and_direct_evaluation(tmp_path, monkeypatch):
    monkeypatch.setattr(registry, 'REGISTRY', tmp_path / 'missing.json')
    with pytest.raises(DatasetError, match='catalog missing or changed'):
        validate_dataset(raw(rows()))
    with pytest.raises(OSError):
        catalog.load_suite()


def test_changed_registry_cannot_silently_remove_training_reservations(tmp_path, monkeypatch):
    path = tmp_path / 'registry.json'
    path.write_text('{"version":"training-only-families.v1","usage":"evaluation_exclusion","families":[]}')
    monkeypatch.setattr(registry, 'REGISTRY', path)
    with pytest.raises(DatasetError, match='catalog missing or changed'):
        validate_dataset(raw(rows()))
    with pytest.raises(ValueError, match='registry changed'):
        catalog.load_reviewer_suite()
