from copy import deepcopy
import json
import pytest

from scripts import brand_plan_review as plan


def review(flagged=(4,)):
    return {'reviews': [{'index': i, 'verdict': 'unsupported' if i in flagged else 'supported',
        'reason': 'The actual SVG establishes this finding.'} for i in range(6)]}


def test_svg_facts_distinguish_text_only_and_full_logo_without_inventing_visual_proof():
    full = plan.structure('<svg xmlns="http://www.w3.org/2000/svg"><circle r="20"/><text x="40" y="50">Name</text></svg>')
    text = plan.structure('<svg xmlns="http://www.w3.org/2000/svg"><text>Name</text></svg>')
    assert full['shape_nodes'] == full['text_nodes'] == 1
    assert text['shape_nodes'] == 0 and text['text_nodes'] == 1
    assert full['text_path_nodes'] == 0 and full['texts'][0]['attributes']['y'] == '50'


@pytest.mark.parametrize('reason', ['An incomplete explanation with', 'x'*181+'.', 'Missing evidence...', ' A complete sentence.'])
def test_truncated_or_oversized_reason_is_refused(reason):
    value = review(); value['reviews'][0]['reason'] = reason
    with pytest.raises(ValueError): plan.review_value(json.dumps(value))


def test_six_reviews_and_concept_only_patch_preserve_graphic_settings():
    original = {'guidelines': ['Existing rule.']*4, 'concept_a': 'A wrong curved wordmark description.',
                'concept_b': 'Another untouched concept description.', 'ink': '#112233', 'tagline': 'Unchanged tagline'}
    saved = deepcopy(original)
    critique = plan.review_value(json.dumps(review()))
    schema = plan.patch_schema(critique)['properties']['replacements']
    assert schema['minItems'] == schema['maxItems'] == 1
    assert schema['items']['properties']['index']['enum'] == [4]
    changed = plan.apply(original, json.dumps({'replacements': [{'index': 4,
        'text': 'A circular symbol sits above the straight wordmark.'}]}), critique)
    assert changed['concept_a'] != original['concept_a'] and original == saved
    changed['concept_a'] = original['concept_a']
    assert changed == original
    with pytest.raises(ValueError):
        plan.apply(original, json.dumps({'replacements': [{'index': 5,
            'text': 'A change to the unflagged concept description.'}]}), critique)
