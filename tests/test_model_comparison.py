import pytest
from scripts.compare_local_models import model_config, MODELS
from app.services.local_ollama import generation_options


@pytest.mark.parametrize('model', MODELS)
def test_local_model_config_is_pinned_and_bounded(model):
    config = model_config(model, {'models':[{'name':model,'digest':'a'*64}]})
    assert config['digest'] == 'a'*64 and config['num_ctx'] == 8192
    assert config['timeout_seconds'] == 120 and config['num_predict'] == 2400
    assert config['think'] == ('low' if model == 'gpt-oss:20b' else False)
    options = generation_options(config)
    assert options['temperature'] == (1.0 if model.startswith('gemma') else .2)


def test_cloud_and_unpinned_models_rejected():
    with pytest.raises(ValueError): model_config('gemma4:31b-cloud', {})
    with pytest.raises(ValueError): model_config('gemma4:31b', {'models':[{'name':'gemma4:31b','digest':'bad'}]})
    with pytest.raises(ValueError, match='not installed'): model_config('gemma4:31b', {'models':[]})


@pytest.mark.parametrize('error', [PermissionError, TimeoutError, ValueError])
def test_unknown_comfy_state_blocks_comparison(monkeypatch, error):
    from scripts import compare_local_models as module
    monkeypatch.setattr(module, 'ensure_idle', lambda: None)
    def fail(*args): raise error('unknown')
    monkeypatch.setattr(module, 'local_json', fail)
    with pytest.raises(error): module.check_idle()


def test_stopped_comfy_is_allowed_but_active_containers_are_not(monkeypatch):
    from scripts import compare_local_models as module
    monkeypatch.setattr(module, 'ensure_idle', lambda: None)
    def absent(*args): raise ConnectionRefusedError('not listening')
    monkeypatch.setattr(module, 'local_json', absent)
    monkeypatch.setattr(module.subprocess, 'check_output', lambda args, **kw: '' if args[0]=='docker' else '30000\n')
    assert module.check_idle()['comfyui'] == 'not_listening'
    monkeypatch.setattr(module.subprocess, 'check_output', lambda *a, **kw: 'foreign-container\n')
    with pytest.raises(ValueError, match='active_containers'): module.check_idle()


def test_ollama_busy_diagnostic_is_safe_and_does_not_launch_work(monkeypatch):
    from scripts import compare_local_models as module
    def busy(): raise ValueError('private external detail')
    monkeypatch.setattr(module, 'ensure_idle', busy)
    with pytest.raises(module.PreflightFailure) as error:
        module.check_idle()
    assert error.value.code == 'ollama_not_confirmed_idle'
    assert 'private' not in str(error.value)


@pytest.mark.parametrize('queue', [None, [], {}, {'queue_running':['job'], 'queue_pending':[]}])
def test_invalid_or_busy_comfy_reply_blocks_work(monkeypatch, queue):
    from scripts import compare_local_models as module
    monkeypatch.setattr(module, 'ensure_idle', lambda: None)
    monkeypatch.setattr(module, 'local_json', lambda *a: queue)
    with pytest.raises(module.PreflightFailure, match='comfyui_busy_or_unknown'):
        module.check_idle()


@pytest.mark.parametrize('memory', ['24000\n', '30000\n30000\n'])
def test_insufficient_or_ambiguous_gpu_memory_blocks_work(monkeypatch, memory):
    from scripts import compare_local_models as module
    monkeypatch.setattr(module, 'ensure_idle', lambda: None)
    monkeypatch.setattr(module, 'local_json', lambda *a: {'queue_running':[], 'queue_pending':[]})
    monkeypatch.setattr(module.subprocess, 'check_output', lambda args, **kw: '' if args[0]=='docker' else memory)
    with pytest.raises(module.PreflightFailure, match='gpu_memory_unavailable'):
        module.check_idle()
