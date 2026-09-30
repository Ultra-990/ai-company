"""Frozen fresh jobs: shared source, measured artwork repair, factual text, ZIP.

The two arms differ only in the artwork repair sampling/thinking profile;
their token, context, time and call budgets match. Neither arm self-approves.
"""
from copy import deepcopy
import json
from pathlib import Path
import shutil
import tempfile
import time

from scripts import brand_school as b, brand_artwork_repair as artwork
from scripts import brand_guide_revision as text_repair
from scripts import brand_spatial_alignment_review as text_protocol
from scripts import verify_brand_package as evidence

CONTRACT = 'brand-complete-delivery-exam.v2'
STRICT_CONTRACT = 'brand-complete-delivery-exam.v3'
STRICT_CASES = (
    {'id': 'willow-hearth', 'name': 'Willow Hearth',
     'concept': 'Fictional neighborhood supper room serving baked root vegetables, grains and warm bread. Welcoming, calm and rustic with a restrained branch or hearth motif; no luxury crests or fork/knife clip art.',
     'audience': 'Neighbors and small groups sharing an informal evening supper.'},
    {'id': 'stone-market', 'name': 'Stone Market',
     'concept': 'Fictional daytime market restaurant serving seasonal vegetable bowls and handmade dumplings. Practical, lively and approachable with a simple market stall or bowl motif; no luxury crests or fork/knife clip art.',
     'audience': 'Market shoppers and nearby workers meeting for a casual lunch.'},
    {'id': 'tide-garden', 'name': 'Tide Garden',
     'concept': 'Fictional seaside restaurant serving vegetable plates, seaweed salads and local fish. Light, relaxed and hospitable with a simple leaf-and-water motif; no luxury crests or fork/knife clip art.',
     'audience': 'Local families and visitors gathering for an unhurried daytime meal.'},
)
CASES = (
    {'id': 'orchard-counter', 'name': 'Orchard Counter',
     'concept': 'Fictional breakfast and lunch counter offering fruit-led breakfasts, warm porridge and seasonal vegetable sandwiches. Bright, relaxed and practical, with orchard imagery; no luxury crests or fork/knife clip art.',
     'audience': 'Commuters and neighbors sharing a quick breakfast or informal daytime meal.'},
    {'id': 'saffron-courtyard', 'name': 'Saffron Courtyard',
     'concept': 'Fictional casual courtyard restaurant offering fragrant rice, roasted vegetables and breads for sharing. Warm, social and inviting, with a restrained spice or courtyard motif; no luxury crests or fork/knife clip art.',
     'audience': 'Friends and families meeting for a shared evening meal.'},
    {'id': 'north-pier', 'name': 'North Pier',
     'concept': 'Fictional harbor lunch room serving fish soup, rye bread and seasonal salads. Clear, modest and welcoming, with a simple pier or water motif; no luxury crests or fork/knife clip art.',
     'audience': 'Local workers and visitors stopping for a relaxed harbor lunch.'},
)
ARMS = {'baseline': False, 'deliberate': True}
GENERATION = {'num_ctx': 8192, 'num_predict': 4096, 'num_thread': 4, 'timeout_seconds': 180}
ARTWORK = {'num_ctx': 16384, 'num_predict': 8192, 'num_thread': 4, 'timeout_seconds': 180}
TEXT = {'num_ctx': 8192, 'num_predict': 1800, 'num_thread': 4, 'timeout_seconds': 90}
CODE = ('brand_delivery_exam.py', 'brand_school.py', 'brand_full_exam.py', 'brand_artwork_repair.py',
        'brand_guide_revision.py', 'brand_plan_review.py', 'brand_spatial_review.py',
        'brand_spatial_alignment_review.py', 'verify_brand_package.py', 'render_school_svg.py',
        'vector_structured_source.py', 'vector_school_contract.py', 'local_retained_batch.py',
        'compare_local_models.py', 'vector_school.py', 'local_ollama.py')


def definition(case, *, strict=False):
    if case not in (STRICT_CASES if strict else CASES): raise ValueError('Frozen complete-delivery case required')
    brief = deepcopy(b.DEFAULT_BRIEF); domain = case['id'].replace('-', '')+'.example'
    brief.update(restaurant_name=case['name'], family=('brand-delivery-v3-' if strict else 'brand-delivery-v2-')+case['id'], split='test',
        concept=case['concept'], audience=case['audience'], qualification_exam=STRICT_CONTRACT if strict else CONTRACT,
        contacts=['Reservations by email', 'hello@'+domain, domain])
    return brief


def protocol_for(strict):
    if strict:
        from scripts import brand_background_review
        return brand_background_review
    return text_protocol


def manifest(config, *, strict=False):
    return {'schema': STRICT_CONTRACT if strict else CONTRACT,
        'briefs': [definition(c, strict=strict) for c in (STRICT_CASES if strict else CASES)],
        'model': config['model'], 'digest': config['digest'], 'shared_original_per_pair': True,
        'generation_budget': GENERATION, 'artwork_budget': ARTWORK, 'text_budget': TEXT,
        'max_generation_calls': 15, 'max_additional_artwork_calls': 6, 'max_text_calls': 5,
        'artwork_contract': artwork.CARD_CONTRACT if strict else artwork.CONTRACT,
        'text_contract': protocol_for(strict).CONTRACT,
        'profiles': {'baseline': 'bounded-default.v1', 'deliberate': 'qwen-deliberate-trial.v1'},
        'warm_text': True, 'manual_hints_allowed': False, 'training_export_allowed': False}


def check_no_text_repair(folder, source, *, strict=False, protocol=None):
    """Replay both original reviews, including geometry veto and warm release."""
    text_protocol = protocol or protocol_for(strict)
    read = evidence.read; report = read(folder/'report.json')
    original, data = text_repair.inputs(source); data = text_protocol.expand(data, source)
    expected = [('review', text_protocol.REVIEW_SYSTEM, data, text_protocol.REVIEW_SCHEMA),
                ('spatial', text_protocol.CLAIM_SYSTEM, text_protocol.claim_input(data), text_protocol.CLAIM_SCHEMA)]
    values = []
    if {p.name for p in folder.glob('*-request.json')} != {'review-request.json', 'spatial-request.json'}:
        raise ValueError('Exactly two reviews required for unchanged text')
    for stage, system, payload, schema in expected:
        if read(folder/(stage+'-request.json')) != {'system': system, 'user': json.dumps(payload), 'format': schema}:
            raise ValueError('Original text review inputs changed')
        response = read(folder/(stage+'-response.json'))
        if (response['model'], response['digest']) != (original['model'], original['digest']):
            raise ValueError('Text reviewer changed')
        values.append(response['content'])
    raw = text_protocol.review_value(values[0])
    claims = text_protocol.claims_value(values[1], text_protocol.claim_input(data))
    reviewed, findings = text_protocol.combine(raw, claims, data)
    if (raw != read(folder/'raw-review.json') or claims != read(folder/'spatial.json')
            or reviewed != read(folder/'review.json') or findings != read(folder/'spatial-findings.json')
            or findings or any(row['verdict'] != 'supported' for row in reviewed['reviews'])):
        raise ValueError('No-repair result still has unsupported text')
    batch = read(folder/'retained-batch.json')
    if batch.get('idle_after') is not True or [c['stage'] for c in batch['calls']] != ['review', 'spatial']:
        raise ValueError('Short text batch not released')
    for c in batch['calls']:
        response = read(folder/(c['stage']+'-response.json'))
        if (c['keep_alive_seconds'] != 3 or c['elapsed_seconds'] != response['elapsed_seconds']
                or c['timings_ns'] != response.get('timings_ns', {})):
            raise ValueError('No-repair batch timing changed')


def run(*, strict=False):
    from scripts.brand_full_exam import exercise_context
    resources = b.school.check_idle(); config = b.configuration()
    out = Path(tempfile.mkdtemp(prefix='delivery-exam-', dir=b.ROOT))
    frozen = manifest(config, strict=strict); b.school.save(out/'exam.json', frozen)
    code = out/'implementation'; code.mkdir()
    for name in CODE + (('brand_background_review.py',) if strict else ()):
        source = Path(__file__).parent/name if name != 'local_ollama.py' else Path(__file__).parents[1]/'app/services/local_ollama.py'
        shutil.copyfile(source, code/name)
    report = {'schema': frozen['schema'], 'status': 'running', 'resources_before': resources,
        'exam_sha256': b.school.checksum(out/'exam.json'), 'cases': [],
        'autonomy_qualified': False, 'training_exported': False, 'production_changed': False,
        'independent_review_required': True}
    started = time.monotonic()
    def save():
        report['elapsed_seconds'] = round(time.monotonic()-started, 3)
        report['artifacts'] = {str(p.relative_to(out)): b.school.checksum(p) for p in out.rglob('*') if p.is_file() and p.name != 'report.json'}
        b.school.save(out/'report.json', report)
    save(); print(json.dumps({'output': str(out)}), flush=True)
    try:
        for index, brief in enumerate(frozen['briefs']):
            with exercise_context(brief): source, generated = b.run()
            entry = {'family': brief['family'], 'source': str(source),
                'source_report_sha256': b.school.checksum(source/'report.json'), 'arms': {}}
            report['cases'].append(entry); save()
            try: artwork.source_values(source)
            except ValueError:
                entry['source_repairable'] = False; save(); continue
            entry['source_repairable'] = True
            for arm in (('baseline', 'deliberate') if index % 2 == 0 else ('deliberate', 'baseline')):
                package, repaired = artwork.run(source, deliberate=ARMS[arm], matched_budget=True, **({'strict_card': True} if strict else {}))
                outcome = {'artwork': str(package), 'artwork_report_sha256': b.school.checksum(package/'report.json'),
                           'text': None, 'candidate': None, 'status': repaired['status']}
                entry['arms'][arm] = outcome; save()
                if repaired['status'] == 'pending_independent_visual_review':
                    b.school.save(package/'verification.json', evidence.verify(package))
                    text_folder, text_result = text_repair.run(package, spatial='background' if strict else 'alignment', warm=True)
                    outcome.update(text=str(text_folder), text_report_sha256=b.school.checksum(text_folder/'report.json'), status=text_result['status'])
                    if text_result['status'] == 'pending_independent_review':
                        b.school.save(text_folder/'verification.json', text_repair.verify(text_folder))
                        outcome['candidate'] = str(text_folder)
                    elif text_result['status'] == 'no_repair_requested':
                        check_no_text_repair(text_folder, package, **({'strict': True} if strict else {})); outcome['candidate'] = str(package)
                save(); print(json.dumps({'case': brief['restaurant_name'], 'arm': arm, **outcome}), flush=True)
        report.update(status='completed', technical_scores={arm: sum(bool(c['arms'].get(arm, {}).get('candidate')) for c in report['cases']) for arm in ARMS})
    except Exception as exc:
        report.update(status='failed', error_type=type(exc).__name__, error=str(exc)[:600])
    finally: save()
    print(json.dumps({'report': str(out/'report.json'), 'status': report['status'], 'scores': report.get('technical_scores')}), flush=True)
    return out, report


def verify(out, *, use_recorded_render=False):
    out = Path(out); read = evidence.read; checksum = b.school.checksum
    report, frozen = read(out/'report.json'), read(out/'exam.json')
    strict = report.get('schema') == STRICT_CONTRACT
    if (report.get('schema') not in (CONTRACT, STRICT_CONTRACT) or report.get('status') != 'completed' or frozen != manifest(frozen, strict=strict)
            or checksum(out/'exam.json') != report['exam_sha256']
            or any(report.get(k) is not False for k in ('autonomy_qualified', 'training_exported', 'production_changed'))
            or [c['family'] for c in report['cases']] != [v['family'] for v in frozen['briefs']]):
        raise ValueError('Complete frozen delivery exam required')
    seen = set()
    def bound(folder, value):
        for name, digest in value['artifacts'].items():
            path = evidence.bounded(folder/name)
            if not path.resolve().is_relative_to(folder.resolve()) or checksum(path) != digest:
                raise ValueError('Delivery experiment artifact changed')
    def stage(folder, digest, budget):
        if folder.resolve() in seen or checksum(folder/'report.json') != digest: raise ValueError('Unique unchanged stage required')
        seen.add(folder.resolve()); value = read(folder/'report.json'); bound(folder, value)
        if ((value['model'], value['digest']) != (frozen['model'], frozen['digest'])
                or any(value['config'][k] != v for k,v in budget.items())):
            raise ValueError('Pinned model and equal stage budgets required')
        for p in (folder/'implementation').iterdir():
            if not (out/'implementation'/p.name).is_file() or p.read_bytes() != evidence.bounded(out/'implementation'/p.name).read_bytes():
                raise ValueError('Implementation changed during frozen exam')
        return value
    bound(out, report); scores = dict.fromkeys(ARMS, 0)
    for case, brief in zip(report['cases'], frozen['briefs']):
        source = Path(case['source']); original = stage(source, case['source_report_sha256'], GENERATION)
        if (original['brief'] != brief or 'repair_contract' in original
                or original['status'] not in ('failed', 'needs_revision', 'pending_independent_visual_review')
                or original['config'].get('think', False) is not False
                or original['config'].get('sampling_profile', 'bounded-default.v1') != 'bounded-default.v1'
                or not 1 <= len(list(source.glob('*-request.json'))) <= 15):
            raise ValueError('Fresh bounded shared source required')
        try: artwork.source_values(source); eligible = True
        except ValueError: eligible = False
        if case['source_repairable'] is not eligible: raise ValueError('Source repairability changed')
        if not eligible:
            if case['arms']: raise ValueError('Unsupported source cannot enter repairs')
            continue
        if set(case['arms']) != set(ARMS): raise ValueError('Both paired repair arms required')
        for arm, outcome in case['arms'].items():
            package = Path(outcome['artwork']); value = stage(package, outcome['artwork_report_sha256'], ARTWORK)
            origin = read(package/'repair-origin.json')
            if (value['brief'] != brief or value.get('repair_contract') != frozen['artwork_contract']
                    or Path(origin['source']).resolve() != source.resolve() or origin['source_report_sha256'] != case['source_report_sha256']
                    or origin['max_additional_model_calls'] != 6 or origin['fresh_exam'] is not False
                    or value['config'].get('think') is not ARMS[arm] or value['config'].get('sampling_profile') != frozen['profiles'][arm]):
                raise ValueError('Matched artwork arm or shared source changed')
            if len(origin['repaired_stages']) > 2 or sum(len(list(package.glob(s+'*-request.json'))) for s in origin['repaired_stages']) > 6:
                raise ValueError('Artwork call budget exceeded')
            candidate = None
            if value['status'] == 'pending_independent_visual_review':
                evidence.verify(package)
                folder = Path(outcome['text']); result = stage(folder, outcome['text_report_sha256'], TEXT)
                if (Path(result['package']).resolve() != package.resolve() or result['source_report_sha256'] != outcome['artwork_report_sha256']
                        or result.get('review_contract') != frozen['text_contract'] or result.get('max_model_calls') != 5
                        or result['config'].get('think') is not False or result['config'].get('sampling_profile') != 'bounded-default.v1'
                        or result.get('retained_batch_contract') != 'local-retained-batch.v1'
                        or not 1 <= len(list(folder.glob('*-request.json'))) <= 5 or result['status'] != outcome['status']):
                    raise ValueError('Bounded unchanged text phase required')
                if result['status'] == 'pending_independent_review':
                    text_repair.verify(folder, use_recorded_render=use_recorded_render); candidate = str(folder)
                elif result['status'] == 'no_repair_requested':
                    check_no_text_repair(folder, package, **({'strict': True} if strict else {})); candidate = str(package)
                elif result['status'] not in ('failed', 'needs_revision'): raise ValueError('Terminal text result required')
            elif value['status'] not in ('failed', 'needs_revision') or outcome['text'] is not None or outcome['status'] != value['status']:
                raise ValueError('Terminal artwork result required')
            if candidate != outcome['candidate']: raise ValueError('Final candidate substituted')
            scores[arm] += bool(candidate)
    if scores != report['technical_scores']: raise ValueError('Delivery score changed')
    return {'schema': frozen['schema'], 'report_sha256': checksum(out/'report.json'), 'technical_scores': scores,
            'shared_original_per_pair': True, 'equal_artwork_budgets': True,
            'independent_review_required': True, 'autonomy_qualified': False,
            'render_evidence_mode': 'prior_recorded_renders_rechecked_without_browser' if use_recorded_render else 'fresh_renders'}


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify', type=Path, required=True)
    parser.add_argument('--use-recorded-render', action='store_true')
    args = parser.parse_args()
    print(json.dumps(verify(args.verify, use_recorded_render=args.use_recorded_render), indent=2))
