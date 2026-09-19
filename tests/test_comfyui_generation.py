import pytest
import json
from pathlib import Path
from scripts.check_comfyui_generation import workflow, output_path


def test_saved_ui_workflow_matches_tested_generation_parameters():
    path = Path(__file__).resolve().parents[1] / 'config/comfyui-workflows/ai-company-z-image.json'
    ui = json.loads(path.read_text())
    subgraph = ui['definitions']['subgraphs'][0]
    nodes = {node['type']: node for node in subgraph['nodes']}
    graph = workflow()
    assert len(nodes) == 9
    assert nodes['CLIPTextEncode']['widgets_values'] == [graph['4']['inputs']['text']]
    assert nodes['EmptySD3LatentImage']['widgets_values'] == [768, 512, 1]
    assert nodes['KSampler']['widgets_values'] == [20260913, 'fixed', 8, 1, 'res_multistep', 'simple', 1]
    assert nodes['CLIPLoader']['widgets_values'] == ['qwen_3_4b.safetensors', 'lumina2', 'default']
    assert nodes['UNETLoader']['widgets_values'] == ['z_image_turbo_bf16.safetensors', 'default']
    assert nodes['VAELoader']['widgets_values'] == ['ae.safetensors']
    assert nodes['ModelSamplingAuraFlow']['widgets_values'] == [3]
    assert any(node['type'] == subgraph['id'] for node in ui['nodes'])
    assert next(node for node in ui['nodes'] if node['type'] == 'SaveImage')['widgets_values'] == ['AI-Company/Z-Image']


def test_fixed_workflow_uses_existing_models_and_bounded_native_nodes():
    graph = workflow()
    assert len(graph) == 10
    assert {node['class_type'] for node in graph.values()} == {
        'UNETLoader', 'CLIPLoader', 'VAELoader', 'CLIPTextEncode', 'ConditioningZeroOut',
        'EmptySD3LatentImage', 'ModelSamplingAuraFlow', 'KSampler', 'VAEDecode', 'SaveImage'}
    assert graph['6']['inputs'] == {'width': 768, 'height': 512, 'batch_size': 1}
    assert graph['8']['inputs']['steps'] == 8
    assert graph['8']['inputs']['cfg'] == 1.0
    assert graph['2']['inputs']['type'] == 'lumina2'
    for node in graph.values():
        for value in node['inputs'].values():
            if isinstance(value, list):
                assert value[0] in graph and value[1] == 0


@pytest.mark.parametrize('name,sub,kind', [
    ('../outside.png', '', 'output'), ('/outside.png', '', 'output'),
    ('image.png', '..', 'output'), ('image.png', '/tmp', 'output'),
    ('image.png', '', 'input'), ('image.svg', '', 'output'),
    ('image.png', '..\\else', 'output'),
])
def test_output_rejects_unsafe_locations(tmp_path, name, sub, kind):
    with pytest.raises(ValueError):
        output_path(tmp_path / 'output', {'filename': name, 'subfolder': sub, 'type': kind})


def test_output_requires_real_bounded_file(tmp_path):
    entry = {'filename': 'image.png', 'subfolder': '', 'type': 'output'}
    with pytest.raises(ValueError):
        output_path(tmp_path, entry)
    p = tmp_path / 'image.png'
    p.write_bytes(b'bytes checked later by Pillow')
    assert output_path(tmp_path, entry) == p
