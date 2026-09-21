import json
from hashlib import sha256
from pathlib import Path
import shutil

from PIL import Image
import pytest

from scripts import vector_school as school
from scripts import vector_school_contract as contract
from scripts.render_school_svg import chrome_args, chrome_env, document, pdf_checks
from scripts.vector_patch_school import apply_edits, catalogue, prepare
from scripts import vector_patch_school as patches
from scripts.vector_curriculum import CURRICULA, LEGACY, metadata, require_learning


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


def test_nearly_invisible_text_cannot_pass_from_geometry_alone():
    invisible = layout(); invisible[0]['low_contrast_character_centers'] = [0, 1, 2]
    assert contract.layout_issues(invisible)[0]['kind'] == 'text_near_background_color'


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
    (folder/'request.json').write_text(json.dumps({'system': contract.RULES, 'user': contract.SOURCE_BRIEF, 'image': None}))
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


def edit(element=3, attribute='font-size', before='20', after='22'):
    return {'element': element, 'attribute': attribute, 'before': before, 'after': after}


def test_model_patch_changes_only_named_value_and_preserves_all_other_bytes():
    source = fixture_svg().replace('font-size="20"', "font-size = '20'", 1)
    output, edits = apply_edits(source, json.dumps({'edits': [edit()]}), {3})
    assert output == source.replace("font-size = '20'", "font-size = '22'", 1)
    assert edits == [edit()]
    assert catalogue(output)[3]['attributes']['font-size'] == '22'


def test_multiple_model_edits_use_original_indices_not_shifted_string_offsets():
    source = fixture_svg()
    patches = [edit(after='24'), edit(element=4, attribute='x', before='30', after='130')]
    output, _ = apply_edits(source, json.dumps({'edits': patches}), {3, 4})
    entries = catalogue(output)
    assert entries[3]['attributes']['font-size'] == '24'
    assert entries[4]['attributes']['x'] == '130'
    assert entries[5:] == catalogue(source)[5:]


@pytest.mark.parametrize('bad', [edit(element=4), edit(element=True), edit(before='19'),
    edit(after='20'), edit(after='100000'), edit(after='22" onload="x'), edit(after='&quot;'),
    edit(attribute='onclick', before='', after='x'), edit(attribute='letter-spacing', before='', after='2')])
def test_invalid_stale_unsafe_and_protected_edits_fail_without_repair(bad):
    with pytest.raises(ValueError): apply_edits(fixture_svg(), json.dumps({'edits': [bad]}), {3})


def test_duplicate_patch_operations_and_schema_wrappers_are_rejected():
    for data in [{'edits': [edit(), edit(after='24')]}, {'properties': {'edits': [edit()]}}, {'edits': []}]:
        with pytest.raises(ValueError): apply_edits(fixture_svg(), json.dumps(data), {3})


def test_patch_targets_come_from_verified_measurements_and_keep_reference_svg_private(tmp_path, monkeypatch):
    source, previous = revision_fixture(tmp_path, monkeypatch, 2)
    rendering = json.loads((previous.parent/'render.json').read_text())
    rendering['layout'][0]['bbox'][2] = 140
    for item in rendering['layout']: item['occluded_character_centers'] = []
    (previous.parent/'render.json').write_text(json.dumps(rendering))
    report = json.loads(previous.read_text())
    report['artifact_sha256']['render.json'] = school.checksum(previous.parent/'render.json')
    previous.write_text(json.dumps(report))
    request, prior_svg, prior_render, expected, targets = prepare(previous)
    assert [item['element'] for item in targets] == [3]
    assert targets[0]['reference_bbox'][2] == 100 and targets[0]['current_bbox'][2] == 140
    assert '<svg' not in request['system'] + request['user']
    assert request['image']['sha256'] == school.checksum(source.parent/'preview.png')
    named, _, _, _, errors = prepare(previous, 'named-deltas-v1')
    assert named['diagnostic_profile'] == 'named-deltas-v1'
    assert errors[0]['dimensions_failing_tolerance'] == ['width']
    assert errors[0]['current_minus_reference']['width'] == 40


def verified_patch_fixture(tmp_path, monkeypatch):
    monkeypatch.setattr(school, 'ROOT', tmp_path)
    previous, source_report = tmp_path/'prior.json', tmp_path/'source.json'
    previous.write_text('{}'); source_report.write_text('{}')
    image = tmp_path/'reference.png'; Image.new('RGB', (592, 840), 'white').save(image)
    request = {'system': 'fixture instruction', 'user': 'fixture diagnosis',
               'image': {'path': str(image), 'sha256': school.checksum(image)}}
    prior = layout(); prior[0]['bbox'][2] = 140
    target = [{'element': 3, 'text': 'fixture 0'}]
    monkeypatch.setattr(patches, 'prepare', lambda path: (request, fixture_svg(), {'layout': prior}, {'layout': layout()}, target))
    monkeypatch.setattr('scripts.render_school_svg.pdf_checks', lambda *args: {'fixture': True})
    folder = tmp_path/'patch'; folder.mkdir()
    raw = json.dumps({'edits': [edit()]})
    output, edits = apply_edits(fixture_svg(), raw, [3])
    (folder/'artwork.svg').write_text(output)
    (folder/'request.json').write_text(json.dumps(request))
    (folder/'response.json').write_text(json.dumps({'model': 'fixture', 'digest': 'd'*64, 'content': raw}))
    (folder/'render.json').write_text(json.dumps({'layout': layout()}))
    shutil.copyfile(image, folder/'preview.png'); (folder/'preview.pdf').write_bytes(b'%PDF-fixture')
    report = {'schema': 'vector-attribute-lesson.v1', 'data_split': 'development', 'status': 'pending_independent_review',
              'thresholds': contract.THRESHOLDS, 'model': 'fixture', 'digest': 'd'*64, 'config': {},
              'previous_report': str(previous), 'previous_sha256': school.checksum(previous),
              'source_report': str(source_report), 'source_sha256': school.checksum(source_report),
              'editable_elements': [3], 'edits': edits, 'raw_response_sha256': sha256(raw.encode()).hexdigest(),
              'protected_text_geometry_unchanged': True,
              'comparison': contract.compare(layout(), layout(), image, folder/'preview.png'),
              'artifact_sha256': {p.name: school.checksum(p) for p in folder.iterdir()}}
    path = folder/'report.json'; path.write_text(json.dumps(report))
    return path


def candidate_fixture(tmp_path, monkeypatch, split='train'):
    monkeypatch.setattr('scripts.check_vision_training_inputs.BUNDLE_ROOTS', (tmp_path,))
    from scripts.vector_curriculum import metadata
    path = verified_patch_fixture(tmp_path, monkeypatch)
    report = json.loads(path.read_text())
    if split == 'train':
        curriculum = metadata({'curriculum': 'restaurant-tasting-train-v1'})
        previous = Path(report['previous_report'])
        previous.write_text(json.dumps(curriculum))
        report.update(curriculum, previous_sha256=school.checksum(previous))
        path.write_text(json.dumps(report))
    judgment = {'schema': 'vector-attribute-review.v1', 'report_sha256': school.checksum(path),
                'reviewer': 'assistant_direct_visual_review', 'decision': 'approved_development_attribute_repair',
                'notes': 'Fixture independent review; limited tool operation only.',
                'visual_checks': {'text_readable': True, 'target_geometry_improved': True,
                                  'no_new_visual_defects': True, 'limited_scope_acknowledged': True}}
    target = tmp_path/'review.json'; target.write_text(json.dumps(judgment))
    archived = path.parent/'experience.json'
    archived.write_text(json.dumps(patches.experience(path, target)))
    return path, target, archived


def test_vector_candidates_preserve_actual_model_response_and_reference_pixels(tmp_path, monkeypatch):
    from scripts import vector_learning_records as records
    from scripts.check_vision_training_inputs import verify_bundle, feature
    path, _, archived = candidate_fixture(tmp_path, monkeypatch)
    out = records.export([archived])
    rows = verify_bundle(out)
    assert len(rows) == 1 and rows[0]['family'] == 'restaurant-tasting-001'
    assert rows[0]['messages'][-1]['content'] == json.loads((path.parent/'response.json').read_text())['content']
    assert (out/rows[0]['images'][0]['file']).read_bytes() == (tmp_path/'reference.png').read_bytes()
    assert feature(rows[0], out)['images'][0].size == (592, 840)
    manifest = json.loads((out/'manifest.json').read_text())
    assert manifest['training_started'] is False and manifest['ready_for_trainer'] is False


def test_development_experience_cannot_enter_vector_training_candidates(tmp_path, monkeypatch):
    from scripts import vector_learning_records as records
    _, _, archived = candidate_fixture(tmp_path, monkeypatch, split='development')
    with pytest.raises(ValueError, match='predeclared train'): records.export([archived])


@pytest.mark.parametrize('change', ['archived_answer', 'review', 'copied_image', 'record_answer', 'collector', 'duplicate'])
def test_candidate_audit_rejects_changes_even_with_rehashed_manifest(tmp_path, monkeypatch, change):
    from scripts import vector_learning_records as records
    from scripts.check_vision_training_inputs import verify_bundle
    _, review, archived = candidate_fixture(tmp_path, monkeypatch)
    if change == 'archived_answer':
        data = json.loads(archived.read_text()); data['messages'][-1]['content'] = 'teacher replacement'
        archived.write_text(json.dumps(data))
        with pytest.raises(ValueError, match='Archived'): records.export([archived])
        return
    if change == 'duplicate':
        with pytest.raises(ValueError, match='Duplicate'): records.export([archived, archived])
        return
    out = records.export([archived]); manifest = json.loads((out/'manifest.json').read_text())
    row = json.loads((out/'records.jsonl').read_text())
    if change == 'review':
        data = json.loads(review.read_text()); data['visual_checks']['text_readable'] = False
        review.write_text(json.dumps(data))
    elif change == 'copied_image':
        (out/row['images'][0]['file']).write_bytes(b'changed image')
    elif change == 'record_answer':
        row['messages'][-1]['content'] = 'teacher replacement'
        payload = json.dumps(row)+'\n'; (out/'records.jsonl').write_text(payload)
        manifest['records_sha256'] = sha256(payload.encode()).hexdigest()
    elif change == 'collector': manifest['collector'] = 'unknown'
    (out/'manifest.json').write_text(json.dumps(manifest))
    with pytest.raises(ValueError): verify_bundle(out)


@pytest.mark.parametrize('kind', ['manual_svg', 'changed_input', 'reported_edit'])
def test_rehashed_changes_cannot_replace_the_models_actual_patch(tmp_path, monkeypatch, kind):
    path = verified_patch_fixture(tmp_path, monkeypatch)
    assert patches.verify(path)['verified']
    report = json.loads(path.read_text())
    if kind == 'manual_svg':
        item = path.parent/'artwork.svg'; item.write_text(item.read_text().replace('font-size="22"', 'font-size="24"'))
        report['artifact_sha256'][item.name] = school.checksum(item)
    elif kind == 'changed_input':
        item = path.parent/'request.json'; request = json.loads(item.read_text()); request['user'] = 'different'
        item.write_text(json.dumps(request)); report['artifact_sha256'][item.name] = school.checksum(item)
    else: report['edits'][0]['after'] = '24'
    path.write_text(json.dumps(report))
    with pytest.raises(ValueError): patches.verify(path)


@pytest.mark.parametrize('decision,check', [('model_self_approval', True), ('approved_development_attribute_repair', False),
                                         ('approved_development_attribute_repair', 1)])
def test_experience_needs_an_explicit_independent_review(tmp_path, monkeypatch, decision, check):
    path = verified_patch_fixture(tmp_path, monkeypatch)
    judgment = {'schema': 'vector-attribute-review.v1', 'report_sha256': school.checksum(path),
                'reviewer': 'assistant_direct_visual_review', 'decision': 'approved_development_attribute_repair',
                'notes': 'Fixture review of a limited edit lesson.',
                'visual_checks': {'text_readable': True, 'target_geometry_improved': True,
                                  'no_new_visual_defects': True, 'limited_scope_acknowledged': True}}
    target = tmp_path/'review.json'; target.write_text(json.dumps(judgment))
    record = patches.experience(path, target)
    assert record['split'] == 'development' and not record['training_exported']
    assert record['messages'][2]['content'] == json.loads((path.parent/'response.json').read_text())['content']
    judgment['decision'] = decision; judgment['visual_checks']['text_readable'] = check
    target.write_text(json.dumps(judgment))
    with pytest.raises(ValueError, match='teacher review'): patches.experience(path, target)


def test_new_families_are_disjoint_and_hash_bound_before_generation():
    assert len({value['family'] for value in CURRICULA.values()}) == len(CURRICULA)
    assert {value['data_split'] for value in CURRICULA.values()} == {'development', 'train', 'validation', 'test'}
    for name in CURRICULA:
        frozen = metadata({'curriculum': name})
        assert metadata({'schema': 'vector-school.v1', **frozen}) == frozen
        if name != LEGACY:
            with pytest.raises(ValueError, match='Incomplete'): metadata({'schema': 'vector-school.v1', 'curriculum': name})
            with pytest.raises(ValueError): metadata({**frozen, 'curriculum_sha256': 'changed'})


@pytest.mark.parametrize('name', ['science-evening-validation-v1', 'travel-club-test-v1'])
def test_reserved_families_cannot_be_relabelled_for_learning(name):
    frozen = metadata({'curriculum': name})
    with pytest.raises(ValueError, match='Reserved'): require_learning(frozen)
    with pytest.raises(ValueError, match='changed'): require_learning({**frozen, 'data_split': 'train'})


def reserved_reference(tmp_path, monkeypatch):
    path = reference(tmp_path, monkeypatch)
    report = json.loads(path.read_text())
    name = 'travel-club-test-v1'; report.update(metadata({'curriculum': name}))
    request = {'system': contract.RULES, 'user': CURRICULA[name]['brief'], 'image': None}
    (path.parent/'request.json').write_text(json.dumps(request))
    report['artifact_sha256']['request.json'] = school.checksum(path.parent/'request.json')
    path.write_text(json.dumps(report))
    return path, report


def test_reserved_reference_is_blocked_before_reconstruction(tmp_path, monkeypatch):
    path, _ = reserved_reference(tmp_path, monkeypatch)
    with pytest.raises(ValueError, match='Reserved'): school.make_request(path)


def test_stripping_holdout_metadata_still_fails_its_original_brief_binding(tmp_path, monkeypatch):
    path, report = reserved_reference(tmp_path, monkeypatch)
    for key in ('curriculum', 'curriculum_sha256', 'family'): report.pop(key)
    report['data_split'] = 'development'; path.write_text(json.dumps(report))
    with pytest.raises(ValueError, match='frozen curriculum'): school.load_source(path)


def source_feedback_fixture(path):
    return {'schema': 'vector-source-feedback.v1', 'source_report': str(path), 'source_sha256': school.checksum(path),
            'request_sha256': school.checksum(path.parent/'request.json'), 'response_sha256': school.checksum(path.parent/'response.json'),
            'comments': 'Correct the observed source defect yourself.'}


def test_source_repair_preserves_family_and_binds_even_failed_raw_reply(tmp_path, monkeypatch):
    path = reference(tmp_path, monkeypatch)
    report = json.loads(path.read_text()); report['status'] = 'failed'; path.write_text(json.dumps(report))
    feedback = source_feedback_fixture(path)
    request = school.source_request(LEGACY, feedback)
    assert 'Correct the observed source defect' in request['user']
    assert request['source_feedback'] == feedback
    assert request['user'].startswith(contract.SOURCE_BRIEF)
    with pytest.raises(ValueError, match='original family'): school.source_request('garden-workshop-train-v1', feedback)
    (path.parent/'response.json').write_text('{}')
    with pytest.raises(ValueError, match='changed'): school.source_request(LEGACY, feedback)


def test_source_feedback_cannot_forge_a_recursive_predecessor(tmp_path, monkeypatch):
    path = reference(tmp_path, monkeypatch)
    feedback = source_feedback_fixture(path)
    request = school.source_request(LEGACY, feedback)
    (path.parent/'request.json').write_text(json.dumps(request))
    feedback = source_feedback_fixture(path)
    with pytest.raises(ValueError): school.source_request(LEGACY, feedback)


def test_source_revision_chain_stops_at_three(tmp_path, monkeypatch):
    path = reference(tmp_path, monkeypatch)
    for number in range(3):
        request = school.source_request(LEGACY, source_feedback_fixture(path))
        folder = tmp_path/('source-revision-'+str(number)); shutil.copytree(path.parent, folder)
        report = json.loads((folder/'report.json').read_text())
        (folder/'request.json').write_text(json.dumps(request))
        report['artifact_sha256']['request.json'] = school.checksum(folder/'request.json')
        path = folder/'report.json'; path.write_text(json.dumps(report))
    with pytest.raises(ValueError, match='three bound'): school.source_request(LEGACY, source_feedback_fixture(path))


def test_training_reference_needs_bound_positive_visual_review(tmp_path, monkeypatch):
    path = reference(tmp_path, monkeypatch)
    report = json.loads(path.read_text()); name = 'garden-workshop-train-v1'
    report.update(metadata({'curriculum': name}))
    (path.parent/'request.json').write_text(json.dumps(school.source_request(name)))
    report['artifact_sha256']['request.json'] = school.checksum(path.parent/'request.json')
    path.write_text(json.dumps(report))
    with pytest.raises(ValueError): school.make_request(path)
    review = {'schema': 'vector-reference-review.v1', 'source_sha256': school.checksum(path),
              'reviewer': 'assistant_direct_visual_review', 'decision': 'rejected_reference', 'notes': 'Fixture defect.'}
    (path.parent/'reference-review.json').write_text(json.dumps(review))
    with pytest.raises(ValueError, match='positive reference'): school.make_request(path)
    review['decision'] = 'usable_synthetic_training_reference'
    (path.parent/'reference-review.json').write_text(json.dumps(review))
    assert school.make_request(path)[1]['data_split'] == 'train'
    review['source_sha256'] = 'changed'; (path.parent/'reference-review.json').write_text(json.dumps(review))
    with pytest.raises(ValueError, match='positive reference'): school.make_request(path)
