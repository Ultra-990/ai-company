import json
from pathlib import Path
import shutil

from PIL import Image
import pytest

from scripts import vector_school as school
from scripts import vector_school_contract as contract
from scripts.render_school_svg import chrome_args, chrome_env, document, pdf_checks


def fixture_svg():
    # Deliberately plain parser/test fixture, not a deliverable or training answer.
    shapes = '<rect x="0" y="0" width="592" height="840" fill="#ffffff"/>' * 3
    texts = ''.join(f'<text x="30" y="{40+i*40}" font-family="Arial" font-size="20" '
                    f'font-weight="400" fill="#000000">fixture {i}</text>' for i in range(8))
    return '<svg xmlns="http://www.w3.org/2000/svg" width="592" height="840" viewBox="0 0 592 840">'+shapes+texts+'</svg>'


def layout():
    return [{'text': f'fixture {i}', 'bbox': [30, 20+i*40, 100, 24]} for i in range(8)]


def test_output_is_exact_and_wrapper_is_rejected():
    source = fixture_svg()
    assert contract.parse_response(json.dumps({'svg': source})) == source
    for raw in [json.dumps({'properties': {'svg': source}}), '```json\n'+json.dumps({'svg': source})+'\n```',
                '{"svg":"x","svg":"y"}']:
        with pytest.raises(ValueError): contract.parse_response(raw)


@pytest.mark.parametrize('addition', [
    '<script>alert(1)</script>', '<image href="file:///etc/passwd"/>',
    '<foreignObject><div>HTML</div></foreignObject>', '<use href="https://example.test/a.svg"/>',
    '<animate attributeName="x"/>', '<!--comment-->', '<g/>',
    '<rect xmlns="http://www.w3.org/1999/xhtml"/>',
])
def test_rejects_active_external_or_unsupported_elements(addition):
    with pytest.raises(ValueError): contract.validate_svg(fixture_svg().replace('</svg>', addition+'</svg>'))


@pytest.mark.parametrize('attribute', [
    'onload="alert(1)"', 'style="fill:url(https://example.test)"',
    'fill="url(file:///etc/passwd)"', 'transform="scale(1000000)"', 'href="data:text/html,x"',
])
def test_rejects_unsafe_attributes(attribute):
    source = fixture_svg().replace('<rect x="0"', '<rect '+attribute+' x="0"', 1)
    with pytest.raises(ValueError): contract.validate_svg(source)


def test_rejects_entity_expansion_invisible_and_nested_text():
    for source in ['<!DOCTYPE svg [<!ENTITY e "expand">]>'+fixture_svg(),
                   fixture_svg().replace('fill="#000000"', 'fill="none"'),
                   fixture_svg().replace('fixture 0', '<tspan>fixture 0</tspan>'),
                   fixture_svg().replace('fixture 0', 'fixture 1')]:
        with pytest.raises(ValueError): contract.validate_svg(source)


def test_text_bounds_and_overlap_have_concrete_findings():
    assert contract.layout_issues(layout()) == []
    broken = layout(); broken[0]['bbox'][0] = -10; broken[1]['bbox'][1] = 25
    issues = contract.layout_issues(broken)
    assert {x['kind'] for x in issues} == {'text_margin_or_bounds', 'text_overlap'}


def test_hidden_text_cannot_pass_from_dom_copy_alone(tmp_path):
    first, second = tmp_path/'one.png', tmp_path/'two.png'
    for path in (first, second): Image.new('RGB', (592, 840), 'white').save(path)
    hidden = layout(); hidden[0]['occluded_character_centers'] = [1, 2, 3]
    result = contract.compare(layout(), hidden, first, second)
    assert result['text_exact'] and not result['mechanical_checks_passed']
    assert result['layout_issues'][0]['kind'] == 'text_occluded'


def test_teacher_feedback_cannot_attach_to_an_unbound_attempt(tmp_path):
    with pytest.raises(ValueError, match='exact prior answer'):
        school.make_request(feedback_path=tmp_path/'feedback.json')


def test_comparison_rejects_copy_errors_large_shift_and_color_change(tmp_path):
    first, second = tmp_path/'one.png', tmp_path/'two.png'
    Image.new('RGB', (592, 840), 'white').save(first)
    Image.new('RGB', (592, 840), 'white').save(second)
    assert contract.compare(layout(), layout(), first, second)['mechanical_checks_passed']
    typo = layout(); typo[0]['text'] = 'wrong copy'
    result = contract.compare(layout(), typo, first, second)
    assert not result['mechanical_checks_passed'] and result['missing_text'] == ['fixture 0']
    moved = layout(); moved[0]['bbox'][0] += 20
    assert not contract.compare(layout(), moved, first, second)['mechanical_checks_passed']
    Image.new('RGB', (592, 840), '#ff0000').save(second)
    assert not contract.compare(layout(), layout(), first, second)['mechanical_checks_passed']


def test_chrome_keeps_sandbox_and_desktop_separate(monkeypatch):
    for key in ('DISPLAY', 'WAYLAND_DISPLAY', 'XAUTHORITY', 'DBUS_SESSION_BUS_ADDRESS'):
        monkeypatch.setenv(key, 'owner-desktop')
        assert key not in chrome_env()
    args = chrome_args('/tmp/private-profile')
    assert '--no-sandbox' not in args and '--disable-setuid-sandbox' not in args
    assert '--headless' in args and '--disable-gpu' in args and '--mute-audio' in args
    assert 'default-src \'none\'' in document(fixture_svg())


def reference(tmp_path, monkeypatch):
    monkeypatch.setattr(school, 'ROOT', tmp_path)
    folder = tmp_path/'reference'; folder.mkdir()
    source = fixture_svg()
    (folder/'artwork.svg').write_text(source)
    (folder/'response.json').write_text(json.dumps({'model': 'fixture-model', 'digest': 'd'*64, 'content': json.dumps({'svg': source})}))
    (folder/'request.json').write_text('{}')
    (folder/'render.json').write_text(json.dumps({'layout': layout()}))
    Image.new('RGB', (592, 840), 'white').save(folder/'preview.png')
    (folder/'preview.pdf').write_bytes(b'%PDF-fixture')
    report = {'schema': 'vector-school.v1', 'status': 'reference_ready', 'role': 'source',
              'data_split': 'development', 'model': 'fixture-model', 'digest': 'd'*64,
              'artifact_sha256': {p.name: school.checksum(p) for p in folder.iterdir()}}
    path = folder/'report.json'; path.write_text(json.dumps(report))
    return path


def test_recreation_sees_only_pixels_and_contract_not_source(tmp_path, monkeypatch):
    path = reference(tmp_path, monkeypatch)
    request, source = school.make_request(path)
    assert fixture_svg() not in json.dumps(request)
    assert 'fixture 0' not in request['system'] + request['user']
    assert request['image']['sha256'] == school.checksum(path.parent/'preview.png')


@pytest.mark.parametrize('name', ['artwork.svg', 'response.json', 'preview.png', 'preview.pdf', 'request.json', 'render.json'])
def test_changed_source_artifact_stops_recreation(tmp_path, monkeypatch, name):
    path = reference(tmp_path, monkeypatch)
    with (path.parent/name).open('ab') as target: target.write(b'changed')
    with pytest.raises(ValueError, match='changed'): school.make_request(path)


def test_rebound_report_during_inference_cannot_change_the_reference(tmp_path, monkeypatch):
    path = reference(tmp_path, monkeypatch)
    frozen = school.checksum(path)
    path.write_text(path.read_text() + '\n')
    with pytest.raises(ValueError, match='during the exercise'): school.require_checksum(path, frozen)


def test_even_rehashed_manual_svg_repair_is_not_model_authorship(tmp_path, monkeypatch):
    path = reference(tmp_path, monkeypatch)
    (path.parent/'artwork.svg').write_text(fixture_svg().replace('fixture 0', 'manual fix'))
    report = json.loads(path.read_text()); report['artifact_sha256']['artwork.svg'] = school.checksum(path.parent/'artwork.svg')
    path.write_text(json.dumps(report))
    with pytest.raises(ValueError, match='changed after model response'): school.load_source(path)


def test_symlink_and_other_workspace_are_rejected(tmp_path, monkeypatch):
    path = reference(tmp_path, monkeypatch)
    link = tmp_path/'link.json'; link.symlink_to(path)
    with pytest.raises(ValueError): school.checked(link)
    with pytest.raises(ValueError): school.checked(Path('/etc/passwd'))


def test_wrong_revision_source_is_rejected_before_inference(tmp_path, monkeypatch):
    path = reference(tmp_path, monkeypatch)
    previous = tmp_path/'previous.json'
    previous.write_text(json.dumps({'schema': 'vector-school.v1', 'role': 'recreation', 'status': 'needs_revision',
                                    'revision_number': 0, 'source_report': str(path), 'source_sha256': 'wrong'}))
    with pytest.raises(ValueError, match='exact reference'): school.make_request(path, previous)


def revision_fixture(tmp_path, monkeypatch, number):
    source = reference(tmp_path, monkeypatch)
    folder = tmp_path/'revision'; shutil.copytree(source.parent, folder)
    report = json.loads((folder/'report.json').read_text())
    report.update(role='recreation', status='needs_revision', revision_number=number,
                  source_report=str(source), source_sha256=school.checksum(source))
    previous = folder/'report.json'; previous.write_text(json.dumps(report))
    return source, previous


@pytest.mark.parametrize('number,mode,contains_prior', [(0, 'prior_source', True), (1, 'fresh_image_with_feedback', False)])
def test_revision_strategy_and_teacher_feedback_are_explicit(tmp_path, monkeypatch, number, mode, contains_prior):
    source, previous = revision_fixture(tmp_path, monkeypatch, number)
    feedback_path = tmp_path/'feedback.json'
    feedback_path.write_text(json.dumps({'previous_report_sha256': school.checksum(previous), 'comments': 'Specific visual observation.'}))
    request, _ = school.make_request(source, previous, feedback_path)
    assert request['revision_mode'] == mode and request['revision_number'] == number+1
    assert (fixture_svg() in request['user']) is contains_prior
    assert 'Specific visual observation.' in request['user']
    feedback_path.write_text(json.dumps({'previous_report_sha256': 'wrong', 'comments': 'Specific visual observation.'}))
    with pytest.raises(ValueError, match='exact prior answer'): school.make_request(source, previous, feedback_path)


@pytest.mark.parametrize('number', [3, -1, True])
def test_revision_limit_cannot_be_silently_extended(tmp_path, monkeypatch, number):
    source, previous = revision_fixture(tmp_path, monkeypatch, number)
    with pytest.raises(ValueError, match='three revisions'): school.make_request(source, previous)


@pytest.mark.parametrize('defect', ['missing_font', 'raster_page', 'wrong_size', 'lost_text'])
def test_pdf_requires_embedded_fonts_vector_export_a5_and_copy(monkeypatch, defect):
    outputs = {
        '/usr/bin/pdfinfo': 'Pages: 1\nPage size: 419.528 x 595.276 pts\n',
        '/usr/bin/pdftotext': 'fixture text',
        '/usr/bin/pdffonts': 'header\n-----\nAAAA+Fixture CID TrueType Identity-H yes yes yes 4 0\n',
        '/usr/bin/pdfimages': 'header\n-----\n',
    }
    monkeypatch.setattr('scripts.render_school_svg.subprocess.check_output', lambda cmd, **kwargs: outputs[cmd[0]])
    assert pdf_checks(Path('/unused.pdf'), ['fixture text'])['embedded_fonts']
    if defect == 'missing_font': outputs['/usr/bin/pdffonts'] = outputs['/usr/bin/pdffonts'].replace('yes yes yes', 'no yes yes')
    if defect == 'raster_page': outputs['/usr/bin/pdfimages'] += '1 0 image 592 840 rgb 3 8 image no 4 0 96 96\n'
    if defect == 'wrong_size': outputs['/usr/bin/pdfinfo'] = 'Pages: 1\nPage size: 612 x 792 pts\n'
    if defect == 'lost_text': outputs['/usr/bin/pdftotext'] = 'fixture'
    with pytest.raises(ValueError, match='PDF'): pdf_checks(Path('/unused.pdf'), ['fixture text'])
