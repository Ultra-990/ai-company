"""Bounded v5 atomic audit, author repair, re-audit, and optional final repair."""
import argparse
import json
from pathlib import Path
import sys
import types

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts import technical_review_atomic_claim_audit as atomic
from scripts import technical_review_final_correction as engine

v3, v2, v1 = atomic.v3, atomic.v2, atomic.v1
CONTRACT = 'technical-review-atomic-self-correction.v5'
MAX_CALLS = 4
CLAIMS = ('atomic_diagnosis', 'atomic_recommendation', 'severity', 'source_grounding')
WRITER = engine.WRITER + '''
ATOMIC PROTECTION: claim_audit is keyed by literal ordered span IDs. Preserve
every supported span exactly. A fully supported field must remain byte-identical.
For a mixed field, keep the same ordered segment slots and change only rejected
slots. Do not insert new assertions. A final-writer follows the same rule using
the final atomic audit. Every output remains unaccepted pending independent review.'''


def audit_dump(audit):
    return {claim: row.model_dump() for claim, row in audit.items()}


def supported(audit):
    return all(row.verdict == 'supported' for row in audit.values())


def writer_audit(audit):
    return {claim: ({'verdict': row.verdict} if row.verdict == 'supported' else row.model_dump())
            for claim, row in audit.items()}


def messages(stage, article, sources, review, audit=None):
    payload = {'article_lines': [{'line': number, 'text': text}
                                 for number, text in enumerate(article.splitlines(), 1)],
               'source_cards': sources}
    if stage in ('writer', 'final-writer'):
        payload.update(previous_review=review.model_dump(), claim_audit=writer_audit(audit),
                       revision_stage=stage)
        return {'system': WRITER, 'user': json.dumps(payload, ensure_ascii=False),
                'format': v1.lab.Review.model_json_schema()}
    payload['atomic_review_claims'] = atomic.atomic_units(review)
    return {'system': atomic.INSTRUCTION, 'user': json.dumps(payload, ensure_ascii=False),
            'format': atomic.audit_schema(review)}


def snapshots():
    return [Path(__file__), Path(atomic.__file__), Path(engine.__file__), Path(v3.__file__),
            Path(v2.__file__), Path(v1.__file__), Path(v1.base.__file__), Path(v1.lab.__file__),
            Path(__file__).parent/'local_retained_batch.py', Path(__file__).parent/'compare_local_models.py',
            Path(__file__).parents[1]/'app/services/local_ollama.py']


class AtomicProtocol:
    audit_value = staticmethod(atomic.audit_value)
    audit_dump = staticmethod(audit_dump)
    supported = staticmethod(supported)
    revision_value = staticmethod(atomic.revision_value)


def _bound(function):
    namespace = dict(function.__globals__)
    namespace.update(CONTRACT=CONTRACT, MAX_CALLS=MAX_CALLS, CLAIMS=CLAIMS,
                     messages=messages, snapshots=snapshots, v3=AtomicProtocol)
    result = types.FunctionType(function.__code__, namespace, function.__name__,
                                function.__defaults__, function.__closure__)
    result.__kwdefaults__ = dict(function.__kwdefaults__ or {})
    result.__annotations__ = dict(function.__annotations__)
    result.__doc__ = function.__doc__; result.__module__ = __name__; result.__qualname__ = function.__name__
    return result


def validate_attempted_transition(stage, next_stage, audit=None, before=None, after=None):
    if stage == 'audit' and next_stage == 'writer' and supported(audit):
        raise ValueError('Impossible writer attempt after a fully supported audit')
    if stage == 'writer' and next_stage == 'final-audit' and before.model_dump() == after.model_dump():
        raise ValueError('Impossible final-audit attempt after an unchanged writer review')
    if stage == 'final-audit' and next_stage == 'final-writer' and supported(audit):
        raise ValueError('Impossible final-writer attempt after a fully supported final audit')


_engine_run = _bound(engine.run)
_engine_verify = _bound(engine.verify)


def run(source, *, root=v3.ROOT):
    out, report = _engine_run(source, root=root)
    if report['status'] == 'failed' and report.get('calls'):
        stage = report['calls'][-1]; request = out/(stage+'-request.json'); response = out/(stage+'-response.json')
        if request.exists() and not response.exists():
            failure = {'schema': 'technical-review-request-only-failure.v1', 'stage': stage,
                       'request_sha256': v1.base.digest(request), 'response_present': False,
                       'error_type': report.get('error_type'), 'error': report.get('error')}
            v1.lab.save(out/'transport-failure.json', failure)
            report['artifacts'] = {str(path.relative_to(out)): v1.base.digest(path) for path in out.rglob('*')
                                   if path.is_file() and path.name != 'report.json'}
            v1.lab.save(out/'report.json', report)
    return out, report


def verify(out):
    out = Path(out); marker = out/'transport-failure.json'
    if not marker.exists(): return _engine_verify(out)
    report, manifest, failure = (v1.base.load(out/name) for name in
                                 ('report.json', 'manifest.json', 'transport-failure.json'))
    if (failure != {'schema': 'technical-review-request-only-failure.v1',
                    'stage': failure.get('stage'), 'request_sha256': failure.get('request_sha256'),
                    'response_present': False, 'error_type': failure.get('error_type'), 'error': failure.get('error')} or
            report.get('schema') != CONTRACT or manifest.get('schema') != CONTRACT or report.get('status') != 'failed' or
            report.get('manifest_sha256') != v1.base.digest(out/'manifest.json') or
            manifest.get('max_model_calls') != MAX_CALLS or manifest.get('claim_kinds') != list(CLAIMS) or
            manifest.get('audit_shape') != 'required-key-map' or
            manifest.get('final_correction') != 'single-author-call-after-objecting-final-audit' or
            any(manifest.get(key) is not False for key in ('fresh_exam', 'training_exported', 'weights_trained')) or
            any(report.get(key) is not False for key in ('accepted', 'production_ready', 'autonomy_qualified')) or
            report.get('semantic_decision') != 'pending_independent_review' or
            report.get('candidate') is not None or not report.get('calls') or failure['stage'] != report['calls'][-1] or
            (failure['error_type'], failure['error']) != (report.get('error_type'), report.get('error'))):
        raise ValueError('Changed request-only transport failure')
    stages = ['audit', 'writer', 'final-audit', 'final-writer']
    if report['calls'] != stages[:len(report['calls'])]: raise ValueError('Changed attempted call order')
    request = out/(failure['stage']+'-request.json')
    if not request.exists() or (out/(failure['stage']+'-response.json')).exists() or v1.base.digest(request) != failure['request_sha256']:
        raise ValueError('Request-only transport evidence changed')
    if set(manifest['implementation']) != {path.name for path in snapshots()}:
        raise ValueError('Incomplete implementation snapshot')
    for name, digest in manifest['implementation'].items():
        if v1.base.digest(out/'implementation'/name) != digest: raise ValueError('Changed implementation snapshot')
    source = Path(manifest['source'])
    if (v1.base.digest(source/'report.json') != manifest['source_report_sha256'] or
            v1.base.digest(source/'manifest.json') != manifest['source_manifest_sha256']):
        raise ValueError('Source review changed')
    _, review, article, sources = v1.origin(source)
    config = manifest['configuration']; parent = v1.base.load(source/'manifest.json')['configuration']
    if (any(config.get(key) != value for key, value in engine.BUDGET.items()) or
            (config.get('model'), config.get('digest')) != (parent.get('model'), parent.get('digest'))):
        raise ValueError('Changed pinned request-only configuration')
    current_audit = None
    for number, stage in enumerate(report['calls']):
        next_stage = report['calls'][number+1] if number+1 < len(report['calls']) else None
        expected_request = messages(stage, article, sources, review, current_audit)
        if v1.base.load(out/(stage+'-request.json')) != expected_request:
            raise ValueError('Changed completed-prefix or failed-stage request')
        if number == len(report['calls'])-1: break
        response = v1.base.load(out/(stage+'-response.json'))
        if (response.get('model'), response.get('digest')) != (config['model'], config['digest']):
            raise ValueError('Changed completed-prefix author')
        if stage in ('audit', 'final-audit'):
            current_audit = atomic.audit_value(response['content'], review, sources)
            artifact = 'audit.json' if stage == 'audit' else 'final-audit.json'
            if v1.base.load(out/artifact) != audit_dump(current_audit):
                raise ValueError('Changed completed-prefix audit')
            validate_attempted_transition(stage, next_stage, audit=current_audit)
        else:
            before = review
            review = atomic.revision_value(response['content'], review, current_audit, article, sources)
            validate_attempted_transition(stage, next_stage, before=before, after=review)
    expected = {'manifest.json', 'retained-batch.json', 'transport-failure.json'} | {
        'implementation/'+name for name in manifest['implementation']}
    expected |= {stage+'-request.json' for stage in report['calls']}
    expected |= {stage+'-response.json' for stage in report['calls'][:-1]}
    if len(report['calls']) >= 2: expected.add('audit.json')
    if len(report['calls']) >= 4: expected.add('final-audit.json')
    disk = {str(path.relative_to(out)) for path in out.rglob('*') if path.is_file() and path.name != 'report.json'}
    if not isinstance(report.get('artifacts'), dict) or set(report['artifacts']) != expected or disk != expected:
        raise ValueError('Request-only artifacts are not exactly bound')
    for name, digest in report['artifacts'].items():
        if v1.base.digest(out/name) != digest: raise ValueError('Changed request-only artifact')
    batch = v1.base.load(out/'retained-batch.json')
    if (set(batch) != {'schema', 'calls', 'idle_after'} or batch['schema'] != 'local-retained-batch.v1' or
            batch['idle_after'] is not True or len(batch['calls']) != len(report['calls'])):
        raise ValueError('Changed request-only retained batch')
    for number, (stage, entry) in enumerate(zip(report['calls'], batch['calls'], strict=True)):
        expected = ({'stage', 'keep_alive_seconds', 'resources_before'} if number == len(batch['calls'])-1 else
                    {'stage', 'keep_alive_seconds', 'resources_before', 'elapsed_seconds', 'timings_ns'})
        resources = entry.get('resources_before', {}) if isinstance(entry, dict) else {}
        expected_keep = 0 if stage == 'final-writer' else 3
        if (not isinstance(entry, dict) or set(entry) != expected or entry.get('stage') != stage or
                set(resources) != {'resident_reused', 'gpu_free_mib', 'resident_vram_bytes', 'docker', 'comfyui'}):
            raise ValueError('Changed attempted/completed retained call record')
        if (entry['keep_alive_seconds'] != expected_keep or
                type(resources['resident_reused']) is not bool or
                type(resources['gpu_free_mib']) is not int or resources['gpu_free_mib'] < 0 or
                type(resources['resident_vram_bytes']) is not int or resources['resident_vram_bytes'] < 0 or
                resources['docker'] != 'empty' or resources['comfyui'] != 'idle_or_not_listening'):
            raise ValueError('Changed request-only lease or resource evidence')
        if number < len(batch['calls'])-1:
            response = v1.base.load(out/(stage+'-response.json'))
            if entry['elapsed_seconds'] != response['elapsed_seconds'] or entry['timings_ns'] != response.get('timings_ns', {}):
                raise ValueError('Changed completed call timing')
    return {'schema': CONTRACT, 'report_sha256': v1.base.digest(out/'report.json'), 'status': 'failed',
            'model_calls': len(report['calls']), 'completed_model_calls': len(report['calls'])-1,
            'request_only_failure': True, 'literal_authorship_verified': True,
            'independent_review_required': True, 'autonomy_qualified': False, 'fresh_exam': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--run', type=Path); action.add_argument('--verify', type=Path); args = parser.parse_args()
    if args.verify: print(json.dumps(verify(args.verify), indent=2))
    else:
        _, result = run(args.run)
        raise SystemExit(int(result['status'] not in ('pending_independent_review',
            'pending_independent_review_after_final_correction', 'no_repair_requested')))
