"""Resume known brand failures with measured feedback and local scene authorship."""
import asyncio
from hashlib import sha256
import json
from pathlib import Path
import shutil
import tempfile
import time
import xml.etree.ElementTree as ET
from PIL import Image, ImageChops

from scripts import brand_school as b, verify_brand_package as evidence
from scripts.brand_full_exam import exercise_context

CONTRACT = 'brand-measured-artwork-repair.v2'
LEGACY_CONTRACT = 'brand-measured-artwork-repair.v1'
CARD_CONTRACT = 'brand-measured-artwork-repair.v3'
FULL_CONTRACT = 'brand-measured-artwork-repair.v4'
TASK = 'Correct your previous scene using the independent measured findings. Preserve the brief, approved copy and palette. Return your complete corrected scene, with no invented output files or claims. Positions and geometry remain your responsibility.'
REPAIR_RULES = b.SCENE_RULES.replace('use roughly 330, 390, 435 and 480\nfor the four centered lines unless a different safe spacing is clearly needed.',
    'choose baselines from actual measured text extents and the transformed logo bounds.\nDo not copy a rejected placement unchanged.')


def source_values(source):
    report = evidence.read(source/'report.json')
    if (report.get('schema') != 'restaurant-brand-school.v1'
            or report.get('status') not in ('failed', 'pending_independent_visual_review')
            or report.get('brief_sha256') != sha256(json.dumps(report['brief'], sort_keys=True).encode()).hexdigest()):
        raise ValueError('Original completed package or stopped card stage required')
    if report['status'] == 'failed' and report.get('stages') != ['plan', 'logo-a', 'logo-b']:
        raise ValueError('Only a stopped card stage can be resumed')
    if 'repair_contract' in report: raise ValueError('Use an original source, not recursively nested repairs')
    for name, digest in report['artifacts'].items():
        path = evidence.bounded(source/name)
        if not path.resolve().is_relative_to(source.resolve()) or b.school.checksum(path) != digest:
            raise ValueError('Original artifact changed')
    raw = {stage: evidence.chain(source, stage, report)[0] for stage in ('plan', 'logo-a', 'logo-b', 'selection')}
    if report['status'] == 'failed':
        # The full failed attempt chain is retained in the original. No extra
        # attempt is disguised as belonging to its exhausted three-call budget.
        try:
            evidence.chain(source, 'card', report)
        except ValueError as exc:
            if str(exc) != 'All brand attempts rejected': raise
        else:
            raise ValueError('Stopped source must preserve the exhausted card chain')
        name = 'card-revision-2-response.json'
        response = evidence.read(source/name)
        if name not in report['artifacts'] or (response['model'], response['digest']) != (report['model'], report['digest']):
            raise ValueError('Bound last failed local card response required')
        raw['card'] = response['content']
    else:
        evidence.verify(source)
        raw['card'] = evidence.chain(source, 'card', report)[0]
    with exercise_context(report['brief']):
        plan = b.plan_value(raw['plan'])
        if plan != evidence.read(source/'plan.json'): raise ValueError('Original plan changed')
        logos = {key: b.compile_scene(raw['logo-'+key], plan, kind='logo') for key in ('a', 'b')}
        selection = b.selected_value(raw['selection'])
        if selection != report['selection']: raise ValueError('Original selection changed')
        b.compile_scene(raw['card'], plan, kind='card', logo=logos[selection['selected']])
    return report, raw, plan, logos, selection


def measure(svg, folder, profile, *, contribution=False):
    folder.mkdir(); (folder/'artwork.svg').write_text(svg)
    b.school.check_idle()
    value = asyncio.run(b.render(svg, folder, profile=profile, measure_shape_contribution=contribution))
    b.school.save(folder/'render.json', value)
    return value


def monochrome_findings(color, mono):
    first, second = color['shape_contributions'], mono['shape_contributions']
    if len(first) != len(second): raise ValueError('Matched shape ablations required')
    result = []
    for index, (a, z) in enumerate(zip(first, second)):
        if (a['index'] != index or z['index'] != index or a['tag'] != z['tag']
                or any(type(v['changed_pixels']) is not int or v['changed_pixels'] < 0 for v in (a, z))):
            raise ValueError('Bound ordered shape contribution required')
        if a['changed_pixels'] >= 16 and z['changed_pixels'] < max(2, a['changed_pixels']*.05):
            result.append({'kind': 'monochrome_feature_disappeared', 'shape_index': index,
                'color_changed_pixels': a['changed_pixels'], 'monochrome_changed_pixels': z['changed_pixels'],
                'measurement': 'Pixels changed when this shape alone is hidden, channel difference >=20 on white.'})
    return result


def verify_contributions(folder, measured):
    """Recompute diagnostic counts from the preserved actual screenshots."""
    with Image.open(evidence.bounded(folder/'preview.png')) as image:
        baseline = image.convert('RGB')
    if baseline.size != (600, 360): raise ValueError('Full-size ablation proof required')
    rows = measured['shape_contributions']
    if not 1 <= len(rows) <= 12: raise ValueError('Bounded shape proof required')
    for index, row in enumerate(rows):
        with Image.open(evidence.bounded(folder/('shape-removed-'+str(index)+'.png'))) as image:
            variant = image.convert('RGB')
        if variant.size != baseline.size: raise ValueError('Ablation dimensions changed')
        red, green, blue = ImageChops.difference(baseline, variant).split()
        count = sum(ImageChops.lighter(ImageChops.lighter(red, green), blue).histogram()[20:])
        if row['index'] != index or row['changed_pixels'] != count:
            raise ValueError('Shape contribution differs from actual PNG evidence')


def card_decoration_findings(svg, measured, paper):
    """Conservative text exclusion boxes for card-only shapes, not glyph hit tests.

    Compiled card decorations are direct children in untransformed card units.
    The inserted logo is protected; a full paper-colored rectangle is background.
    Bounding-box intersections require review even for a hollow shape or curve.
    """
    from scripts.brand_spatial_review import box
    root = ET.fromstring(svg)
    tags = {'rect', 'circle', 'ellipse', 'line', 'path'}
    shapes = [e for e in root.iter() if e.tag.rsplit('}', 1)[-1] in tags]
    if len(shapes) != len(measured['shape_layout']):
        raise ValueError('Exact shape-to-render mapping required')
    direct = set(root); findings = []
    for index, (element, shape) in enumerate(zip(shapes, measured['shape_layout'])):
        tag = element.tag.rsplit('}', 1)[-1]
        if tag != shape['tag']: raise ValueError('Measured shape order changed')
        if element not in direct: continue
        if element.get('transform'): raise ValueError('Untransformed card decorations required')
        bounds = box(shape['bbox'])
        fill, stroke = element.get('fill', 'black'), element.get('stroke', 'none')
        if fill == 'none' and stroke == 'none': continue
        if tag == 'rect' and bounds == [0, 0, 850, 550] and fill.lower() == paper.lower() and stroke == 'none':
            continue
        width = float(element.get('stroke-width', '1')) / 2 if stroke != 'none' else 0
        left, top, right, bottom = bounds
        bounds = [left-width, top-width, right+width, bottom+width]
        for row in measured['layout']:
            x, y, u, v = box(row['bbox'])
            overlap = [max(bounds[0], x), max(bounds[1], y), min(bounds[2], u), min(bounds[3], v)]
            if overlap[2] > overlap[0] and overlap[3] > overlap[1]:
                findings.append({'kind': 'card_decoration_in_text_bounds', 'shape_index': index,
                    'shape_bounds': bounds, 'text': row['text'], 'text_bounds': [x, y, u, v],
                    'intersection_bounds': overlap,
                    'measurement': 'Decoration bounding box enters a text exclusion box; curve/glyph intersection is not asserted.'})
    return findings


def diagnose(svg, folder, plan, kind, *, strict_card=False, full_scene=False):
    color = measure(svg, folder, 'brand_'+kind, contribution=kind == 'logo')
    feedback = b.measured_feedback(color, 'brand_'+kind)
    if full_scene:
        from scripts.brand_scene_contract import margin_findings
        feedback['issues'] += margin_findings(svg, color, kind, plan['paper'])
    if kind == 'card' and strict_card:
        feedback['issues'] += card_decoration_findings(svg, color, plan['paper'])
    if kind == 'logo':
        mono = measure(b.monochrome(svg, plan['monochrome_ink']), folder/'monochrome', 'brand_logo', contribution=True)
        feedback['issues'] += monochrome_findings(color, mono)
        feedback['monochrome_shape_contributions'] = mono['shape_contributions']
        feedback['color_shape_contributions'] = color['shape_contributions']
    return feedback


def payload(brief, plan, raw, findings, chosen=None):
    data = {'brief': brief, 'plan': plan, 'previous_scene': json.loads(raw), 'measured_findings': findings, 'task': TASK}
    if chosen is not None: data['chosen_logo_svg'] = chosen
    return json.dumps(data)


def run(source, *, deliberate=False, matched_budget=False, strict_card=False, full_scene=False):
    from scripts import brand_scene_contract as scoped
    strict_card = strict_card or full_scene
    source = Path(source); original, raw, plan, logos, selection = source_values(source)
    resources = b.school.check_idle()
    config = b.configuration() | {'num_ctx': 8192, 'num_predict': 4096, 'num_thread': 4, 'timeout_seconds': 180}
    if deliberate:
        config.update(sampling_profile='qwen-deliberate-trial.v1', think=True, num_ctx=16384, num_predict=8192)
    elif matched_budget:
        config.update(sampling_profile='bounded-default.v1', think=False, num_ctx=16384, num_predict=8192)
    if (config['model'], config['digest']) != (original['model'], original['digest']):
        raise ValueError('Original local model must author the repair')
    out = Path(tempfile.mkdtemp(prefix='artwork-repair-', dir=b.ROOT))
    implementation = out/'implementation'; implementation.mkdir()
    for name in ('brand_artwork_repair.py', 'brand_school.py', 'verify_brand_package.py', 'render_school_svg.py', 'vector_school_contract.py', 'vector_structured_source.py'):
        shutil.copyfile(Path(__file__).parent/name, implementation/name)
    shutil.copyfile(Path(__file__).parents[1]/'app/services/local_ollama.py', implementation/'local_ollama.py')
    if full_scene: shutil.copyfile(Path(scoped.__file__), implementation/'brand_scene_contract.py')
    contract = FULL_CONTRACT if full_scene else CARD_CONTRACT if strict_card else CONTRACT
    record = {'schema': contract, 'source': str(source), 'source_report_sha256': b.school.checksum(source/'report.json'),
              'reused_stages': [], 'repaired_stages': [], 'max_additional_model_calls': 9 if full_scene else 6, 'fresh_exam': False}
    report = {key: original[key] for key in ('schema', 'brief', 'brief_sha256', 'model', 'digest')}
    report.update(status='running', config=config, resources_before=resources, selection=selection,
        stages=['plan', 'logo-a', 'logo-b'], checks={}, repair_contract=contract,
        training_started=False, training_exported=False, production_changed=False, print_ready=False,
        commercial_delivery_approved=False, autonomy_qualified=False, exam_score_changed=False,
        implementation_sha256=b.school.checksum(Path(b.__file__)))
    started = time.monotonic(); print(json.dumps({'output': str(out)}), flush=True)
    def reuse(stage):
        for path in source.glob(stage+'*-*.json'):
            if path.is_file() and any(path.name.endswith('-'+suffix+'.json') for suffix in ('request', 'response', 'feedback')):
                shutil.copyfile(path, out/path.name)
        record['reused_stages'].append(stage)
    def repair(stage, kind, findings, chosen=None):
        attempt = 0
        cache = {json.dumps(json.loads(raw[stage]), sort_keys=True): findings}
        def validate(answer):
            nonlocal attempt
            svg = scoped.compile_scene(answer, plan, kind=kind, brief=original['brief'], logo=chosen) if full_scene else b.compile_scene(answer, plan, kind=kind, logo=chosen)
            key = json.dumps(json.loads(answer), sort_keys=True)
            if key in cache and cache[key]['issues']:
                raise ValueError(json.dumps(cache[key]))
            folder = out/(stage+'-layout-'+str(attempt)); attempt += 1
            feedback = diagnose(svg, folder, plan, kind, strict_card=strict_card, full_scene=full_scene)
            cache[key] = feedback
            if feedback['issues']:
                raise ValueError(json.dumps(feedback))
            return svg
        record['repaired_stages'].append(stage)
        rules = scoped.rules(kind) if full_scene else REPAIR_RULES
        schema = scoped.schema(kind, plan, original['brief']) if full_scene else b.scene_schema(kind, plan)
        return b.validated_call(out, stage, b.INSTRUCTION+'\n'+rules,
            payload(original['brief'], plan, raw[stage], findings, chosen), schema, config, validate)
    try:
        with exercise_context(original['brief']):
            for stage in ('plan', 'selection'): reuse(stage)
            b.school.save(out/'plan.json', plan)
            selected = selection['selected']; stage = 'logo-'+selected
            findings = diagnose(logos[selected], out/'initial-logo', plan, 'logo', full_scene=full_scene)
            b.school.save(out/'initial-logo-feedback.json', findings)
            for key in ('a', 'b'):
                current = findings
                if full_scene and key != selected:
                    current = diagnose(logos[key], out/'initial-alternate', plan, 'logo', full_scene=True)
                    b.school.save(out/'initial-alternate-feedback.json', current)
                if (key == selected or full_scene) and current['issues']:
                    logos[key] = repair('logo-'+key, 'logo', current)
                else: reuse('logo-'+key)
                (out/('logo-'+key+'.svg')).write_text(logos[key])
            chosen = logos[selected]
            card = b.compile_scene(raw['card'], plan, kind='card', logo=chosen)
            findings = diagnose(card, out/'initial-card', plan, 'card', strict_card=strict_card, full_scene=full_scene)
            b.school.save(out/'initial-card-feedback.json', findings)
            if findings['issues'] or original['status'] == 'failed':
                card = repair('card', 'card', findings, chosen)
            else: reuse('card')
            report['stages'].append('card')
            b.assemble(out, plan, logos, selection, card, report)
    except Exception as exc:
        report.update(status='failed', error_type=type(exc).__name__, error=str(exc)[:600])
    finally:
        b.school.save(out/'repair-origin.json', record)
        report['elapsed_seconds'] = round(time.monotonic()-started, 3)
        report['artifacts'] = {str(p.relative_to(out)): b.school.checksum(p) for p in out.rglob('*') if p.is_file() and p.name != 'report.json'}
        b.school.save(out/'report.json', report)
    print(json.dumps({'report': str(out/'report.json'), 'status': report['status'], 'elapsed_seconds': report['elapsed_seconds']}), flush=True)
    return out, report


def verify_origin(out, report):
    from scripts import brand_scene_contract as scoped
    record = evidence.read(out/'repair-origin.json'); source = Path(record['source'])
    full_scene = record.get('schema') == FULL_CONTRACT
    original, raw, plan, logos, selection = source_values(source)
    if (record.get('schema') not in (LEGACY_CONTRACT, CONTRACT, CARD_CONTRACT, FULL_CONTRACT) or report['repair_contract'] != record['schema']
            or record.get('fresh_exam') is not False or record.get('max_additional_model_calls') != (9 if full_scene else 6)
            or b.school.checksum(source/'report.json') != record['source_report_sha256']
            or any(report[k] != original[k] for k in ('brief', 'model', 'digest', 'selection'))
            or any(report.get(k) is not False for k in ('autonomy_qualified', 'exam_score_changed', 'training_exported'))):
        raise ValueError('Original repair provenance changed')
    repaired, reused = record['repaired_stages'], record['reused_stages']
    allowed = {'logo-a', 'logo-b', 'card'} if full_scene else {'logo-'+selection['selected'], 'card'}
    if (set(repaired) - allowed or set(repaired) & set(reused)
            or sorted(repaired+reused) != sorted(evidence.STAGES)):
        raise ValueError('Exact protected and repaired stages required')
    for stage in reused:
        for path in out.glob(stage+'*-*.json'):
            if path.is_file() and any(path.name.endswith('-'+suffix+'.json') for suffix in ('request', 'response', 'feedback')):
                if path.read_bytes() != evidence.bounded(source/path.name).read_bytes():
                    raise ValueError('Protected stage changed')
    with exercise_context(original['brief']):
        initial_logo = out/'initial-logo'
        if evidence.bounded(initial_logo/'artwork.svg').read_text() != logos[selection['selected']]:
            raise ValueError('Initial measured logo differs from original')
        if evidence.bounded(initial_logo/'monochrome/artwork.svg').read_text() != b.monochrome(logos[selection['selected']], plan['monochrome_ink']):
            raise ValueError('Initial monochrome differs from declared conversion')
        color = evidence.read(initial_logo/'render.json'); mono = evidence.read(initial_logo/'monochrome/render.json')
        verify_contributions(initial_logo, color)
        verify_contributions(initial_logo/'monochrome', mono)
        feedback = b.measured_feedback(color, 'brand_logo')
        if full_scene: feedback['issues'] += scoped.margin_findings(logos[selection['selected']], color, 'logo', plan['paper'])
        feedback['issues'] += monochrome_findings(color, mono)
        feedback.update(monochrome_shape_contributions=mono['shape_contributions'], color_shape_contributions=color['shape_contributions'])
        if feedback != evidence.read(out/'initial-logo-feedback.json'):
            raise ValueError('Initial logo diagnostic changed')
        local_raw, _ = evidence.chain(out, 'logo-'+selection['selected'], report)
        local_logo = b.compile_scene(local_raw, plan, kind='logo')
        if 'logo-'+selection['selected'] in repaired:
            proofs = [p for p in out.glob('logo-'+selection['selected']+'-layout-*')
                      if (p/'artwork.svg').is_file() and evidence.bounded(p/'artwork.svg').read_text() == local_logo]
            if len(proofs) != 1: raise ValueError('Exact accepted logo render proof required')
            accepted = proofs[0]
        else:
            accepted = initial_logo
        final_color = evidence.read(accepted/'render.json'); final_mono = evidence.read(accepted/'monochrome/render.json')
        if evidence.bounded(accepted/'monochrome/artwork.svg').read_text() != b.monochrome(local_logo, plan['monochrome_ink']):
            raise ValueError('Accepted monochrome proof differs from delivered scene')
        verify_contributions(accepted, final_color)
        verify_contributions(accepted/'monochrome', final_mono)
        if b.quality_issues(final_color, 'brand_logo') or monochrome_findings(final_color, final_mono):
            raise ValueError('Accepted logo still loses monochrome features or has layout defects')
        if full_scene:
            other = 'b' if selection['selected'] == 'a' else 'a'
            folder = out/'initial-alternate'
            if evidence.bounded(folder/'artwork.svg').read_text() != logos[other]:
                raise ValueError('Alternate source logo changed')
            if evidence.bounded(folder/'monochrome/artwork.svg').read_text() != b.monochrome(logos[other], plan['monochrome_ink']):
                raise ValueError('Alternate monochrome conversion changed')
            measured, mono = evidence.read(folder/'render.json'), evidence.read(folder/'monochrome/render.json')
            verify_contributions(folder, measured); verify_contributions(folder/'monochrome', mono)
            other_feedback = b.measured_feedback(measured, 'brand_logo')
            other_feedback['issues'] += scoped.margin_findings(logos[other], measured, 'logo', plan['paper'])
            other_feedback['issues'] += monochrome_findings(measured, mono)
            other_feedback.update(monochrome_shape_contributions=mono['shape_contributions'], color_shape_contributions=measured['shape_contributions'])
            if other_feedback != evidence.read(out/'initial-alternate-feedback.json'):
                raise ValueError('Alternate diagnostic changed')
            other_raw, _ = evidence.chain(out, 'logo-'+other, report)
            other_svg = b.compile_scene(other_raw, plan, kind='logo')
            if 'logo-'+other in repaired:
                proofs = [p for p in out.glob('logo-'+other+'-layout-*') if (p/'artwork.svg').is_file() and evidence.bounded(p/'artwork.svg').read_text() == other_svg]
                if len(proofs) != 1: raise ValueError('Exact accepted alternate logo proof required')
                folder = proofs[0]
            if evidence.bounded(folder/'monochrome/artwork.svg').read_text() != b.monochrome(other_svg, plan['monochrome_ink']):
                raise ValueError('Accepted alternate monochrome changed')
            measured, mono = evidence.read(folder/'render.json'), evidence.read(folder/'monochrome/render.json')
            verify_contributions(folder, measured); verify_contributions(folder/'monochrome', mono)
            if monochrome_findings(measured, mono): raise ValueError('Alternate monochrome still loses features')
            for key in ('a', 'b'):
                delivered = evidence.bounded(out/'delivery'/('logo-'+key+'.svg')).read_text()
                if scoped.margin_findings(delivered, evidence.read(out/('logo-'+key)/'render.json'), 'logo', plan['paper']):
                    raise ValueError('Delivered logo violates margins')
        if evidence.bounded(out/'initial-card/artwork.svg').read_text() != b.compile_scene(raw['card'], plan, kind='card', logo=local_logo):
            raise ValueError('Initial measured card differs from original scene with current logo')
        card_measurements = evidence.read(out/'initial-card/render.json')
        card_feedback = b.measured_feedback(card_measurements, 'brand_card')
        if full_scene:
            card_feedback['issues'] += scoped.margin_findings(evidence.bounded(out/'initial-card/artwork.svg').read_text(), card_measurements, 'card', plan['paper'])
        if record['schema'] in (CARD_CONTRACT, FULL_CONTRACT):
            card_feedback['issues'] += card_decoration_findings(
                evidence.bounded(out/'initial-card/artwork.svg').read_text(), card_measurements, plan['paper'])
            card_raw, _ = evidence.chain(out, 'card', report)
            final_card = b.compile_scene(card_raw, plan, kind='card', logo=local_logo)
            if evidence.bounded(out/'business-card/artwork.svg').read_text() != final_card:
                raise ValueError('Final measured card differs from local author')
            if card_decoration_findings(final_card, evidence.read(out/'business-card/render.json'), plan['paper']):
                raise ValueError('Card decoration still enters text bounds')
            if full_scene and scoped.margin_findings(final_card, evidence.read(out/'business-card/render.json'), 'card', plan['paper']):
                raise ValueError('Delivered card violates margins')
        if card_feedback != evidence.read(out/'initial-card-feedback.json'):
            raise ValueError('Initial card diagnostic changed')
        for stage in repaired:
            kind = 'card' if stage == 'card' else 'logo'
            diagnostic = 'alternate' if full_scene and kind == 'logo' and stage != 'logo-'+selection['selected'] else kind
            findings = evidence.read(out/('initial-'+diagnostic+'-feedback.json'))
            chosen = None
            if kind == 'card':
                chosen = local_logo
            rules = b.SCENE_RULES if record['schema'] == LEGACY_CONTRACT else REPAIR_RULES
            if full_scene: rules = scoped.rules(kind)
            schema = scoped.schema(kind, plan, original['brief']) if full_scene else b.scene_schema(kind, plan)
            if evidence.read(out/(stage+'-request.json')) != {'system': b.INSTRUCTION+'\n'+rules,
                    'user': payload(original['brief'], plan, raw[stage], findings, chosen), 'format': schema}:
                raise ValueError('Repair contains extra hints or changed source scene')
    calls = sum(evidence.chain(out, stage, report)[1]['requests'] for stage in repaired)
    if calls > (9 if full_scene else 6): raise ValueError('Additional repair budget exceeded')
    return {'schema': record['schema'], 'fresh_exam': False, 'source_report_sha256': record['source_report_sha256'],
            'additional_model_calls': calls, 'protected_stages': reused, 'repaired_stages': repaired}
