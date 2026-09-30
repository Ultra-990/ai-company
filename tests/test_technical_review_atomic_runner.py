import json

import pytest

from scripts import technical_review_atomic_runner as runner
from tests.test_technical_review_atomic_claim_audit import assessment_map
from tests.test_technical_review_holdout import content, run_fixture


@pytest.fixture
def pipeline(tmp_path, monkeypatch):
    source, _, _, _ = run_fixture(tmp_path/'source', monkeypatch, [content()])
    article = (source/'article.md').read_text(); sources = runner.v1.base.load(source/'sources.json')
    original = runner.v1.lab.check_response(content(), article, sources)
    first = assessment_map(original); first_claim = next(k for k in first if k.startswith('comment:3:diagnosis:'))
    first[first_claim].update(verdict='needs_revision', support_basis='unsupported',
                              issue_quote=runner.atomic.atomic_units(original)[first_claim]['text'], evidence_quotes=[])
    middle = original.model_copy(deep=True); middle.comments[0].issue = 'A bounded corrected diagnosis.'
    final = assessment_map(middle); final_claim = next(k for k in final if k.startswith('comment:3:recommendation:'))
    final[final_claim].update(verdict='needs_revision', support_basis='unsupported',
                              issue_quote=runner.atomic.atomic_units(middle)[final_claim]['text'], evidence_quotes=[])
    corrected = middle.model_copy(deep=True); corrected.comments[0].recommendation = 'A bounded corrected recommendation.'
    outputs = [first, middle.model_dump(), final, corrected.model_dump()]; calls = []
    config = runner.v1.base.load(source/'manifest.json')['configuration']
    monkeypatch.setattr(runner.v1.lab, 'configuration', lambda: config)
    monkeypatch.setattr(runner.v1.lab, 'check_idle', lambda: {})
    class Batch:
        def __init__(self, supplied, maximum): assert maximum == 4; self.calls = []
        def call(self, out, stage, system, user, schema, *, final=False):
            response = {'content': json.dumps(outputs[len(calls)]), 'model': config['model'],
                        'digest': config['digest'], 'elapsed_seconds': .1}
            calls.append(stage)
            runner.v1.lab.save(out/(stage+'-request.json'), {'system': system, 'user': user, 'format': schema})
            runner.v1.lab.save(out/(stage+'-response.json'), response)
            self.calls.append({'stage': stage, 'keep_alive_seconds': 0 if final else 3,
                'resources_before': {'resident_reused': False, 'gpu_free_mib': 30000,
                    'resident_vram_bytes': 0, 'docker': 'empty', 'comfyui': 'idle_or_not_listening'},
                'elapsed_seconds': .1, 'timings_ns': {}})
            return response['content']
        def close(self):
            return {'schema': 'local-retained-batch.v1', 'calls': self.calls, 'idle_after': True}
    monkeypatch.setattr(runner.v1, 'RetainedBatch', Batch)
    return source, tmp_path/'runs', outputs, calls, middle, corrected


def test_atomic_runner_four_call_chain_and_exact_replay(pipeline):
    source, root, _, calls, middle, corrected = pipeline
    out, report = runner.run(source, root=root)
    assert report['status'] == 'pending_independent_review_after_final_correction'
    assert calls == ['audit', 'writer', 'final-audit', 'final-writer']
    verified = runner.verify(out)
    assert verified['model_calls'] == 4 and verified['autonomy_qualified'] is False
    result = runner.v1.base.load(out/'review.json')
    assert result['comments'][0]['issue'] == middle.comments[0].issue
    assert result['comments'][0]['recommendation'] == corrected.comments[0].recommendation
    assert report['accepted'] is report['production_ready'] is False


def test_atomic_runner_rejects_final_writer_damage_to_supported_field(pipeline):
    source, root, outputs, _, _, _ = pipeline
    outputs[3]['comments'][0]['issue'] = 'Damage the supported final diagnosis.'
    out, report = runner.run(source, root=root)
    assert report['status'] == 'failed'
    assert runner.verify(out)['status'] == 'failed'


def test_atomic_runner_invalid_map_is_failed_and_replayable(pipeline):
    source, root, outputs, calls, _, _ = pipeline
    outputs[0].pop(next(iter(outputs[0])))
    out, report = runner.run(source, root=root)
    assert report['status'] == 'failed' and calls == ['audit']
    assert runner.verify(out)['status'] == 'failed'


@pytest.mark.parametrize('fault', ['artifact', 'resource'])
def test_atomic_runner_exact_artifact_and_resource_evidence(pipeline, fault):
    source, root, _, _, _, _ = pipeline
    out, _ = runner.run(source, root=root); report = runner.v1.base.load(out/'report.json')
    if fault == 'artifact':
        extra = out/'extra.json'; extra.write_text('{}')
    else:
        batch = runner.v1.base.load(out/'retained-batch.json')
        batch['calls'][0]['resources_before']['note'] = 'extra'
        runner.v1.lab.save(out/'retained-batch.json', batch)
        report['artifacts']['retained-batch.json'] = runner.v1.base.digest(out/'retained-batch.json')
        runner.v1.lab.save(out/'report.json', report)
    with pytest.raises(ValueError): runner.verify(out)


def test_bound_engine_keeps_keyword_defaults_and_run_without_explicit_root(pipeline, monkeypatch, tmp_path):
    source, _, _, _, _, _ = pipeline
    assert runner._engine_run.__kwdefaults__ == runner.engine.run.__kwdefaults__
    target = tmp_path/'default-root'
    monkeypatch.setitem(runner.run.__kwdefaults__, 'root', target)
    out, report = runner.run(source)
    assert out.parent == target
    assert report['status'] == 'pending_independent_review_after_final_correction'


def test_request_only_transport_failure_is_preserved_and_replayed(tmp_path, monkeypatch):
    source, _, _, _ = run_fixture(tmp_path/'source', monkeypatch, [content()])
    config = runner.v1.base.load(source/'manifest.json')['configuration']
    monkeypatch.setattr(runner.v1.lab, 'configuration', lambda: config)
    monkeypatch.setattr(runner.v1.lab, 'check_idle', lambda: {})
    class FailingBatch:
        def __init__(self, supplied, maximum): self.calls = []
        def call(self, out, stage, system, user, schema, *, final=False):
            entry = {'stage': stage, 'keep_alive_seconds': 0 if final else 3,
                     'resources_before': {'resident_reused': False, 'gpu_free_mib': 30000,
                         'resident_vram_bytes': 0, 'docker': 'empty', 'comfyui': 'idle_or_not_listening'}}
            self.calls.append(entry)
            runner.v1.lab.save(out/(stage+'-request.json'), {'system': system, 'user': user, 'format': schema})
            raise ConnectionError('synthetic_transport_failure')
        def close(self):
            return {'schema': 'local-retained-batch.v1', 'calls': self.calls, 'idle_after': True}
    monkeypatch.setattr(runner.v1, 'RetainedBatch', FailingBatch)
    out, report = runner.run(source, root=tmp_path/'runs')
    assert report['status'] == 'failed' and report['calls'] == ['audit']
    assert not (out/'audit-response.json').exists()
    verified = runner.verify(out)
    assert verified['request_only_failure'] is True
    assert verified['model_calls'] == 1 and verified['completed_model_calls'] == 0
    failure = runner.v1.base.load(out/'transport-failure.json')
    assert failure['error_type'] == 'ConnectionError'
    original_batch = runner.v1.base.load(out/'retained-batch.json')
    for field, value in [('keep_alive_seconds', 9), ('docker', 'busy')]:
        batch = json.loads(json.dumps(original_batch))
        if field == 'docker': batch['calls'][0]['resources_before']['docker'] = value
        else: batch['calls'][0][field] = value
        runner.v1.lab.save(out/'retained-batch.json', batch)
        changed_report = runner.v1.base.load(out/'report.json')
        changed_report['artifacts']['retained-batch.json'] = runner.v1.base.digest(out/'retained-batch.json')
        runner.v1.lab.save(out/'report.json', changed_report)
        with pytest.raises(ValueError, match='lease or resource'):
            runner.verify(out)


@pytest.mark.parametrize('fault', ['config', 'semantic', 'audit_shape', 'final_correction'])
def test_request_only_rejects_changed_configuration_or_semantics(tmp_path, monkeypatch, fault):
    source, _, _, _ = run_fixture(tmp_path/'source', monkeypatch, [content()])
    config = runner.v1.base.load(source/'manifest.json')['configuration']
    monkeypatch.setattr(runner.v1.lab, 'configuration', lambda: config)
    monkeypatch.setattr(runner.v1.lab, 'check_idle', lambda: {})
    class Failure:
        def __init__(self, supplied, maximum): self.calls=[]
        def call(self, out, stage, system, user, schema, *, final=False):
            self.calls.append({'stage': stage, 'keep_alive_seconds': 3,
                'resources_before': {'resident_reused': False, 'gpu_free_mib': 30000,
                    'resident_vram_bytes': 0, 'docker': 'empty', 'comfyui': 'idle_or_not_listening'}})
            runner.v1.lab.save(out/(stage+'-request.json'), {'system':system,'user':user,'format':schema})
            raise ConnectionError('transport')
        def close(self): return {'schema':'local-retained-batch.v1','calls':self.calls,'idle_after':True}
    monkeypatch.setattr(runner.v1, 'RetainedBatch', Failure)
    out, _ = runner.run(source, root=tmp_path/'runs'); report = runner.v1.base.load(out/'report.json')
    if fault == 'semantic': report['semantic_decision'] = 'accepted'
    else:
        manifest = runner.v1.base.load(out/'manifest.json')
        if fault == 'config': manifest['configuration']['num_ctx'] -= 1
        else: manifest[fault] = 'invented'
        runner.v1.lab.save(out/'manifest.json', manifest)
        report['manifest_sha256'] = runner.v1.base.digest(out/'manifest.json')
        report['artifacts']['manifest.json'] = runner.v1.base.digest(out/'manifest.json')
    runner.v1.lab.save(out/'report.json', report)
    with pytest.raises(ValueError): runner.verify(out)


@pytest.mark.parametrize('fault', ['completed_response', 'next_request'])
def test_request_only_replays_completed_prefix_semantics(pipeline, monkeypatch, fault):
    source, root, outputs, calls, _, _ = pipeline
    config = runner.v1.base.load(source/'manifest.json')['configuration']
    class FailFinalAudit:
        def __init__(self, supplied, maximum): self.calls=[]
        def call(self, out, stage, system, user, schema, *, final=False):
            entry={'stage':stage,'keep_alive_seconds':0 if final else 3,
                'resources_before': {'resident_reused':False,'gpu_free_mib':30000,
                    'resident_vram_bytes':0,'docker':'empty','comfyui':'idle_or_not_listening'}}
            self.calls.append(entry); runner.v1.lab.save(out/(stage+'-request.json'),{'system':system,'user':user,'format':schema})
            if stage == 'final-audit': raise ConnectionError('transport_after_completed_prefix')
            response={'content':json.dumps(outputs[len(calls)]),'model':config['model'],'digest':config['digest'],'elapsed_seconds':.1}
            calls.append(stage); runner.v1.lab.save(out/(stage+'-response.json'),response)
            entry.update(elapsed_seconds=.1,timings_ns={}); return response['content']
        def close(self): return {'schema':'local-retained-batch.v1','calls':self.calls,'idle_after':True}
    monkeypatch.setattr(runner.v1, 'RetainedBatch', FailFinalAudit)
    out, report = runner.run(source, root=root)
    assert report['calls'] == ['audit','writer','final-audit']
    if fault == 'completed_response':
        response=runner.v1.base.load(out/'audit-response.json'); response['content']='{}'
        runner.v1.lab.save(out/'audit-response.json',response); changed='audit-response.json'
    else:
        request=runner.v1.base.load(out/'final-audit-request.json'); request['system']+=' changed'
        runner.v1.lab.save(out/'final-audit-request.json',request); changed='final-audit-request.json'
    report=runner.v1.base.load(out/'report.json'); report['artifacts'][changed]=runner.v1.base.digest(out/changed)
    runner.v1.lab.save(out/'report.json',report)
    with pytest.raises((ValueError, TypeError)):
        runner.verify(out)


@pytest.mark.parametrize('fault, message', [
    ('supported_initial_audit', 'Impossible writer attempt'),
    ('unchanged_writer', 'Impossible final-audit attempt'),
    ('supported_final_audit', 'Impossible final-writer attempt'),
])
def test_request_only_rejects_impossible_state_machine_prefixes(
        pipeline, monkeypatch, fault, message):
    source, root, outputs, calls, _, _ = pipeline
    config = runner.v1.base.load(source/'manifest.json')['configuration']

    class FailFinalWriter:
        def __init__(self, supplied, maximum): self.calls = []
        def call(self, out, stage, system, user, schema, *, final=False):
            entry = {'stage': stage, 'keep_alive_seconds': 0 if final else 3,
                     'resources_before': {'resident_reused': False, 'gpu_free_mib': 30000,
                         'resident_vram_bytes': 0, 'docker': 'empty',
                         'comfyui': 'idle_or_not_listening'}}
            self.calls.append(entry)
            runner.v1.lab.save(out/(stage+'-request.json'),
                               {'system': system, 'user': user, 'format': schema})
            if stage == 'final-writer':
                raise ConnectionError('transport_after_valid_prefix')
            response = {'content': json.dumps(outputs[len(calls)]), 'model': config['model'],
                        'digest': config['digest'], 'elapsed_seconds': .1}
            calls.append(stage); runner.v1.lab.save(out/(stage+'-response.json'), response)
            entry.update(elapsed_seconds=.1, timings_ns={}); return response['content']
        def close(self):
            return {'schema': 'local-retained-batch.v1', 'calls': self.calls, 'idle_after': True}

    monkeypatch.setattr(runner.v1, 'RetainedBatch', FailFinalWriter)
    out, report = runner.run(source, root=root)
    assert report['calls'] == ['audit', 'writer', 'final-audit', 'final-writer']
    if fault == 'supported_initial_audit':
        artifact = 'audit-response.json'; replacement = assessment_map(
            runner.v1.lab.check_response(content(), (source/'article.md').read_text(),
                                         runner.v1.base.load(source/'sources.json')))
    elif fault == 'unchanged_writer':
        artifact = 'writer-response.json'; replacement = json.loads(content())
    else:
        artifact = 'final-audit-response.json'; replacement = assessment_map(
            runner.v1.lab.check_response(json.dumps(outputs[1]), (source/'article.md').read_text(),
                                         runner.v1.base.load(source/'sources.json')))
    response = runner.v1.base.load(out/artifact); response['content'] = json.dumps(replacement)
    runner.v1.lab.save(out/artifact, response)
    report = runner.v1.base.load(out/'report.json')
    report['artifacts'][artifact] = runner.v1.base.digest(out/artifact)
    if fault in ('supported_initial_audit', 'supported_final_audit'):
        audit_artifact = 'audit.json' if fault == 'supported_initial_audit' else 'final-audit.json'
        audited_review = runner.v1.lab.check_response(
            content() if fault == 'supported_initial_audit' else json.dumps(outputs[1]),
            (source/'article.md').read_text(), runner.v1.base.load(source/'sources.json'))
        parsed = runner.atomic.audit_value(response['content'], audited_review,
                                           runner.v1.base.load(source/'sources.json'))
        runner.v1.lab.save(out/audit_artifact, runner.audit_dump(parsed))
        report['artifacts'][audit_artifact] = runner.v1.base.digest(out/audit_artifact)
    runner.v1.lab.save(out/'report.json', report)
    with pytest.raises(ValueError, match=message):
        runner.verify(out)
