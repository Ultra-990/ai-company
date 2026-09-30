"""One bounded correction cycle after a v1 delivery's final common veto.

The pinned local model remains the only headline author.  A panel critic is
only iteration feedback; it cannot overrule the final common review, and a
passing common review still leaves the assembled package pending independent
review.  Historical v1 artifacts are read only.
"""
from contextlib import nullcontext
from copy import deepcopy
import json
from pathlib import Path
import shutil
import tempfile
import time

from scripts import product_delivery_workflow as v1

product, probe, repair, assembly = v1.product, v1.probe, v1.repair, v1.assembly
CONTRACT = 'product-complete-delivery-correction.v2'
REPAIR_CONTRACT = 'product-headline-late-correction.v2'
BUDGET = {'correction_cycles': 1, 'panels': 4, 'writer_calls_per_panel': 3,
    'panel_review_calls_per_panel': 3, 'full_review_calls': 1,
    'maximum_correction_calls': 25, 'maximum_v1_and_correction_calls': 51}
IMPLEMENTATION = ('product_delivery_correction.py', 'product_delivery_workflow.py', 'product_headline_probe.py',
    'product_headline_repair.py', 'product_revised_package.py', 'product_infographic_school.py',
    'product_correction_evidence.py', 'product_visual_revision.py')
CONFIG_KNOBS = {'sampling_profile': 'bounded-default.v1', 'think': False, 'num_ctx': 8192,
    'num_predict': 2048, 'num_thread': 4, 'timeout_seconds': 90}


def _check_config(config, original):
    allowed = {'enabled', 'model', 'digest', *CONFIG_KNOBS}
    if (set(config) - allowed or (config.get('model'), config.get('digest')) != (original['model'], original['digest'])
            or any(config.get(k) != value for k, value in CONFIG_KNOBS.items())
            or ('enabled' in config and not isinstance(config['enabled'], bool))):
        raise ValueError('Frozen v2 model identity and sampling configuration required')


def _read(path): return probe.revision.read(Path(path))


def _v1_state(folder):
    folder = Path(folder); report = _read(folder/'report.json')
    if (report.get('schema') != v1.CONTRACT or report.get('status') != 'needs_revision'
            or report.get('candidate') is not None or report.get('final_review_mode') != 'all_selected_headlines'
            or report.get('budgets') != v1.BUDGET):
        raise ValueError('A stopped v1 final common review with no candidate is required')
    for name, digest in report['artifacts'].items():
        path = probe.revision.bounded(folder/name)
        if not path.resolve().is_relative_to(folder.resolve()) or product.school.checksum(path) != digest:
            raise ValueError('Historical v1 artifact changed')
    config_limits = {'sampling_profile': 'bounded-default.v1', 'think': False,
        'num_ctx': 8192, 'num_predict': 2048, 'num_thread': 4, 'timeout_seconds': 90}
    if any(report['config'].get(k) != value for k, value in config_limits.items()):
        raise ValueError('Historical v1 final-review configuration changed')
    if report.get('model_calls') != v1.call_counts(folder, report):
        raise ValueError('Historical v1 model-call count changed')
    source, initial, prior = v1.bound(report['source']), v1.bound(report['initial_review']), v1.bound(report['repair'])
    original, data, _ = v1.selected_data(source, initial, prior)
    expected = {'system': probe.SYSTEM, 'user': json.dumps(data), 'format': probe.schema()}
    if _read(folder/'final-review-request.json') != expected:
        raise ValueError('The v1 final review did not cover its exact selected set')
    response = _read(folder/'final-review-response.json')
    if (response['model'], response['digest']) != (original['model'], original['digest']):
        raise ValueError('Historical final reviewer changed')
    final = probe.validate(response['content'], data)
    if final != _read(folder/'final-review.json'):
        raise ValueError('Historical final verdict changed')
    rejected = [row for row in final['reviews'] if row['verdict'] != 'supported']
    if not rejected: raise ValueError('No unresolved final-review panel exists')
    return report, source, prior, original, data, rejected


def _counts(out, repair_folder, previous):
    writer = len(list(Path(repair_folder).rglob('writer*-request.json'))) if repair_folder else 0
    critics = len(list(Path(repair_folder).rglob('critic-*-request.json'))) if repair_folder else 0
    full = len(list(Path(out).glob('full-review-request.json')))
    correction = writer+critics+full
    inherited = previous['model_calls']['headlines']
    if writer > 12 or critics > 12 or full > 1 or correction > 25 or inherited+correction > 51:
        raise ValueError('Declared global correction budget exceeded')
    return {'inherited_v1': inherited, 'writer': writer, 'panel_review': critics,
        'full_review': full, 'correction': correction, 'aggregate': inherited+correction}


def _repair(out, previous_folder, source, prior, original, data, rejected, config):
    folder = out/'late-repair'; folder.mkdir()
    report = {'schema': REPAIR_CONTRACT, 'status': 'running', 'package': str(source),
        'previous': {'directory': str(previous_folder), 'report_sha256': product.school.checksum(Path(previous_folder)/'report.json')},
        'prior_repair': v1.binding(prior), 'panels': [], 'config': config,
        'max_writer_calls_per_panel': 3, 'max_reviewer_calls_per_panel': 3,
        'whole_package_accepted': False, 'independent_review_required': True}
    product.school.save(folder/'report.json', report)
    case = probe.exam.matching_case(original)
    try:
        with probe.exam.exercise_context(case) if case else nullcontext():
            style = product.style_value(product.accepted_raw(source, 'style'))
            source_svg = product.compile_scene(product.accepted_raw(source, 'source'), style)
            for finding in rejected:
                panel = finding['panel']; target = folder/panel; target.mkdir()
                scene = product.parse(product.accepted_raw(source, panel))
                # Apply an already-authenticated v1 change before the late edit.
                prior_entry = next((x for x in _read(prior/'report.json')['panels'] if x['panel'] == panel), None)
                if prior_entry: scene = _read(prior/panel/'accepted-scene.json')
                panel_data = next(row for row in data['panels'] if row['panel'] == panel)
                writer_data = {'panel': panel_data, 'scene': scene, 'final_common_review': finding}
                product.school.save(target/'original-scene.json', scene)
                product.school.save(target/'writer-input.json', writer_data)
                geometry = product.checked_scene(target, 'candidate', style, panel=panel, product=source_svg,
                    placement_contract=original['placement_contract'], annotation_contract=original['annotation_contract'],
                    copy_contract=original['supplier_copy_contract'], paint_separation=True)
                attempt = 0
                def validate(raw):
                    nonlocal attempt
                    index = attempt; attempt += 1
                    changed = repair.apply(scene, raw); svg = geometry(json.dumps(changed))
                    selected = deepcopy(data)
                    next(row for row in selected['panels'] if row['panel'] == panel)['headline'] = changed['texts'][0]['text']
                    answer = product.brand.call(target, 'critic-'+str(index), probe.SYSTEM,
                        json.dumps(selected), probe.schema(), config | {'num_predict': 2048})
                    verdict = probe.validate(answer, selected)
                    product.school.save(target/('critic-'+str(index)+'.json'), verdict)
                    decision = next(row for row in verdict['reviews'] if row['panel'] == panel)
                    if decision['verdict'] != 'supported':
                        raise ValueError('Panel critic rejected the local correction: '+json.dumps(decision))
                    product.school.save(target/'accepted-scene.json', changed)
                    (target/'artwork.svg').write_text(svg)
                    return {'panel': panel, 'headline': changed['texts'][0]['text'], 'accepted_attempt': index,
                        'layout': 'candidate-layout-'+str(len(list(target.glob('candidate-layout-*')))-1)}
                entry = product.brand.validated_call(target, 'writer', repair.SYSTEM, json.dumps(writer_data),
                    repair.SCHEMA, config | {'num_predict': 512}, validate)
                report['panels'].append(entry)
        report['status'] = 'pending_independent_review'
    except Exception as exc:
        report.update(status='failed', error_type=type(exc).__name__, error=str(exc)[:1000])
    report['artifacts'] = {str(p.relative_to(folder)): product.school.checksum(p)
        for p in folder.rglob('*') if p.is_file() and p.name != 'report.json'}
    product.school.save(folder/'report.json', report)
    return folder, report


def selected_sources(package, folder):
    """Assembly adapter: prior v1 repairs plus v2 late repairs."""
    package, folder = Path(package), Path(folder); report = _read(folder/'report.json')
    if report.get('schema') != REPAIR_CONTRACT or report.get('status') != 'pending_independent_review':
        raise ValueError('Completed v2 late repair required')
    for name, digest in report['artifacts'].items():
        path = probe.revision.bounded(folder/name)
        if not path.resolve().is_relative_to(folder.resolve()) or product.school.checksum(path) != digest:
            raise ValueError('Late repair artifact changed')
    actual_artifacts = {str(path.relative_to(folder)) for path in folder.rglob('*')
        if path.is_file() and path.name != 'report.json'}
    if set(report['artifacts']) != actual_artifacts:
        raise ValueError('Every and only late repair artifact must be bound')
    prior = v1.bound(report['prior_repair'])
    original = _read(package/'report.json'); _check_config(report['config'], original)
    if report.get('max_writer_calls_per_panel') != 3 or report.get('max_reviewer_calls_per_panel') != 3:
        raise ValueError('Late repair author or per-panel budget changed')
    previous_folder = Path(report['previous']['directory'])
    if product.school.checksum(probe.revision.bounded(previous_folder/'report.json')) != report['previous']['report_sha256']:
        raise ValueError('Late repair lost its v1 provenance')
    _, previous_source, previous_prior, previous_original, authenticated_data, rejected = _v1_state(previous_folder)
    if (previous_source.resolve() != package.resolve() or previous_prior.resolve() != prior.resolve()
            or (previous_original['model'], previous_original['digest']) != (original['model'], original['digest'])):
        raise ValueError('Late repair belongs to a different v1 selection')
    findings = {row['panel']: row for row in rejected}
    if [row['panel'] for row in report['panels']] != [row['panel'] for row in rejected]:
        raise ValueError('Late repair scope differs from the authenticated final veto')
    from scripts import product_correction_evidence as evidence
    case = probe.exam.matching_case(original)
    with probe.exam.exercise_context(case) if case else nullcontext():
        style = product.style_value(product.accepted_raw(package, 'style'))
        source_svg = product.compile_scene(product.accepted_raw(package, 'source'), style)
        prior_entries = {x['panel']: x for x in _read(prior/'report.json')['panels']}
        for entry in report['panels']:
            panel = entry['panel']; target = folder/panel
            base = (_read(prior/panel/'accepted-scene.json') if panel in prior_entries
                    else product.parse(product.accepted_raw(package, panel)))
            writer_input = {'panel': next(row for row in authenticated_data['panels'] if row['panel'] == panel),
                'scene': base, 'final_common_review': findings[panel]}
            if (_read(target/'original-scene.json') != base
                    or _read(target/'writer-request.json') != {'system': repair.SYSTEM,
                        'user': json.dumps(writer_input), 'format': repair.SCHEMA}
                    or _read(target/'writer-input.json') != writer_input):
                raise ValueError('Late writer received modified scene or hidden instructions')
            bound = {'model': original['model'], 'digest': original['digest'], 'artifacts': {
                name[len(panel)+1:]: digest for name, digest in report['artifacts'].items() if name.startswith(panel+'/')}}
            chain = evidence.verify_stage(target, 'writer', bound)
            if chain['accepted_attempt'] != entry['accepted_attempt'] or chain['requests'] > 3:
                raise ValueError('Late writer attempt selection or budget changed')
            accepted_name = 'writer' if chain['accepted_attempt'] == 0 else 'writer-revision-'+str(chain['accepted_attempt'])
            changed = repair.apply(base, _read(target/(accepted_name+'-response.json'))['content'])
            svg = product.compile_scene(json.dumps(changed), style, panel=panel, product=source_svg,
                placement_contract=original['placement_contract'], copy_contract=original['supplier_copy_contract'])
            if (_read(target/'accepted-scene.json') != changed or entry['headline'] != changed['texts'][0]['text']
                    or probe.revision.bounded(target/'artwork.svg').read_text() != svg
                    or probe.revision.bounded(target/entry['layout']/'artwork.svg').read_text() != svg):
                raise ValueError('Late correction differs from the accepted local response')
            critic_requests = sorted(target.glob('critic-*-request.json'))
            if (len(critic_requests) > 3
                    or not (target/('critic-'+str(chain['accepted_attempt'])+'-request.json')).is_file()):
                raise ValueError('Accepted writer attempt requires a bounded panel review')
            for request_path in critic_requests:
                index = int(request_path.name.split('-')[1])
                writer_name = 'writer' if index == 0 else 'writer-revision-'+str(index)
                candidate = repair.apply(base, _read(target/(writer_name+'-response.json'))['content'])
                request = _read(request_path); review_data = deepcopy(authenticated_data)
                next(row for row in review_data['panels'] if row['panel'] == panel)['headline'] = candidate['texts'][0]['text']
                selected = next(row for row in review_data['panels'] if row['panel'] == panel)
                if (set(request) != {'system', 'user', 'format'} or request['system'] != probe.SYSTEM
                        or request['format'] != probe.schema() or request['user'] != json.dumps(review_data)
                        or selected['headline'] != candidate['texts'][0]['text']):
                    raise ValueError('Panel critic reviewed a substituted headline or hidden prompt')
                response = _read(target/('critic-'+str(index)+'-response.json'))
                if (response['model'], response['digest']) != (original['model'], original['digest']):
                    raise ValueError('Panel critic identity changed')
                verdict = probe.validate(response['content'], review_data)
                if verdict != _read(target/('critic-'+str(index)+'.json')):
                    raise ValueError('Panel critic verdict changed')
            accepted_verdict = _read(target/('critic-'+str(chain['accepted_attempt'])+'.json'))
            if next(row for row in accepted_verdict['reviews'] if row['panel'] == panel)['verdict'] != 'supported':
                raise ValueError('Accepted late headline lacks its panel review')
    sources = {name: package/name/'artwork.svg' for name in ('source', *product.PANELS)}
    bindings = []
    for origin, entries in ((prior, _read(prior/'report.json')['panels']), (folder, report['panels'])):
        for entry in entries:
            part = entry['panel']; sources[part] = origin/part/'artwork.svg'
            bindings = [x for x in bindings if x['part'] != part]
            bindings.append({'part': part, 'report': str(origin/'report.json'),
                'report_sha256': product.school.checksum(origin/'report.json'),
                'svg_sha256': product.school.checksum(sources[part]), 'independently_approved': False})
    return sources, bindings


def verify(out):
    out = Path(out); report = _read(out/'report.json')
    if (report.get('schema') != CONTRACT or report.get('status') != 'pending_independent_review'
            or report.get('budgets') != BUDGET or report.get('independent_review_required') is not True
            or any(report.get(k) is not False for k in ('training_exported', 'exam_score_changed',
                'production_changed', 'whole_package_accepted'))):
        raise ValueError('Completed bounded v2 workflow without acceptance claims required')
    previous_folder = Path(report['previous']['directory'])
    if product.school.checksum(probe.revision.bounded(previous_folder/'report.json')) != report['previous']['report_sha256']:
        raise ValueError('Historical v1 report changed')
    previous, source, prior, original, data, rejected = _v1_state(previous_folder)
    _check_config(report['config'], original)
    required_snapshots = {'implementation/'+name for name in IMPLEMENTATION}
    implementation_artifacts = {name for name in report['artifacts'] if name.startswith('implementation/')}
    if implementation_artifacts != required_snapshots or any(not (out/name).is_file() for name in required_snapshots):
        raise ValueError('Exact required v2 implementation snapshots must be bound')
    actual_artifacts = {str(path.relative_to(out)) for path in out.rglob('*')
        if path.is_file() and path.name not in ('report.json', 'verification.json')}
    if set(report['artifacts']) != actual_artifacts:
        raise ValueError('Every and only correction workflow artifact must be bound')
    if report['source'] != v1.binding(source) or report['triggered_panels'] != [r['panel'] for r in rejected]:
        raise ValueError('Late correction scope changed')
    expected_protected = [p for p in product.PANELS if p not in set(report['triggered_panels'])]
    if report['protected_panels'] != expected_protected:
        raise ValueError('Protected panel declaration changed')
    repaired = Path(report['repair']['directory'])
    if product.school.checksum(repaired/'report.json') != report['repair']['report_sha256']:
        raise ValueError('Late repair report changed')
    sources, _ = selected_sources(source, repaired)
    repair_report = _read(repaired/'report.json')
    if [x['panel'] for x in repair_report['panels']] != report['triggered_panels']:
        raise ValueError('Only final-vetoed panels may be corrected')
    selected = deepcopy(data)
    for entry in repair_report['panels']:
        scene = _read(repaired/entry['panel']/'accepted-scene.json')
        if scene['texts'][0]['text'] != entry['headline']:
            raise ValueError('Accepted local headline changed')
        next(row for row in selected['panels'] if row['panel'] == entry['panel'])['headline'] = entry['headline']
    expected = {'system': probe.SYSTEM, 'user': json.dumps(selected), 'format': probe.schema()}
    if _read(out/'full-review-request.json') != expected:
        raise ValueError('Full common review must cover the exact selected package')
    response = _read(out/'full-review-response.json')
    if (response['model'], response['digest']) != (original['model'], original['digest']):
        raise ValueError('Pinned common reviewer changed')
    final = probe.validate(response['content'], selected)
    if final != _read(out/'full-review.json') or any(x['verdict'] != 'supported' for x in final['reviews']):
        raise ValueError('A full common-review veto remains')
    candidate = v1.bound(report['candidate']); proof = assembly.verify(candidate)
    candidate_report = _read(candidate/'report.json')
    if Path(candidate_report['candidate_headlines']) != repaired:
        raise ValueError('Candidate uses different correction evidence')
    # The assembly verifier compares every artifact to these selected sources;
    # make the protected-panel source choice explicit in this contract too.
    for panel in expected_protected:
        expected_source = prior/panel/'artwork.svg' if any(x['panel'] == panel for x in _read(prior/'report.json')['panels']) else source/panel/'artwork.svg'
        if sources[panel].read_bytes() != expected_source.read_bytes() or (candidate/panel/'artwork.svg').read_bytes() != expected_source.read_bytes():
            raise ValueError('Protected panel changed')
    counts = _counts(out, repaired, previous)
    if report['model_calls'] != counts: raise ValueError('Recorded global model-call count changed')
    for name, digest in report['artifacts'].items():
        path = probe.revision.bounded(out/name)
        if not path.resolve().is_relative_to(out.resolve()) or product.school.checksum(path) != digest:
            raise ValueError('Correction workflow artifact changed')
    return {'schema': CONTRACT, 'verified': True, 'candidate': str(candidate),
        'candidate_verification': proof, 'model_calls': counts, 'protected_panels': expected_protected,
        'literal_local_authorship_required': True, 'independent_review_required': True,
        'whole_package_accepted': False, 'training_exported': False}


def run(v1_folder):
    previous, source, prior, original, data, rejected = _v1_state(v1_folder)
    out = Path(tempfile.mkdtemp(prefix='delivery-correction-', dir=product.ROOT))
    implementation = out/'implementation'; implementation.mkdir()
    for name in IMPLEMENTATION:
        shutil.copyfile(Path(__file__).with_name(name), implementation/name)
    config = product.configuration() | CONFIG_KNOBS
    if (config['model'], config['digest']) != (original['model'], original['digest']):
        raise ValueError('Pinned original local author required')
    report = {'schema': CONTRACT, 'status': 'running', 'budgets': deepcopy(BUDGET),
        'previous': {'directory': str(v1_folder), 'report_sha256': product.school.checksum(Path(v1_folder)/'report.json')},
        'source': v1.binding(source), 'protected_panels': [p for p in product.PANELS if p not in {r['panel'] for r in rejected}],
        'triggered_panels': [r['panel'] for r in rejected], 'repair': None, 'candidate': None,
        'config': config, 'training_exported': False, 'exam_score_changed': False,
        'production_changed': False, 'whole_package_accepted': False, 'independent_review_required': True}
    started = time.monotonic()
    def persist():
        report['elapsed_seconds'] = round(time.monotonic()-started, 3); product.school.save(out/'report.json', report)
    persist()
    try:
        repaired, repair_report = _repair(out, v1_folder, source, prior, original, data, rejected, config)
        report['repair'] = {'directory': str(repaired), 'report_sha256': product.school.checksum(repaired/'report.json')}; persist()
        if repair_report['status'] != 'pending_independent_review': raise ValueError('Late bounded repair failed')
        selected = deepcopy(data)
        for entry in repair_report['panels']:
            next(row for row in selected['panels'] if row['panel'] == entry['panel'])['headline'] = entry['headline']
        raw = product.brand.call(out, 'full-review', probe.SYSTEM, json.dumps(selected), probe.schema(), config)
        final = probe.validate(raw, selected); product.school.save(out/'full-review.json', final)
        if any(row['verdict'] != 'supported' for row in final['reviews']):
            report['status'] = 'needs_revision'
        else:
            candidate, candidate_report = assembly.run(source, candidate_headlines=repaired)
            if candidate_report['status'] != 'pending_independent_review': raise ValueError('Candidate assembly failed')
            report.update(candidate=v1.binding(candidate), status='pending_independent_review')
    except Exception as exc:
        report.update(status='failed', error_type=type(exc).__name__, error=str(exc)[:1000])
    finally:
        try: report['model_calls'] = _counts(out, Path(report['repair']['directory']) if report['repair'] else None, previous)
        except Exception as exc: report.update(status='failed', error_type=type(exc).__name__, error=str(exc)[:1000])
        report['artifacts'] = {str(p.relative_to(out)): product.school.checksum(p)
            for p in out.rglob('*') if p.is_file() and p.name != 'report.json'}; persist()
    if report['status'] == 'pending_independent_review':
        try: product.school.save(out/'verification.json', verify(out))
        except Exception as exc:
            report.update(status='failed', error_type=type(exc).__name__, error=str(exc)[:1000]); persist()
    return out, report
