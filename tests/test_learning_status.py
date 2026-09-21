from datetime import datetime, timedelta, timezone
import json

import pytest

from app.services import learning_status
from tests.conftest import OWNER_HEADERS, WORKER_HEADERS


def report(tmp_path, monkeypatch):
    path = tmp_path/'state.json'; monkeypatch.setattr(learning_status, 'STATE', path)
    data = {'schema': 'learning-autopilot.v1', 'phase': 'collecting_reviewed_data',
            'checked_at': datetime.now(timezone.utc).isoformat(),
            'counts': {'train': 2, 'validation': 0, 'test': 0}, 'training_started': False,
            'automatic_weight_training_available': False, 'entries': {'private/path': 'private prompt'},
            'errors': [], 'skipped': []}
    path.write_text(json.dumps(data)); return path, data


def test_learning_status_is_owner_only_and_never_exposes_private_inputs(client, tmp_path, monkeypatch):
    report(tmp_path, monkeypatch)
    assert client.get('/api/learning/status').status_code == 401
    assert client.get('/api/learning/status', headers=WORKER_HEADERS).status_code == 403
    result = client.get('/api/learning/status', headers=OWNER_HEADERS)
    assert result.status_code == 200 and result.headers['cache-control'] == 'no-store'
    assert result.json()['counts']['train'] == 2 and result.json()['fresh'] is True
    assert 'private' not in result.text
    assert result.json()['training_started'] is False


def test_stale_learning_report_does_not_claim_live_activity(tmp_path, monkeypatch):
    path, data = report(tmp_path, monkeypatch)
    data['checked_at'] = (datetime.now(timezone.utc)-timedelta(hours=1)).isoformat()
    path.write_text(json.dumps(data))
    assert learning_status.status()['fresh'] is False


@pytest.mark.parametrize('change', [{'training_started': True}, {'counts': {'train': True}}, {'checked_at': 'bad'}])
def test_invalid_learning_report_is_not_silently_shown_as_training(tmp_path, monkeypatch, change):
    path, data = report(tmp_path, monkeypatch); data.update(change); path.write_text(json.dumps(data))
    with pytest.raises(ValueError): learning_status.status()
