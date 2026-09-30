"""Claim-map correction with one bounded final-audit-directed author repair."""
import argparse
import json
from pathlib import Path
import sys
import tempfile
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts import technical_review_claim_map_self_correction as v3

v2, v1 = v3.v2, v3.v1
CONTRACT = 'technical-review-source-self-correction.v4'
ROOT, BUDGET, CLAIMS = v3.ROOT, v3.BUDGET, v3.CLAIMS
MAX_CALLS = 4
WRITER = v3.WRITER + '''
FINAL CORRECTION: When stage is final-writer, the supplied claim audit is the
post-revision audit of previous_review. Preserve exactly only claims marked
supported in that final audit. Correct every needs_revision or uncertain claim
without changing final-audit-supported fields. This is one bounded author repair,
not approval; no later local audit is implied and independent review is required.'''


def messages(stage, article, sources, review, audit=None):
    if stage not in ('writer', 'final-writer'):
        return v3.messages(stage, article, sources, review, audit)
    payload = {'article_lines': [{'line': number, 'text': text}
                                 for number, text in enumerate(article.splitlines(), 1)],
               'source_cards': sources, 'previous_review': review.model_dump(),
               'claim_audit': v3.writer_audit(audit), 'revision_stage': stage}
    return {'system': WRITER, 'user': json.dumps(payload, ensure_ascii=False),
            'format': v1.lab.Review.model_json_schema()}


def snapshots():
    return [Path(__file__), Path(v3.__file__), Path(v2.__file__), Path(v1.__file__),
            Path(v1.base.__file__), Path(v1.lab.__file__), Path(__file__).parent/'local_retained_batch.py',
            Path(__file__).parent/'compare_local_models.py',
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
    out = Path(tempfile.mkdtemp(prefix='final-correction-', dir=root)); code = out/'implementation'; code.mkdir()
    for path in snapshots(): (code/path.name).write_bytes(path.read_bytes())
    manifest = {'schema': CONTRACT, 'source': str(source.resolve()),
                'source_report_sha256': v1.base.digest(source/'report.json'),
                'source_manifest_sha256': v1.base.digest(source/'manifest.json'), 'configuration': config,
                'max_model_calls': MAX_CALLS, 'claim_kinds': list(CLAIMS), 'audit_shape': 'required-key-map',
                'final_correction': 'single-author-call-after-objecting-final-audit',
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
                          final=stage == 'final-writer')
    save()
    try:
        first = v3.audit_value(call('audit', review), review, sources)
        v1.lab.save(out/'audit.json', v3.audit_dump(first))
        if v3.supported(first): report['status'] = 'no_repair_requested'
        else:
            changed = v3.revision_value(call('writer', review, first), review, first, article, sources)
            if changed.model_dump() == review.model_dump(): report['status'] = 'unchanged_revision'
            else:
                review = changed; final = v3.audit_value(call('final-audit', review), review, sources)
                v1.lab.save(out/'final-audit.json', v3.audit_dump(final))
                if v3.supported(final): report['status'] = 'pending_independent_review'
                else:
                    corrected = v3.revision_value(call('final-writer', review, final), review, final,
                                                  article, sources)
                    if corrected.model_dump() == review.model_dump():
                        report['status'] = 'unchanged_final_revision'
                    else:
                        review = corrected; report['status'] = 'pending_independent_review_after_final_correction'
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
            manifest.get('final_correction') != 'single-author-call-after-objecting-final-audit' or
            any(manifest.get(key) is not False for key in ('fresh_exam', 'training_exported', 'weights_trained')) or
            any(report.get(key) is not False for key in ('accepted', 'production_ready', 'autonomy_qualified')) or
            report.get('semantic_decision') != 'pending_independent_review' or
            report.get('manifest_sha256') != v1.base.digest(out/'manifest.json')):
        raise ValueError('Changed final-correction protocol')
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
            raise ValueError('Changed final-correction prompt')
        response = v1.base.load(out/(stage+'-response.json'))
        if (response.get('model'), response.get('digest')) != (config['model'], config['digest']):
            raise ValueError('Changed local author')
        return response['content']
    def check(function, *args):
        nonlocal failure
        try: return function(*args)
        except (ValueError, TypeError) as error: failure = (type(error).__name__, str(error)[:600]); return None
    first = check(v3.audit_value, replay('audit', review), review, sources); status = 'failed'
    if first is not None:
        if v1.base.load(out/'audit.json') != v3.audit_dump(first): raise ValueError('Audit differs')
        if v3.supported(first): status = 'no_repair_requested'
        else:
            changed = check(v3.revision_value, replay('writer', review, first), review, first, article, sources)
            if changed is not None:
                if changed.model_dump() == review.model_dump(): status = 'unchanged_revision'
                else:
                    review = changed; final = check(v3.audit_value, replay('final-audit', review), review, sources)
                    if final is not None:
                        if v1.base.load(out/'final-audit.json') != v3.audit_dump(final): raise ValueError('Final audit differs')
                        if v3.supported(final): status = 'pending_independent_review'
                        else:
                            corrected = check(v3.revision_value, replay('final-writer', review, final),
                                              review, final, article, sources)
                            if corrected is not None:
                                if corrected.model_dump() == review.model_dump(): status = 'unchanged_final_revision'
                                else:
                                    review = corrected; status = 'pending_independent_review_after_final_correction'
    if report['calls'] != calls or len(calls) > MAX_CALLS or report['status'] != status:
        raise ValueError('Declared final-correction outcome does not replay')
    if failure is not None and failure != (report.get('error_type'), report.get('error')):
        raise ValueError('Changed validation failure')
    expected = {stage+'-'+suffix+'.json' for stage in calls for suffix in ('request', 'response')}
    actual = {path.name for suffix in ('request', 'response') for path in out.glob('*-'+suffix+'.json')}
    if actual != expected: raise ValueError('Extra, missing or reordered calls')
    required = expected | {'manifest.json', 'retained-batch.json'} | {
        'implementation/'+name for name in manifest['implementation']}
    if first is not None: required.add('audit.json')
    if 'final-audit' in calls: required.add('final-audit.json')
    if status != 'failed':
        required |= {'review.json', 'review.md'}
    elif report.get('candidate') is not None: raise ValueError('Failed correction cannot claim a candidate')
    disk_artifacts = {str(path.relative_to(out)) for path in out.rglob('*')
                      if path.is_file() and path.name != 'report.json'}
    if (not isinstance(report.get('artifacts'), dict) or
            set(report['artifacts']) != required or disk_artifacts != required):
        raise ValueError('Exact branch artifact set is not preserved and bound')
    if status != 'failed' and (report.get('candidate') != 'review.json' or
            v1.base.load(out/'review.json') != review.model_dump() or
            (out/'review.md').read_text() != v1.lab.render(review, sources)):
        raise ValueError('Final-correction export differs from literal author review')
    for name, digest in report['artifacts'].items():
        path = out/name
        if not path.resolve().is_relative_to(out.resolve()) or v1.base.digest(path) != digest:
            raise ValueError('Changed final-correction artifact')
    batch = v1.base.load(out/'retained-batch.json')
    if (set(batch) != {'schema', 'calls', 'idle_after'} or
            batch.get('schema') != 'local-retained-batch.v1' or batch.get('idle_after') is not True or
            not isinstance(batch.get('calls'), list) or len(batch['calls']) != len(calls)):
        raise ValueError('Short bounded batch release not evidenced')
    resource_keys = {'resident_reused', 'gpu_free_mib', 'resident_vram_bytes', 'docker', 'comfyui'}
    for expected_stage, entry in zip(calls, batch['calls'], strict=True):
        if (not isinstance(entry, dict) or set(entry) != {
                'stage', 'keep_alive_seconds', 'resources_before', 'elapsed_seconds', 'timings_ns'} or
                entry.get('stage') != expected_stage or not isinstance(entry.get('resources_before'), dict) or
                set(entry['resources_before']) != resource_keys or
                type(entry['resources_before']['resident_reused']) is not bool or
                type(entry['resources_before']['gpu_free_mib']) is not int or
                type(entry['resources_before']['resident_vram_bytes']) is not int or
                entry['resources_before']['docker'] != 'empty' or
                entry['resources_before']['comfyui'] != 'idle_or_not_listening'):
            raise ValueError('Changed retained call or resource evidence')
        response = v1.base.load(out/(entry['stage']+'-response.json'))
        expected_keep = 0 if entry['stage'] == 'final-writer' else 3
        if (entry['keep_alive_seconds'] != expected_keep or entry['elapsed_seconds'] != response['elapsed_seconds'] or
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
        _, result = run(args.run)
        raise SystemExit(int(result['status'] not in ('pending_independent_review',
            'pending_independent_review_after_final_correction', 'no_repair_requested')))
