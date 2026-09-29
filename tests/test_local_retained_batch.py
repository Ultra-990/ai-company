import pytest
from scripts import local_retained_batch as batch

CONFIG = {'model': 'fixture', 'digest': 'f'*64, 'timeout_seconds': 90}
RESIDENT = {'name': 'fixture', 'digest': 'f'*64, 'size_vram': 18000*1024**2}


@pytest.fixture
def state(monkeypatch):
    state = {'models': [], 'queue': {'queue_running': [], 'queue_pending': []},
             'containers': '', 'free': '31000', 'idle_checks': 0}
    def idle(): state['idle_checks'] += 1
    monkeypatch.setattr(batch, 'check_idle', idle)
    monkeypatch.setattr(batch, 'local_json', lambda port, path: {'models': state['models']} if port == 11434 else state['queue'])
    monkeypatch.setattr(batch.subprocess, 'check_output', lambda cmd, **kw: state['containers'] if cmd[0] == 'docker' else state['free'])
    return state


def test_only_model_loaded_by_this_batch_can_be_reused(state):
    assert not batch.check_resources(CONFIG, False)['resident_reused']
    assert state['idle_checks'] == 1
    state.update(models=[RESIDENT], free='13000')
    with pytest.raises(batch.PreflightFailure): batch.check_resources(CONFIG, False)
    assert batch.check_resources(CONFIG, True)['resident_reused']


@pytest.mark.parametrize('change', ['digest', 'multiple', 'container', 'queue', 'unknown_queue', 'memory', 'unknown_memory'])
def test_new_or_unknown_resource_conflicts_stop_followup_calls(state, change):
    state.update(models=[dict(RESIDENT)], free='13000')
    if change == 'digest': state['models'][0]['digest'] = 'a'*64
    elif change == 'multiple': state['models'].append(dict(RESIDENT))
    elif change == 'container': state['containers'] = 'active'
    elif change == 'queue': state['queue']['queue_running'] = ['active']
    elif change == 'unknown_queue': state['queue'] = {}
    elif change == 'memory': state['free'] = '100'
    else: state['models'][0]['size_vram'] = True
    with pytest.raises(batch.PreflightFailure): batch.check_resources(CONFIG, True)


def test_batch_reuses_then_releases_and_enforces_budget(tmp_path, monkeypatch, state):
    configs = []
    class Provider:
        def __init__(self, config): self.config = config
        def complete(self, messages):
            configs.append(self.config)
            state.update(models=[RESIDENT] if self.config['keep_alive_seconds'] else [], free='13000')
            return {'model': 'fixture', 'digest': 'f'*64, 'content': '{}', 'elapsed_seconds': .1}
    monkeypatch.setattr(batch, 'OllamaProvider', Provider)
    session = batch.RetainedBatch(CONFIG, 2)
    session.call(tmp_path, 'review', 's', 'u', {})
    session.call(tmp_path, 'final-review', 's', 'u', {}, final=True)
    with pytest.raises(ValueError): session.call(tmp_path, 'extra', 's', 'u', {})
    result = session.close()
    assert result['idle_after'] and len(result['calls']) == 2
    assert [c['keep_alive_seconds'] for c in configs] == [3, 0]
    assert result['calls'][1]['resources_before']['resident_reused']


def test_failed_transport_consumes_budget_without_retry(tmp_path, monkeypatch, state):
    class Provider:
        def __init__(self, config): pass
        def complete(self, messages): raise TimeoutError('bounded failure')
    monkeypatch.setattr(batch, 'OllamaProvider', Provider)
    session = batch.RetainedBatch(CONFIG, 1)
    with pytest.raises(TimeoutError): session.call(tmp_path, 'review', 's', 'u', {})
    with pytest.raises(ValueError): session.call(tmp_path, 'again', 's', 'u', {})
    assert session.close()['idle_after']


def test_early_exit_waits_for_natural_expiry_without_eviction(monkeypatch):
    sequence = iter([[RESIDENT], [RESIDENT], []])
    monkeypatch.setattr(batch, 'resident_models', lambda: next(sequence))
    monkeypatch.setattr(batch.time, 'sleep', lambda seconds: None)
    assert batch.RetainedBatch(CONFIG, 1).close()['idle_after']
