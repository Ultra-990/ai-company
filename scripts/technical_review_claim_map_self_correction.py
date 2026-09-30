"""Bounded claim-map source correction; local judgments never accept work."""
import argparse
import json
from pathlib import Path
import sys
import tempfile
import time
from typing import Annotated, Literal

from pydantic import Field

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts import technical_review_claim_self_correction as v2

v1 = v2.v1
CONTRACT = 'technical-review-source-self-correction.v3'
ROOT, BUDGET, MAX_CALLS, CLAIMS = v2.ROOT, v2.BUDGET, 3, v2.CLAIMS
LEGACY_AUDIT_SHAPE = 'Return one assessment per claim ID, exactly once and\nin order.'
KEYED_AUDIT_SHAPE = ('Return one assessment value under every supplied claim ID key. '
                     'The map must contain every key exactly once and no other keys. '
                     'Object key order has no semantic meaning.')
if v2.CRITIC.count(LEGACY_AUDIT_SHAPE) != 1:
    raise RuntimeError('V3 critic prompt cannot replace the legacy audit-shape instruction exactly once')
CRITIC = v2.CRITIC.replace(LEGACY_AUDIT_SHAPE, KEYED_AUDIT_SHAPE)
WRITER = v2.WRITER.replace(
    'The writer audit is a deterministic projection of the preserved full audit:',
    'The writer audit is a deterministic keyed-map projection of the preserved full audit:')


class ClaimAssessment(v1.lab.StrictModel):
    verdict: Literal['supported', 'needs_revision', 'uncertain']
    issue_quote: Annotated[str, Field(max_length=500)]
    reason: Annotated[str, Field(min_length=10, max_length=400)]
    evidence_quotes: Annotated[list[v2.EvidenceQuote], Field(max_length=3)]


def audit_schema(review):
    ids = list(v2.claim_units(review))
    definition = ClaimAssessment.model_json_schema(ref_template='#/$defs/{model}')
    definitions = definition.pop('$defs', {})
    definitions['ClaimAssessment'] = definition
    return {'type': 'object', 'properties': {claim: {'$ref': '#/$defs/ClaimAssessment'} for claim in ids},
            'required': ids, 'additionalProperties': False, '$defs': definitions}


def audit_value(raw, review, sources):
    parsed = json.loads(raw, object_pairs_hook=v1.lab.unique_object)
    if not isinstance(parsed, dict):
        raise ValueError('Audit must be a claim-keyed object')
    expected = v2.claim_units(review)
    missing = [claim for claim in expected if claim not in parsed]
    extra = [claim for claim in parsed if claim not in expected]
    if missing or extra:
        raise ValueError('Audit claim map mismatch; missing='+','.join(missing)+'; extra='+','.join(extra))
    cards = {card['id']: card for card in sources}; canonical = {}
    for claim, unit in expected.items():
        row = ClaimAssessment.model_validate(parsed[claim])
        if row.verdict == 'supported':
            if row.issue_quote:
                raise ValueError('Supported audit claim must not declare an issue quote')
        elif not row.issue_quote.strip() or not any(row.issue_quote in text for text in v1.strings(unit)):
            raise ValueError('Audit issue must quote the actual reviewed claim')
        for anchor in row.evidence_quotes:
            if anchor.source_id not in cards or not any(anchor.quote in cards[anchor.source_id][key]
                                                        for key in ('notes', 'scope')):
                raise ValueError('Audit evidence quote must come from its named source card')
        canonical[claim] = row
    return canonical


def audit_dump(audit):
    return {claim: row.model_dump() for claim, row in audit.items()}


def supported(audit):
    return all(row.verdict == 'supported' for row in audit.values())


def writer_audit(audit):
    return {claim: ({'verdict': row.verdict} if row.verdict == 'supported' else row.model_dump())
            for claim, row in audit.items()}


def revision_value(raw, original, audit, article, sources):
    changed = v1.lab.check_response(raw, article, sources)
    protected = [claim for claim, row in audit.items() if row.verdict == 'supported']
    changed_claims = [claim for claim in protected
                      if v2.protected_value(original, claim) != v2.protected_value(changed, claim)]
    if changed_claims:
        raise ValueError('Preserve claims that the source audit marked supported: '+', '.join(changed_claims))
    return changed


def messages(stage, article, sources, review, audit=None):
    payload = {'article_lines': [{'line': number, 'text': text}
                                 for number, text in enumerate(article.splitlines(), 1)],
               'source_cards': sources}
    if stage == 'writer':
        payload.update(previous_review=review.model_dump(), claim_audit=writer_audit(audit))
        return {'system': WRITER, 'user': json.dumps(payload, ensure_ascii=False),
                'format': v1.lab.Review.model_json_schema()}
    payload['review_claims'] = v2.claim_units(review)
    return {'system': CRITIC, 'user': json.dumps(payload, ensure_ascii=False),
            'format': audit_schema(review)}


def snapshots():
    return [Path(__file__), Path(v2.__file__), Path(v1.__file__), Path(v1.base.__file__), Path(v1.lab.__file__),
            Path(__file__).parent/'local_retained_batch.py', Path(__file__).parent/'compare_local_models.py',
            Path(__file__).parents[1]/'app/services/local_ollama.py']


def run(source, *, root=ROOT):
    source = Path(source); _, review, article, sources = v1.origin(source)
    config = v1.lab.configuration() | BUDGET
    parent_config = v1.base.load(source/'manifest.json')['configuration']
    if (config['model'], config['digest']) != (parent_config['model'], parent_config['digest']):
        raise ValueError('Same pinned model must critique and revise its original review')
    resources = v1.lab.check_idle(); root = Path(root)
    if any(path.is_symlink() for path in (root, *root.parents)):
        raise ValueError('Private non-symlink workspace required')
    root.mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix='claim-map-self-correction-', dir=root)); code = out/'implementation'; code.mkdir()
    for path in snapshots(): (code/path.name).write_bytes(path.read_bytes())
    manifest = {'schema': CONTRACT, 'source': str(source.resolve()),
                'source_report_sha256': v1.base.digest(source/'report.json'),
                'source_manifest_sha256': v1.base.digest(source/'manifest.json'), 'configuration': config,
                'max_model_calls': MAX_CALLS, 'claim_kinds': list(CLAIMS), 'audit_shape': 'required-key-map',
                'fresh_exam': False, 'training_exported': False, 'weights_trained': False,
                'implementation': {path.name: v1.base.digest(path) for path in code.iterdir()}}
    v1.lab.save(out/'manifest.json', manifest)
    report = {'schema': CONTRACT, 'manifest_sha256': v1.base.digest(out/'manifest.json'), 'status': 'running',
              'calls': [], 'resources_before': resources, 'accepted': False, 'production_ready': False,
              'autonomy_qualified': False, 'semantic_decision': 'pending_independent_review', 'candidate': None}
    batch = v1.RetainedBatch(config, MAX_CALLS); started = time.monotonic()
    print(json.dumps({'output': str(out)}), flush=True)
    def save():
        report['seconds'] = round(time.monotonic()-started, 3)
        report['artifacts'] = {str(path.relative_to(out)): v1.base.digest(path) for path in out.rglob('*')
                               if path.is_file() and path.name != 'report.json'}
        v1.lab.save(out/'report.json', report)
    def call(stage, current, audit=None):
        request = messages(stage, article, sources, current, audit)
        report['calls'].append(stage); save()
        return batch.call(out, stage, request['system'], request['user'], request['format'],
                          final=stage == 'final-audit')
    save()
    try:
        first = audit_value(call('audit', review), review, sources); v1.lab.save(out/'audit.json', audit_dump(first))
        if supported(first): report['status'] = 'no_repair_requested'
        else:
            changed = revision_value(call('writer', review, first), review, first, article, sources)
            if changed.model_dump() == review.model_dump(): report['status'] = 'unchanged_revision'
            else:
                review = changed; final = audit_value(call('final-audit', review), review, sources)
                v1.lab.save(out/'final-audit.json', audit_dump(final))
                report['status'] = 'pending_independent_review' if supported(final) else 'needs_revision'
        v1.lab.save(out/'review.json', review.model_dump()); (out/'review.md').write_text(v1.lab.render(review, sources))
        report['candidate'] = 'review.json'
    except Exception as error:
        report.update(status='failed', error_type=type(error).__name__, error=str(error)[:600])
    finally:
        try: v1.lab.save(out/'retained-batch.json', batch.close())
        except Exception as error:
            report.update(status='failed', cleanup_error_type=type(error).__name__, cleanup_error=str(error)[:200])
            v1.lab.save(out/'retained-batch.json', {'calls': batch.calls, 'idle_after': False})
        save()
    return out, report


def verify(out):
    out = Path(out)
    if any(path.is_symlink() for path in (out, *out.parents)): raise ValueError('Non-symlink evidence required')
    report, manifest = v1.base.load(out/'report.json'), v1.base.load(out/'manifest.json')
    if (report.get('schema') != CONTRACT or manifest.get('schema') != CONTRACT or
            manifest.get('max_model_calls') != MAX_CALLS or manifest.get('claim_kinds') != list(CLAIMS) or
            manifest.get('audit_shape') != 'required-key-map' or
            any(manifest.get(key) is not False for key in ('fresh_exam', 'training_exported', 'weights_trained')) or
            any(report.get(key) is not False for key in ('accepted', 'production_ready', 'autonomy_qualified')) or
            report.get('semantic_decision') != 'pending_independent_review' or
            report.get('manifest_sha256') != v1.base.digest(out/'manifest.json')):
        raise ValueError('Changed claim-map protocol')
    source = Path(manifest['source']); _, review, article, sources = v1.origin(source)
    if (v1.base.digest(source/'report.json') != manifest['source_report_sha256'] or
            v1.base.digest(source/'manifest.json') != manifest['source_manifest_sha256']):
        raise ValueError('Source review changed')
    config = manifest['configuration']; parent = v1.base.load(source/'manifest.json')['configuration']
    if (any(config.get(key) != value for key, value in BUDGET.items()) or
            (config.get('model'), config.get('digest')) != (parent.get('model'), parent.get('digest'))):
        raise ValueError('Changed pinned inference configuration')
    if set(manifest['implementation']) != {path.name for path in snapshots()}:
        raise ValueError('Incomplete implementation snapshot')
    for name, digest in manifest['implementation'].items():
        if v1.base.digest(out/'implementation'/name) != digest: raise ValueError('Changed implementation snapshot')
    calls = []; failure = None
    def replay(stage, current, audit=None):
        calls.append(stage)
        if v1.base.load(out/(stage+'-request.json')) != messages(stage, article, sources, current, audit):
            raise ValueError('Changed claim-map prompt')
        response = v1.base.load(out/(stage+'-response.json'))
        if (response.get('model'), response.get('digest')) != (config['model'], config['digest']):
            raise ValueError('Changed local author')
        return response['content']
    def check(function, *args):
        nonlocal failure
        try: return function(*args)
        except (ValueError, TypeError) as error: failure = (type(error).__name__, str(error)[:600]); return None
    first = check(audit_value, replay('audit', review), review, sources); status = 'failed'
    if first is not None:
        if v1.base.load(out/'audit.json') != audit_dump(first): raise ValueError('Audit differs from model answer')
        if supported(first): status = 'no_repair_requested'
        else:
            changed = check(revision_value, replay('writer', review, first), review, first, article, sources)
            if changed is not None:
                if changed.model_dump() == review.model_dump(): status = 'unchanged_revision'
                else:
                    review = changed; final = check(audit_value, replay('final-audit', review), review, sources)
                    if final is not None:
                        if v1.base.load(out/'final-audit.json') != audit_dump(final): raise ValueError('Final audit differs')
                        status = 'pending_independent_review' if supported(final) else 'needs_revision'
    if report['calls'] != calls or len(calls) > MAX_CALLS or report['status'] != status:
        raise ValueError('Declared claim-map outcome does not replay')
    if failure is not None and failure != (report.get('error_type'), report.get('error')):
        raise ValueError('Changed validation failure')
    expected = {stage+'-'+suffix+'.json' for stage in calls for suffix in ('request', 'response')}
    actual = {path.name for suffix in ('request', 'response') for path in out.glob('*-'+suffix+'.json')}
    if actual != expected: raise ValueError('Extra, missing or reordered claim-map calls')
    required = expected | {'manifest.json', 'retained-batch.json'} | {
        'implementation/'+name for name in manifest['implementation']}
    if first is not None: required.add('audit.json')
    if status != 'failed':
        required |= {'review.json', 'review.md'}
        if 'final-audit' in calls: required.add('final-audit.json')
        if (report.get('candidate') != 'review.json' or v1.base.load(out/'review.json') != review.model_dump() or
                (out/'review.md').read_text() != v1.lab.render(review, sources)):
            raise ValueError('Claim-map export differs from literal model review')
    elif report.get('candidate') is not None: raise ValueError('Failed correction cannot claim a candidate')
    if not required <= set(report['artifacts']): raise ValueError('Required claim-map artifacts are not bound')
    for name, digest in report['artifacts'].items():
        path = out/name
        if not path.resolve().is_relative_to(out.resolve()) or v1.base.digest(path) != digest:
            raise ValueError('Changed claim-map artifact')
    batch = v1.base.load(out/'retained-batch.json')
    if batch.get('idle_after') is not True or [entry['stage'] for entry in batch['calls']] != calls:
        raise ValueError('Short bounded batch release not evidenced')
    for entry in batch['calls']:
        response = v1.base.load(out/(entry['stage']+'-response.json'))
        if (entry['keep_alive_seconds'] != (0 if entry['stage'] == 'final-audit' else 3) or
                entry['elapsed_seconds'] != response['elapsed_seconds'] or
                entry['timings_ns'] != response.get('timings_ns', {})):
            raise ValueError('Batch retention or timings changed')
    return {'schema': CONTRACT, 'report_sha256': v1.base.digest(out/'report.json'), 'status': status,
            'model_calls': len(calls), 'literal_authorship_verified': True,
            'independent_review_required': True, 'autonomy_qualified': False, 'fresh_exam': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--run', type=Path); action.add_argument('--verify', type=Path); args = parser.parse_args()
    if args.verify: print(json.dumps(verify(args.verify), indent=2))
    else:
        _, result = run(args.run); raise SystemExit(int(result['status'] not in ('pending_independent_review', 'no_repair_requested')))
