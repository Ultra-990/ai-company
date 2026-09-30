from copy import deepcopy
import json
from PIL import Image
import pytest
from scripts import brand_guide_revision as guide
from scripts.brand_spatial_review import geometry


@pytest.fixture
def proof(tmp_path, monkeypatch):
    b = guide.brand; monkeypatch.setattr(b, 'ROOT', tmp_path)
    out, source, folder = (tmp_path/n for n in ('revision', 'source', 'proof'))
    out.mkdir(); (source/'delivery').mkdir(parents=True); folder.mkdir()
    b.school.save(out/'report.json', {'fixture': 'immutable report'})
    raw = {'layout': [{'bbox': [100, 250, 300, 60]}], 'shape_layout': [{'bbox': [200, 50, 100, 80]}]}
    measurements = {key: geometry(raw) for key in ('a', 'b')}
    for key in ('a','b'):
        (folder/key).mkdir()
        for p in (folder/key/'artwork.svg', source/'delivery'/('logo-'+key+'.svg')): p.write_text('<svg xmlns="http://www.w3.org/2000/svg"/>')
        for p in (folder/key/'preview.png', source/'delivery'/('logo-'+key+'.png')): Image.new('RGB', (600,360), 'white').save(p)
        b.school.save(folder/key/'render.json', raw)
    b.school.save(folder/'measurements.json', measurements)
    prior = {'report_sha256': b.school.checksum(out/'report.json'), 'independent_spatial_render': {'directory': str(folder), 'measurements_sha256': b.school.checksum(folder/'measurements.json')}}
    b.school.save(out/'verification.json', prior)
    return out, source, folder, {'spatial_measurements': measurements}


def test_cached_render_rechecks_original_svg_pixels_and_measured_geometry(proof):
    out, source, folder, data = proof
    assert guide.recorded_render(out, source, data)['directory'] == str(folder)
    extended = deepcopy(data)
    for v in extended['spatial_measurements'].values(): v['necessary_conditions']['inside'] = False
    assert guide.recorded_render(out, source, extended)['directory'] == str(folder)


@pytest.mark.parametrize('fault', ['report', 'svg', 'pixels', 'measurements', 'renderer', 'source_geometry'])
def test_old_render_cannot_be_reused_after_its_bound_evidence_changes(proof, fault):
    out, source, folder, data = proof
    if fault == 'report': (out/'report.json').write_text('{}')
    elif fault == 'svg': (folder/'a/artwork.svg').write_text('<svg/>')
    elif fault == 'pixels': Image.new('RGB', (600,360), 'black').save(folder/'a/preview.png')
    elif fault == 'measurements': (folder/'measurements.json').write_text('{}')
    elif fault == 'renderer': (folder/'a/render.json').write_text(json.dumps({'layout': [{'bbox':[0,0,1,1]}], 'shape_layout':[{'bbox':[0,0,1,1]}]}))
    else: data['spatial_measurements']['a']['wordmark_bounds'][0] += 1
    with pytest.raises(ValueError): guide.recorded_render(out, source, data)
