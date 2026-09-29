import pytest

from scripts import product_paint_separation as paint


@pytest.mark.parametrize('box,color,expected', [
    ([160, 360, 480, 880], '#4A6B8A', True),
    ([160, 360, 480, 880], '#223344', True),
    ([160, 360, 480, 880], '#FFFFFF', False),
    ([0, 0, 55, 1500], '#4A6B8A', False),
    ([300, 500, 200, 3], '#223344', False),
    ([295, 495, 10, 10], '#4A6B8A', False),
    ([600, 500, 100, 100], '#4A6B8A', False),
    ([300, 500, 50, 50], 'none', False),
])
def test_product_paint_cannot_merge_with_large_decoration_but_annotations_and_clear_bands_remain_allowed(box, color, expected):
    svg = '<svg xmlns="http://www.w3.org/2000/svg"><rect fill="'+color+'"/><g/><text>Fixture</text></svg>'
    measured = {'group_layout': [{'bbox': [300, 300, 300, 900]}],
                'shape_layout': [{'tag': 'rect', 'bbox': box}, {'tag': 'rect', 'bbox': [300, 300, 300, 900]}]}
    findings = paint.issues(svg, measured, {'body_color': '#4A6B8A', 'cap_color': '#223344'})
    assert bool(findings) is expected
    if expected:
        assert findings[0]['shape_index'] == 0
        assert findings[0]['kind'] == 'decoration_merges_with_product'


def test_missing_or_misaligned_measurements_do_not_silently_accept():
    svg = '<svg xmlns="http://www.w3.org/2000/svg"><ellipse fill="#4A6B8A"/><g/></svg>'
    style = {'body_color': '#4A6B8A', 'cap_color': '#223344'}
    assert paint.issues(svg, {}, style)[0]['kind'] == 'missing_product_paint_reference'
    measured = {'group_layout': [{'bbox': [300, 300, 300, 900]}], 'shape_layout': []}
    assert paint.issues(svg, measured, style)[0]['kind'] == 'missing_decoration_paint_measurements'
    measured['shape_layout'] = [{'tag': 'rect', 'bbox': [100, 100, 500, 900]}]
    with pytest.raises(ValueError, match='does not match'): paint.issues(svg, measured, style)
