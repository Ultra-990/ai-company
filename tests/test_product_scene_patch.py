from copy import deepcopy
import json

import pytest

from scripts import product_scene_patch as patch


def scene():
    return {'shapes': [{'tag': 'rect', 'attributes': {'x': '10', 'y': '20', 'width': '100', 'height': '100', 'fill': '#112233'}}],
            'texts': [{'text': 'Exact fact', 'attributes': {'x': '30', 'y': '40', 'font-family': 'Arial', 'font-size': '48', 'fill': '#112233'}}],
            'product_placement': {'x': '100', 'y': '200', 'scale': '1'}}


def edit(**changes):
    return {'target': 'texts', 'index': 0, 'attribute': 'y', 'value': '80'} | changes


def test_model_edit_preserves_original_scene_and_all_unnamed_fields():
    original = scene(); snapshot = deepcopy(original)
    result = patch.apply(original, json.dumps({'edits': [edit()]}))
    expected = deepcopy(original); expected['texts'][0]['attributes']['y'] = '80'
    assert result == expected and original == snapshot


@pytest.mark.parametrize('operation', [edit(attribute='text', value='Different fact'),
    edit(attribute='fill', value='#445566'), edit(attribute='font-family', value='Georgia'),
    edit(index=True), edit(index=-1), edit(index=8), edit(value=80), edit(value='40'),
    edit(target='shapes', attribute='d', value='M0 0'), edit(target='placement', index=1)])
def test_rejects_content_paint_font_and_target_changes(operation):
    with pytest.raises(ValueError): patch.apply(scene(), json.dumps({'edits': [operation]}))


def test_geometry_can_be_added_and_product_moved_but_duplicate_targets_are_rejected():
    operations = [edit(target='shapes', attribute='rx', value='8'), edit(target='placement', attribute='x', value='-50')]
    result = patch.apply(scene(), json.dumps({'edits': operations}))
    assert result['shapes'][0]['attributes']['rx'] == '8' and result['product_placement']['x'] == '-50'
    with pytest.raises(ValueError, match='Duplicate'): patch.apply(scene(), json.dumps({'edits': [edit(), edit(value='90')]}))
    with pytest.raises(ValueError): patch.apply(scene(), json.dumps({'edits': []}))
