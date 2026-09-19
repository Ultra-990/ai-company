import hashlib
import json
from pathlib import Path

import pytest

from scripts import qwen_qlora_smoke as smoke


def test_fixture_is_independent_of_pending_dataset_and_arithmetic_correct():
    rows = smoke.synthetic_messages()
    assert len(rows) == 4
    for messages in rows:
        assert [m['role'] for m in messages] == ['system', 'user', 'assistant']
        parts = messages[1]['content'].removeprefix('Calculate ').removesuffix('.').split(' + ')
        assert int(messages[2]['content']) == sum(map(int, parts))
    assert hashlib.sha256(json.dumps(rows).encode()).hexdigest() == hashlib.sha256(json.dumps(smoke.synthetic_messages()).encode()).hexdigest()


def test_smoke_rejects_application_environment(monkeypatch):
    monkeypatch.setattr(smoke.sys, 'prefix', '/not-the-training-environment')
    with pytest.raises(RuntimeError, match='isolated'):
        smoke.configure()


def test_model_revision_and_download_allowlist():
    assert len(smoke.REVISION) == 40
    assert int(smoke.REVISION, 16) > 0
    assert 'model.safetensors' in smoke.FILES
    assert not any(Path(name).suffix in ('.py', '.bin', '.pt') for name in smoke.FILES)


def test_smoke_has_no_import_time_training_or_download():
    # Import above succeeded in application venv, where training packages do not exist.
    assert callable(smoke.run_smoke) and callable(smoke.download)
