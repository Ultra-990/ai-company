import pytest
from scripts.compare_local_models import model_config, MODELS
from app.services.local_ollama import generation_options


@pytest.mark.parametrize('model', MODELS)
def test_local_model_config_is_pinned_and_bounded(model):
    config = model_config(model, {'models':[{'name':model,'digest':'a'*64}]})
    assert config['digest'] == 'a'*64 and config['num_ctx'] == 8192
    assert config['timeout_seconds'] == 120 and config['num_predict'] == 1200
    options = generation_options(config)
    assert options['temperature'] == (1.0 if model.startswith('gemma') else .2)


def test_cloud_and_unpinned_models_rejected():
    with pytest.raises(ValueError): model_config('gemma4:31b-cloud', {})
    with pytest.raises(ValueError): model_config('gemma4:31b', {'models':[{'name':'gemma4:31b','digest':'bad'}]})
