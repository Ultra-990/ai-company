"""Replay the whole delivery pipeline with synthetic transport/render fixtures.

These tests exercise provenance and orchestration, not image quality or the
local reviewer's factual accuracy. No browser, network, GPU or model is used.
"""
from copy import deepcopy
import json
from pathlib import Path
import zipfile

from PIL import Image
import pytest

from scripts import product_delivery_workflow as flow
from scripts import product_delivery_correction as correction
from tests.test_product_infographic_school import style, source_scene, panel_scene

p = flow.product


@pytest.fixture
def pipeline(tmp_path, monkeypatch):
    monkeypatch.setattr(p, 'ROOT', tmp_path)
    monkeypatch.setattr(flow.probe.revision, 'ROOT', tmp_path)
    monkeypatch.setattr(p.school, 'check_idle', lambda: {'test_fixture': True})
    config = {'model': 'fixture-model', 'digest': 'a'*64}
    monkeypatch.setattr(p, 'configuration', lambda: deepcopy(config))
    # Existing geometry and browser checks have their own tests. Here the
    # actual compiler, requests, correction replay, literal selection and ZIP
    # verification run; only rendering/measurement and initial package gate
    # are fixtures, so this cannot be interpreted as an artwork acceptance.
    monkeypatch.setattr(p, 'verify', lambda folder: {'verified': True, 'fixture': True})
    for name in ('quality_issues', 'source_fidelity_issues'):
        monkeypatch.setattr(p, name, lambda *a, **k: [])
    monkeypatch.setattr(p.callouts, 'issues', lambda *a, **k: [])
    monkeypatch.setattr(p.paint, 'issues', lambda *a, **k: [])
    monkeypatch.setattr(p, 'pdf_checks', lambda *a, **k: None)
    async def render(svg, folder, *, profile, png_scale=1):
        size = (600, 800) if profile == 'product_source' else (1500, 1500)
        Image.new('RGB', tuple(int(n*png_scale) for n in size), 'white').save(folder/'preview.png')
        (folder/'preview.pdf').write_bytes(b'Synthetic PDF fixture, not a product')
        return {'layout': [], 'shape_layout': [], 'group_layout': []}
    monkeypatch.setattr(p, 'render', render)
    package = tmp_path/'original'; package.mkdir()
    report = config | {'schema': 'product-infographic-school.v1', 'status': 'pending_independent_review',
        'brief': p.DEFAULT_BRIEF, 'supplier_copy': p.DEFAULT_PANELS,
        'placement_contract': p.LEGACY_PLACEMENT, 'supplier_copy_contract': p.LEGACY_COPY,
        'annotation_contract': p.callouts.CONTRACT}
    p.school.save(package/'report.json', report)
    values = {'style': style(), 'source': source_scene()} | {part: panel_scene(part) for part in p.PANELS}
    source = p.compile_scene(json.dumps(values['source']), values['style'])
    for stage, value in values.items():
        p.school.save(package/(stage+'-response.json'), config | {'content': json.dumps(value)})
        if stage == 'style': continue
        folder = package/stage; folder.mkdir()
        svg = source if stage == 'source' else p.compile_scene(json.dumps(value), values['style'], panel=stage, product=source)
        (folder/'artwork.svg').write_text(svg)
    delivery = package/'delivery'; delivery.mkdir()
    p.school.save(delivery/'style.json', values['style'])
    p.school.save(delivery/'supplier-brief.json', {'brief': p.BRIEF, 'supplier_copy': p.PANELS})
    state = {'flagged': ['capacity', 'care'], 'final_flag': None, 'calls': [], 'reject_writes': False}
    class Provider:
        def __init__(self, conf): self.conf = conf
        def complete(self, messages):
            system, user = (m['content'] for m in messages)
            state['calls'].append((system, user, self.conf))
            if system == flow.repair.SYSTEM:
                # Correction prompt includes the first JSON followed by its
                # preserved response/feedback. Parse only the initial object.
                data, _ = json.JSONDecoder().raw_decode(user)
                value = {'headline': 'Fixture revised '+data['panel']['panel']}
                if state['reject_writes']: value['headline'] = data['panel']['headline']
            else:
                data = json.loads(user)
                final = all(row['headline'].startswith('Fixture revised') for row in data['panels'] if row['panel'] in state['flagged'])
                value = {'reviews': [{'panel': row['panel'],
                    'verdict': 'unsupported' if (row['panel'] in state['flagged'] and row['headline'] == 'Fixture headline')
                        or (final and row['panel'] == state['final_flag']) else 'supported',
                    'reason': 'Synthetic fixture judgment for pipeline replay.', 'evidence': []} for row in data['panels']]}
            return config | {'content': json.dumps(value)}
    monkeypatch.setattr(p.brand, 'OllamaProvider', Provider)
    return package, state


def test_full_pipeline_combines_literal_repairs_and_preserves_original_and_delivery(pipeline):
    package, state = pipeline
    before = {str(f.relative_to(package)): f.read_bytes() for f in package.rglob('*') if f.is_file()}
    out, report = flow.run(package)
    assert report['status'] == 'pending_independent_review', report
    proof = flow.verify(out)
    assert proof['literal_authorship_verified'] and not proof['whole_package_accepted']
    assert report['model_calls'] == {'generation': 0, 'initial_review': 1, 'repair': 4, 'final_review': 1, 'headlines': 6}
    candidate = Path(report['candidate']['directory']); repaired = Path(report['repair']['directory'])
    assembled = json.loads((candidate/'report.json').read_text())
    assert assembled['schema'] == flow.assembly.CANDIDATE_SCHEMA
    assert assembled['independent_panel_approval'] is False
    assert all(row['independently_approved'] is False for row in assembled['revisions'])
    for part in ('source', *p.PANELS):
        selected = repaired if part in state['flagged'] else package
        assert (candidate/part/'artwork.svg').read_bytes() == (selected/part/'artwork.svg').read_bytes()
    for part in state['flagged']:
        scene = deepcopy(panel_scene(part)); scene['texts'][0]['text'] = 'Fixture revised '+part
        assert json.loads((repaired/part/'accepted-scene.json').read_text()) == scene
    final = json.loads(json.loads((out/'final-review-request.json').read_text())['user'])
    assert {r['panel']: r['headline'] for r in final['panels']} == {
        part: 'Fixture revised '+part if part in state['flagged'] else 'Fixture headline' for part in p.PANELS}
    with zipfile.ZipFile(candidate/'infographics.zip') as archive:
        assert len(archive.namelist()) == 19
        assert archive.read('supplier-brief.json') == (package/'delivery/supplier-brief.json').read_bytes()
        assert archive.read('style.json') == (package/'delivery/style.json').read_bytes()
    assert before == {str(f.relative_to(package)): f.read_bytes() for f in package.rglob('*') if f.is_file()}


def test_final_screen_rechecks_untouched_panels_and_stops_without_assembly(pipeline):
    package, state = pipeline; state['final_flag'] = 'materials'
    out, report = flow.run(package)
    assert report['status'] == 'needs_revision' and report['candidate'] is None
    assert report['model_calls']['headlines'] == 6
    assert not list(p.ROOT.glob('reviewed-package-*'))
    assert (out/'final-review-response.json').is_file()


def test_supported_original_uses_single_screen_and_keeps_whole_package_pending(pipeline):
    package, state = pipeline; state['flagged'] = []
    out, report = flow.run(package)
    assert report['status'] == 'pending_independent_review', report
    assert Path(report['candidate']['directory']) == package and report['repair'] is None
    assert flow.verify(out)['model_calls']['headlines'] == 1
    assert len(state['calls']) == 1 and not list(p.ROOT.glob('reviewed-package-*'))


def test_failed_repair_stops_at_existing_three_attempt_budget(pipeline):
    package, state = pipeline; state['reject_writes'] = True
    out, report = flow.run(package)
    assert report['status'] == 'failed' and report['candidate'] is None
    assert report['model_calls']['repair'] == 3 and len(state['calls']) == 4
    assert not list(out.glob('final-review-request.json'))
    assert not list(p.ROOT.glob('reviewed-package-*'))


@pytest.mark.parametrize('fault', ['source', 'repair', 'candidate', 'budget', 'acceptance', 'final_prompt', 'unbound_response'])
def test_replay_rejects_changed_provenance_or_claims_even_with_rebound_artifact_hash(pipeline, fault):
    package, _ = pipeline; out, report = flow.run(package)
    assert report['status'] == 'pending_independent_review', report
    if fault in ('source', 'repair', 'candidate'):
        folder = Path(report[fault]['directory'])
        original = json.loads((folder/'report.json').read_text()); original['tampered'] = True
        p.school.save(folder/'report.json', original)
    elif fault == 'budget': report['budgets']['maximum_headline_calls'] += 1
    elif fault == 'acceptance': report['whole_package_accepted'] = True
    elif fault == 'unbound_response': del report['artifacts']['final-review-response.json']
    else:
        name = 'final-review-request.json'; request = json.loads((out/name).read_text())
        request['user'] += 'Unrecorded instruction'
        p.school.save(out/name, request); report['artifacts'][name] = p.school.checksum(out/name)
    p.school.save(out/'report.json', report)
    with pytest.raises(ValueError): flow.verify(out)


def test_generation_failure_cannot_start_headline_work(pipeline, monkeypatch):
    package, state = pipeline; received = []
    def generate(**kwargs):
        received.append(kwargs)
        return package, {'status': 'failed'}
    monkeypatch.setattr(p, 'run', generate)
    _, report = flow.run()
    assert report['status'] == 'failed' and not state['calls']
    assert received == [{'sampling_profile': 'qwen-deliberate-trial.v1', 'functional_callouts': True,
        'focused_stages': True, 'recover_incomplete': True, 'source_contour': True, 'source_lesson': None}]


def test_fresh_generation_continues_through_same_complete_pipeline(pipeline, monkeypatch):
    package, _ = pipeline
    for name in ('style', 'source', *p.PANELS): p.school.save(package/(name+'-request.json'), {'fixture': True})
    monkeypatch.setattr(p, 'run', lambda **kwargs: (package, {'status': 'pending_independent_review'}))
    out, report = flow.run()
    assert report['status'] == 'pending_independent_review', report
    assert report['generated_here'] and flow.verify(out)['model_calls']['generation'] == 6


@pytest.mark.parametrize('fault', ['style', 'brief', 'untouched_panel', 'source_artwork', 'annotation',
    'false_panel_approval', 'metadata', 'source_png'])
def test_candidate_rejects_protected_changes_even_when_hashes_are_rebound(pipeline, fault):
    package, _ = pipeline; out, workflow = flow.run(package)
    candidate = Path(workflow['candidate']['directory'])
    report = json.loads((candidate/'report.json').read_text())
    if fault in ('style', 'brief'):
        path = candidate/'delivery'/('style.json' if fault == 'style' else 'supplier-brief.json')
        value = json.loads(path.read_text()); value['unrequested'] = True; p.school.save(path, value)
    elif fault in ('untouched_panel', 'source_artwork'):
        path = candidate/('materials' if fault == 'untouched_panel' else 'source')/'artwork.svg'
        path.write_text(path.read_text().replace('#003388', '#123456'))
    elif fault == 'annotation': report['annotation_contract'] = 'functional-callouts.v2'
    elif fault == 'metadata': report['protected_contracts']['supplier_copy_contract'] = 'invented'
    elif fault == 'source_png': Image.new('RGB', (50, 50), 'white').save(candidate/'source/preview.png')
    else: report['independent_panel_approval'] = True
    report['artifacts'] = {name: p.school.checksum(candidate/name) for name in report['artifacts']}
    p.school.save(candidate/'report.json', report)
    with pytest.raises(ValueError): flow.assembly.verify(candidate)


def test_call_counter_enforces_global_four_panel_budget(tmp_path, monkeypatch):
    monkeypatch.setattr(flow.probe.revision, 'ROOT', tmp_path)
    folder = tmp_path/'repair'; folder.mkdir(); p.school.save(folder/'report.json', {})
    for index in range(25): (folder/(str(index)+'-request.json')).write_text('{}')
    with pytest.raises(ValueError, match='budget'): flow.call_counts(tmp_path, {'repair': flow.binding(folder)})


def late_provider(monkeypatch, state, *, final_veto=None, reject_first=False):
    config = {'model': 'fixture-model', 'digest': 'a'*64}
    state['late_review_calls'] = 0
    state['late_writer_calls'] = 0
    class Provider:
        def __init__(self, conf): self.conf = conf
        def complete(self, messages):
            system, user = (m['content'] for m in messages)
            if system == flow.repair.SYSTEM:
                state['late_writer_calls'] += 1
                data, _ = json.JSONDecoder().raw_decode(user)
                value = {'headline': (data['scene']['texts'][0]['text']
                    if reject_first and state['late_writer_calls'] == 1 else 'Late local correction')}
            else:
                state['late_review_calls'] += 1
                data = json.loads(user)
                # First review is the per-panel critic; second is the mandatory
                # common review of every selected panel.
                veto = final_veto if state['late_review_calls'] > 1 else None
                value = {'reviews': [{'panel': row['panel'],
                    'verdict': 'uncertain' if row['panel'] == veto else 'supported',
                    'reason': 'Synthetic bounded replay judgment.', 'evidence': []}
                    for row in data['panels']]}
            return config | {'content': json.dumps(value)}
    monkeypatch.setattr(p.brand, 'OllamaProvider', Provider)


def stopped_v1(pipeline):
    package, state = pipeline
    state['final_flag'] = 'materials'
    out, report = flow.run(package)
    assert report['status'] == 'needs_revision' and report['candidate'] is None
    return package, state, out, report


def test_v2_repairs_late_final_defect_and_protects_every_other_panel(pipeline, monkeypatch):
    package, state, previous_out, previous = stopped_v1(pipeline)
    historical = {str(f.relative_to(previous_out)): f.read_bytes() for f in previous_out.rglob('*') if f.is_file()}
    late_provider(monkeypatch, state)
    out, report = correction.run(previous_out)
    assert report['status'] == 'pending_independent_review', report
    proof = correction.verify(out)
    assert proof['protected_panels'] == ['capacity', 'dimensions', 'care']
    assert report['model_calls'] == {'inherited_v1': 6, 'writer': 1, 'panel_review': 1,
        'full_review': 1, 'correction': 3, 'aggregate': 9}
    candidate = Path(report['candidate']['directory'])
    prior = Path(previous['repair']['directory'])
    for panel in proof['protected_panels']:
        selected = prior if panel in state['flagged'] else package
        assert (candidate/panel/'artwork.svg').read_bytes() == (selected/panel/'artwork.svg').read_bytes()
    assert b'Late local correction' in (candidate/'materials/artwork.svg').read_bytes()
    assert historical == {str(f.relative_to(previous_out)): f.read_bytes() for f in previous_out.rglob('*') if f.is_file()}
    assert not proof['whole_package_accepted'] and proof['independent_review_required']


def test_v2_full_common_review_veto_stops_without_candidate(pipeline, monkeypatch):
    _, state, previous_out, _ = stopped_v1(pipeline)
    late_provider(monkeypatch, state, final_veto='dimensions')
    out, report = correction.run(previous_out)
    assert report['status'] == 'needs_revision' and report['candidate'] is None
    assert (out/'full-review.json').is_file()
    assert not list(p.ROOT.glob('reviewed-package-*'))


def test_v2_declared_global_budget_is_enforced(tmp_path):
    repair_folder = tmp_path/'late'; repair_folder.mkdir()
    for index in range(13): (repair_folder/f'writer-revision-{index}-request.json').write_text('{}')
    previous = {'model_calls': {'headlines': 5}}
    with pytest.raises(ValueError, match='budget'):
        correction._counts(tmp_path, repair_folder, previous)


def test_v2_replays_rejected_writer_attempt_before_literal_acceptance(pipeline, monkeypatch):
    _, state, previous_out, _ = stopped_v1(pipeline)
    late_provider(monkeypatch, state, reject_first=True)
    out, report = correction.run(previous_out)
    assert report['status'] == 'pending_independent_review', report
    assert report['model_calls']['writer'] == 2 and report['model_calls']['panel_review'] == 1
    assert correction.verify(out)['literal_local_authorship_required']
    repair_folder = Path(report['repair']['directory'])/'materials'
    assert (repair_folder/'writer-feedback.json').is_file()
    assert (repair_folder/'writer-revision-1-response.json').is_file()


def test_v2_verify_rejects_protected_content_change_even_if_candidate_hashes_rebound(pipeline, monkeypatch):
    _, state, previous_out, _ = stopped_v1(pipeline)
    late_provider(monkeypatch, state)
    out, report = correction.run(previous_out)
    assert report['status'] == 'pending_independent_review', report
    candidate = Path(report['candidate']['directory'])
    candidate_report = json.loads((candidate/'report.json').read_text())
    path = candidate/'dimensions/artwork.svg'
    path.write_text(path.read_text().replace('#003388', '#123456'))
    candidate_report['artifacts']['dimensions/artwork.svg'] = p.school.checksum(path)
    p.school.save(candidate/'report.json', candidate_report)
    report['candidate'] = correction.v1.binding(candidate)
    p.school.save(out/'report.json', report)
    with pytest.raises(ValueError): correction.verify(out)


def rebind_repair_file(repair_folder, relative, value):
    path = repair_folder/relative
    p.school.save(path, value)
    report = json.loads((repair_folder/'report.json').read_text())
    report['artifacts'][str(relative)] = p.school.checksum(path)
    p.school.save(repair_folder/'report.json', report)


@pytest.mark.parametrize('fault', ['supplier_fact', 'teacher_hint', 'critic_payload', 'config'])
def test_v2_standalone_assembly_rejects_rebound_fake_authorship_inputs(pipeline, monkeypatch, fault):
    package, state, previous_out, _ = stopped_v1(pipeline)
    late_provider(monkeypatch, state)
    out, workflow = correction.run(previous_out)
    assert workflow['status'] == 'pending_independent_review', workflow
    repair_folder = Path(workflow['repair']['directory'])
    report = json.loads((repair_folder/'report.json').read_text())
    if fault == 'config':
        report['config']['num_predict'] = 4096
        p.school.save(repair_folder/'report.json', report)
    elif fault in ('supplier_fact', 'teacher_hint'):
        relative = Path('materials/writer-input.json')
        value = json.loads((repair_folder/relative).read_text())
        if fault == 'supplier_fact': value['panel']['supplier_facts'][0] = 'Body: invented alloy'
        else: value['teacher_hint'] = 'Use the preferred answer'
        rebind_repair_file(repair_folder, relative, value)
        report = json.loads((repair_folder/'report.json').read_text())
        request = json.loads((repair_folder/'materials/writer-request.json').read_text())
        request['user'] = json.dumps(value)
        rebind_repair_file(repair_folder, Path('materials/writer-request.json'), request)
    else:
        relative = Path('materials/critic-0-request.json')
        request = json.loads((repair_folder/relative).read_text())
        payload = json.loads(request['user']); payload['panels'][0]['supplier_facts'][0] = 'Invented reviewer fact'
        request['user'] = json.dumps(payload)
        rebind_repair_file(repair_folder, relative, request)
    with pytest.raises(ValueError): correction.selected_sources(package, repair_folder)


def test_v2_verify_requires_every_named_implementation_snapshot_even_if_report_is_rebound(pipeline, monkeypatch):
    _, state, previous_out, _ = stopped_v1(pipeline)
    late_provider(monkeypatch, state)
    out, workflow = correction.run(previous_out)
    assert workflow['status'] == 'pending_independent_review', workflow
    report = json.loads((out/'report.json').read_text())
    missing = 'implementation/product_delivery_correction.py'
    del report['artifacts'][missing]
    (out/missing).unlink()
    p.school.save(out/'report.json', report)
    with pytest.raises(ValueError, match='snapshots'): correction.verify(out)


def test_v2_verify_rejects_rebound_top_level_sampling_change(pipeline, monkeypatch):
    _, state, previous_out, _ = stopped_v1(pipeline)
    late_provider(monkeypatch, state)
    out, workflow = correction.run(previous_out)
    assert workflow['status'] == 'pending_independent_review', workflow
    workflow['config']['timeout_seconds'] = 180
    p.school.save(out/'report.json', workflow)
    with pytest.raises(ValueError, match='configuration'): correction.verify(out)
