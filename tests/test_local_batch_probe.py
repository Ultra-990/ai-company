import json

import pytest

from scripts import probe_local_batch as probe


@pytest.mark.parametrize('wrong', [False, True])
def test_probe_bounds_retention_keeps_authorship_and_checks_answers(tmp_path, monkeypatch, wrong):
    monkeypatch.setattr(probe, 'ROOT', tmp_path)
    monkeypatch.setattr(probe, 'check_idle', lambda: {})
    monkeypatch.setattr(probe, 'ensure_idle', lambda: None)
    monkeypatch.setattr(probe, 'local_json', lambda *args: {'models': []})
    monkeypatch.setattr(probe.subprocess, 'check_output', lambda *args, **kwargs: '')
    monkeypatch.setattr(probe, 'configuration', lambda: {'model': 'fixture', 'digest': 'f'*64})
    monkeypatch.setattr(probe.tempfile, 'mkdtemp', lambda **kwargs: str(tmp_path))
    seen = []
    class Provider:
        def __init__(self, config): self.config = config
        def complete(self, messages):
            index = len(seen) % 3
            seen.append(self.config['keep_alive_seconds'])
            assert 'Return only' in messages[0]['content']
            assert self.config['num_predict'] == 128
            return {'content': json.dumps({'result': -1 if wrong else probe.TASKS[index][1]}),
                    'model': 'fixture', 'digest': 'f'*64, 'elapsed_seconds': 1, 'timings_ns': {}}
    monkeypatch.setattr(probe, 'OllamaProvider', Provider)
    out, report = probe.run()
    assert out == tmp_path
    assert report['status'] == ('failed' if wrong else 'completed')
    assert seen == ([0] if wrong else [0, 0, 0, 15, 15, 1])
    assert not report['autonomy_qualified'] and not report['production_changed']
    assert all((tmp_path/name).is_file() for name in report['artifacts'])
