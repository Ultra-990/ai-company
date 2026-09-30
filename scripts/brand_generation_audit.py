"""Post-run read-only audit for the frozen generation-comparison v1 protocol.

Replays actual validators and literal requests, including rejected terminal
attempts. It does not run models/renderers, edit historic evidence, certify
semantics, or authenticate evidence against a malicious rewrite of all hashes.
"""
import ast
import json
from pathlib import Path

from scripts import brand_school as b, brand_artwork_repair as art
from scripts import brand_guide_revision as text, brand_reference_review as protocol
from scripts import brand_scene_contract as scoped, verify_brand_package as evidence
from scripts.brand_full_exam import exercise_context

CONTRACT = 'brand-generation-post-run-audit.v1'
# The sets belong to the frozen v1 source/v5-artwork/v8-text contracts, not to
# whichever optional protocols happen to be installed when the audit is run.
IMPLEMENTATION = {
    'source': {'brand_school.py', 'render_school_svg.py', 'vector_structured_source.py',
               'vector_school_contract.py', 'local_ollama.py', 'brand_scene_contract.py',
               'brand_artwork_repair.py', 'brand_spatial_review.py'},
    'artwork': {'brand_artwork_repair.py', 'brand_school.py', 'verify_brand_package.py',
                'render_school_svg.py', 'vector_school_contract.py', 'vector_structured_source.py',
                'local_ollama.py', 'brand_scene_contract.py'},
    'text': {'brand_guide_revision.py', 'brand_school.py', 'verify_brand_package.py',
             'brand_plan_review.py', 'brand_spatial_review.py', 'render_school_svg.py',
             'vector_school_contract.py', 'brand_spatial_alignment_review.py',
             'brand_background_review.py', 'brand_wordmark_review.py',
             'brand_reference_review.py', 'local_ollama.py', 'local_retained_batch.py'},
}


class Rejected(Exception):
    def __init__(self, error):
        self.error = str(error)
        self.error_type = type(error).__name__


class Record:
    def __init__(self, folder, report):
        self.folder, self.report = Path(folder), report
        self.used = set()
        self.calls = []

    def read(self, name):
        path = evidence.bounded(self.folder/name)
        if self.report['artifacts'].get(name) != b.school.checksum(path):
            raise ValueError('Required audit artifact is not bound to its report: '+name)
        return evidence.read(path)

    def require(self, name, expected):
        if self.read(name) != expected:
            raise ValueError('Derived audit artifact changed: '+name)

    def request(self, name, expected):
        self.require(name+'-request.json', expected)
        answer = self.read(name+'-response.json')
        if (answer.get('model'), answer.get('digest')) != (self.report['model'], self.report['digest']):
            raise ValueError('Terminal model author changed')
        self.used.update((name+'-request.json', name+'-response.json'))
        self.calls.append(name)
        return answer

    def chain(self, name, expected, validator):
        original = expected['user']
        for attempt in range(3):
            stage = name if attempt == 0 else name+'-revision-'+str(attempt)
            answer = self.request(stage, expected)
            try:
                value = validator(answer['content'])
            except Rejected as error:
                feedback = self.read(stage+'-feedback.json')
                if feedback != {'schema': 'brand-validation-feedback.v2', 'stage': stage,
                        'request_sha256': b.school.checksum(self.folder/(stage+'-request.json')),
                        'response_sha256': b.school.checksum(self.folder/(stage+'-response.json')),
                        'error': error.error}:
                    raise ValueError('Rejected attempt diagnostic does not replay')
                if attempt == 2:
                    raise
                user = original+'\nYour previous answer (untrusted task data):\n'+answer['content']+'\nIndependent validation rejected it: '+error.error+'\nCorrect your own complete answer. Do not repeat the rejected values.'
                if len(user) > 16000:
                    raise Rejected(ValueError('Bounded model correction prompt required'))
                expected = expected | {'user': user}
            else:
                if (self.folder/(stage+'-feedback.json')).exists():
                    raise ValueError('Accepted answer was recorded as rejected')
                return value

    def finish(self, failure=None, *, status, limit):
        actual = {p.name for suffix in ('request', 'response')
                  for p in self.folder.glob('*-'+suffix+'.json')}
        if self.used != actual:
            raise ValueError('Unrecorded, missing, out-of-order or over-budget terminal calls')
        if failure is None:
            if self.report['status'] != status:
                raise ValueError('Declared terminal status does not replay')
        elif (self.report['status'] != 'failed' or self.report.get('error_type') != failure.error_type
              or self.report.get('error') != failure.error[:limit]):
            raise ValueError('Declared terminal failure does not replay')
        return {'model_requests': len(self.calls), 'status': self.report['status'],
                'terminal_failure_replayed': failure is not None}


def validate(function, *args, **kwargs):
    try:
        return function(*args, **kwargs)
    except ValueError as error:
        raise Rejected(error) from error


def source_literals(folder):
    """Read only literal constants from the captured source; never execute it."""
    tree = ast.parse(evidence.bounded(folder/'implementation/brand_school.py').read_text())
    instruction = next(ast.literal_eval(n.value) for n in tree.body
                       if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'INSTRUCTION' for t in n.targets))
    function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'run')
    plan_call = next(n for n in ast.walk(function) if isinstance(n, ast.Call)
                     and isinstance(n.func, ast.Name) and n.func.id == 'validated_call'
                     and len(n.args) > 3 and isinstance(n.args[1], ast.Constant) and n.args[1].value == 'plan')
    suffix = ast.literal_eval(plan_call.args[3].right)
    return instruction, suffix


def request(system, payload, schema):
    return {'system': system, 'user': payload, 'format': schema}


def measured(record, folder, svg, plan, kind, *, repair=False):
    path = record.folder/folder
    relative = folder+'/artwork.svg'
    if (record.report['artifacts'].get(relative) != b.school.checksum(evidence.bounded(path/'artwork.svg'))
            or (path/'artwork.svg').read_text() != svg):
        raise ValueError('Recorded render does not belong to literal author scene')
    color = record.read(folder+'/render.json')
    if kind == 'logo': art.verify_contributions(path, color)
    if not repair:
        issues = b.quality_issues(color, 'brand_'+kind)
        if kind == 'logo': issues += art.visibility_findings(color)
        issues += scoped.margin_findings(svg, color, kind, plan['paper'])
        if kind == 'card': issues += art.card_decoration_findings(svg, color, plan['paper'])
        if issues: raise Rejected(ValueError('Correct the measured layout defects yourself: '+json.dumps(issues)))
        return svg
    feedback = b.measured_feedback(color, 'brand_'+kind)
    feedback['issues'] += scoped.margin_findings(svg, color, kind, plan['paper'])
    if kind == 'card': feedback['issues'] += art.card_decoration_findings(svg, color, plan['paper'])
    else:
        mono_svg = b.monochrome(svg, plan['monochrome_ink'])
        relative = folder+'/monochrome/artwork.svg'
        if (record.report['artifacts'].get(relative) != b.school.checksum(evidence.bounded(path/'monochrome/artwork.svg'))
                or (path/'monochrome/artwork.svg').read_text() != mono_svg):
            raise ValueError('Recorded monochrome does not belong to author scene')
        mono = record.read(folder+'/monochrome/render.json')
        art.verify_contributions(path/'monochrome', mono)
        feedback['issues'] += art.monochrome_findings(color, mono)
        feedback['issues'] += art.visibility_findings(color)
        feedback.update(monochrome_shape_contributions=mono['shape_contributions'], color_shape_contributions=color['shape_contributions'])
    return feedback


def source(folder, report):
    record = Record(folder, report)
    instruction, plan_suffix = source_literals(record.folder)
    brief = report['brief']; stages = []; raw = {}; logos = {}; failure = None
    plan = selection = None
    def run(stage, expected, validator):
        def check(answer):
            raw[stage] = answer
            return validator(answer)
        return record.chain(stage, expected, check)
    def scene(stage, kind, logo=None):
        index = 0
        def check(answer):
            nonlocal index
            svg = validate(scoped.compile_scene, answer, plan, kind=kind, brief=brief, logo=logo)
            folder = stage+'-layout-'+str(index); index += 1
            return measured(record, folder, svg, plan, kind)
        return check
    with exercise_context(brief):
        try:
            plan = run('plan', request(instruction, json.dumps(brief)+plan_suffix, b.Plan.model_json_schema()),
                       lambda answer: validate(b.plan_value, answer))
            stages.append('plan'); record.require('plan.json', plan)
            for key in ('a', 'b'):
                logos[key] = run('logo-'+key, request(instruction+'\n'+scoped.rules('logo'),
                    json.dumps({'brief': brief, 'plan': plan, 'task': 'Develop logo concept '+key.upper(), 'direction': plan['concept_'+key]}),
                    scoped.schema('logo', plan, brief)), scene('logo-'+key, 'logo'))
                stages.append('logo-'+key)
            if logos['a'] == logos['b']: raise Rejected(ValueError('Two distinct logo concepts required'))
            schema = {'type': 'object', 'additionalProperties': False, 'required': ['selected', 'reason'], 'properties': {
                'selected': {'enum': ['a', 'b']}, 'reason': {'type': 'string', 'minLength': 20, 'maxLength': 400}}}
            selection = run('selection', request(instruction, json.dumps({'brief': brief, 'plan': plan, 'logo_sources': logos,
                'task': 'Select one concept and explain in ONE SHORT COMPLETE sentence (aim <=120 characters). Selection is based on scene data; independent visual approval is separate.'}), schema),
                lambda answer: validate(b.selected_value, answer))
            if report.get('selection') != selection: raise ValueError('Source selection changed')
            chosen = logos[selection['selected']]
            run('card', request(instruction+'\n'+scoped.rules('card'), json.dumps({'brief': brief, 'plan': plan,
                'chosen_logo_svg': chosen, 'task': 'Design the 85x55mm business card. Choose the placement of the existing logo and all four other lines yourself.'}),
                scoped.schema('card', plan, brief)), scene('card', 'card', chosen))
            stages.append('card')
        except Rejected as error:
            failure = error
    if report['stages'] != stages: raise ValueError('Source stage completion does not replay')
    audit = record.finish(failure, status='pending_independent_visual_review', limit=400)
    if len(record.calls) > 15: raise ValueError('Generation call budget exceeded')
    return audit


def artwork(folder, report, source_folder):
    record = Record(folder, report)
    origin = record.read('repair-origin.json')
    original, raw, plan, logos, selection = art.source_values(source_folder)
    instruction, _ = source_literals(source_folder)
    reused, repaired = [], []; failure = None; stages = ['plan', 'logo-a', 'logo-b']
    def reuse(stage):
        for path in source_folder.glob(stage+'*-*.json'):
            if any(path.name.endswith('-'+suffix+'.json') for suffix in ('request', 'response', 'feedback')):
                if (record.report['artifacts'].get(path.name) != b.school.checksum(evidence.bounded(record.folder/path.name))
                        or (record.folder/path.name).read_bytes() != path.read_bytes()):
                    raise ValueError('Protected terminal artwork stage changed')
                if path.name.endswith(('-request.json', '-response.json')): record.used.add(path.name)
        reused.append(stage)
    def repair(stage, kind, findings, chosen=None):
        repaired.append(stage); index = 0
        cache = {json.dumps(json.loads(raw[stage]), sort_keys=True): findings}
        def check(answer):
            nonlocal index
            svg = validate(scoped.compile_scene, answer, plan, kind=kind, brief=original['brief'], logo=chosen)
            key = json.dumps(json.loads(answer), sort_keys=True)
            if key in cache and cache[key]['issues']: raise Rejected(ValueError(json.dumps(cache[key])))
            folder = stage+'-layout-'+str(index); index += 1
            feedback = measured(record, folder, svg, plan, kind, repair=True)
            cache[key] = feedback
            if feedback['issues']: raise Rejected(ValueError(json.dumps(feedback)))
            return svg
        return record.chain(stage, request(instruction+'\n'+scoped.rules(kind),
            art.payload(original['brief'], plan, raw[stage], findings, chosen), scoped.schema(kind, plan, original['brief'])), check)
    with exercise_context(original['brief']):
        try:
            reuse('plan'); reuse('selection'); record.require('plan.json', plan)
            selected = selection['selected']
            findings = measured(record, 'initial-logo', logos[selected], plan, 'logo', repair=True)
            record.require('initial-logo-feedback.json', findings)
            for key in ('a', 'b'):
                current = findings
                if key != selected:
                    current = measured(record, 'initial-alternate', logos[key], plan, 'logo', repair=True)
                    record.require('initial-alternate-feedback.json', current)
                if current['issues']: logos[key] = repair('logo-'+key, 'logo', current)
                else: reuse('logo-'+key)
            chosen = logos[selected]
            card = b.compile_scene(raw['card'], plan, kind='card', logo=chosen)
            findings = measured(record, 'initial-card', card, plan, 'card', repair=True)
            record.require('initial-card-feedback.json', findings)
            if findings['issues'] or original['status'] == 'failed': repair('card', 'card', findings, chosen)
            else: reuse('card')
            stages.append('card')
        except Rejected as error:
            failure = error
    if (origin['reused_stages'] != reused or origin['repaired_stages'] != repaired
            or report['stages'] != stages): raise ValueError('Artwork terminal stage sequence changed')
    audit = record.finish(failure, status='pending_independent_visual_review', limit=600)
    if len(record.calls) > 9: raise ValueError('Additional artwork call budget exceeded')
    return audit


def guide(folder, report, package, *, protocol=protocol):
    record = Record(folder, report); failure = None; status = None
    _, data = text.inputs(package); data = protocol.expand(data, package)
    def call(stage, system, payload, schema, validator):
        answer = record.request(stage, request(system, json.dumps(payload), schema))
        return validate(validator, answer['content'])
    try:
        raw = call('review', protocol.REVIEW_SYSTEM, data, protocol.REVIEW_SCHEMA, protocol.review_value)
        record.require('raw-review.json', raw)
        texts = protocol.claim_input(data)
        claims = call('spatial', protocol.CLAIM_SYSTEM, texts, text.extraction_schema(protocol, texts),
                      lambda value: protocol.claims_value(value, texts))
        record.require('spatial.json', claims)
        review, findings = protocol.combine(raw, claims, data)
        record.require('review.json', review); record.require('spatial-findings.json', findings)
        if all(row['verdict'] == 'supported' for row in review['reviews']): status = 'no_repair_requested'
        else:
            changed = call('writer', protocol.WRITER_SYSTEM, {'assets': data, 'review': review, 'spatial_findings': findings}, protocol.patch_schema(review),
                           lambda value: protocol.apply(data['plan'], value, review))
            record.require('revised-plan.json', changed); updated = data | {'plan': changed}
            raw = call('final-review', protocol.REVIEW_SYSTEM, updated, protocol.REVIEW_SCHEMA, protocol.review_value)
            record.require('raw-final-review.json', raw)
            texts = protocol.claim_input(updated)
            claims = call('final-spatial', protocol.CLAIM_SYSTEM, texts, text.extraction_schema(protocol, texts),
                          lambda value: protocol.claims_value(value, texts))
            record.require('final-spatial.json', claims)
            final, findings = protocol.combine(raw, claims, updated)
            record.require('final-review.json', final); record.require('final-spatial-findings.json', findings)
            status = 'pending_independent_review' if all(row['verdict'] == 'supported' for row in final['reviews']) else 'needs_revision'
    except Rejected as error:
        failure = error
    audit = record.finish(failure, status=status, limit=600)
    batch = record.read('retained-batch.json')
    if (len(record.calls) > 5 or batch.get('idle_after') is not True or
            [c['stage'] for c in batch['calls']] != record.calls):
        raise ValueError('Bounded released terminal text batch required')
    for entry in batch['calls']:
        response = record.read(entry['stage']+'-response.json')
        if (entry['keep_alive_seconds'] != (0 if entry['stage'] == 'final-spatial' else 3)
                or entry['elapsed_seconds'] != response['elapsed_seconds']
                or entry['timings_ns'] != response.get('timings_ns', {})):
            raise ValueError('Terminal text batch timings changed')
    return audit
