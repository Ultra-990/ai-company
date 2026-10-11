"""Offline checks for the pinned full-revision canary wrapper."""
import json
from hashlib import sha256
import os
from pathlib import Path

import pytest

from app.services.application_profile import PROFILE,REPAIR_PROFILE
from scripts import filewise_production_canary_case as case
from scripts import filewise_production_canary_revision as revision


def test_revision_is_full_profile_and_pins_all_inputs():
    data=revision.revision_input('00000000-0000-0000-0000-000000000001')
    assert PROFILE=='python-web-v1' and PROFILE!=REPAIR_PROFILE
    assert data['package_id']==3 and data['package_checksum']==revision.PACKAGE_CHECKSUM
    assert data['auto_test'] is True and len(data['evidence'])==3
    assert 'H(None, None, None)' in data['description']
    assert 'pełną nową wersję wszystkich źródeł' in data['description']
    assert 'Co najmniej sześć' in data['expected_result']


def test_revision_keeps_public_contract_and_frozen_harness():
    source=case.harness_source()
    assert sha256(source.encode()).hexdigest()==revision.HARNESS_SHA256
    prompt=json.dumps({'description':revision.DESCRIPTION,'expected':revision.EXPECTED},ensure_ascii=False)
    for required in ('/health','duplikat','dodatkowy parametr','404','encodeURIComponent',
                     'textContent','aria-live','brak zapisu'):
        assert required in prompt
    assert len(case.PROBES)==6


@pytest.mark.skipif(not os.environ.get('AIC_FILEWISE_CANARY_REVISION_SOURCE'),
    reason='Pinned local canary history requires an explicit source directory')
def test_real_revision_source_hashes_match_pinned_history(monkeypatch):
    monkeypatch.setattr(revision,'SOURCE',Path(os.environ['AIC_FILEWISE_CANARY_REVISION_SOURCE']))
    revision.validate_source()
    assert case.harness_source()==(revision.SOURCE/'independent-harness.py').read_text(encoding='utf-8')
