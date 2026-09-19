import json
from hashlib import sha256
from pathlib import Path

import pytest

from scripts import evaluate_qwen_repairs as evaluate
from scripts import qwen_evaluation_catalog as catalog
from scripts.prepare_training_data import validate_dataset, DatasetError
from tests.test_repair_training import run_result


def test_frozen_catalog_and_training_families_are_separate():
    suite=catalog.load_suite()
    assert len(suite['cases'])==4
    families={c['family'] for c in suite['cases']}
    assert len(families)==4
    root=Path(__file__).resolve().parents[1]/'datasets/qwen'
    for name in ['specialization-batch-001.jsonl','repair-batch-001.jsonl']:
        rows,_=validate_dataset((root/name).read_bytes())
        assert not families.intersection(r['family'] for r in rows)


def test_changed_suite_rejected(tmp_path,monkeypatch):
    path=tmp_path/'changed.json'
    path.write_text('{}')
    monkeypatch.setattr(catalog,'SUITE',path)
    with pytest.raises(ValueError): catalog.load_suite()


@pytest.mark.parametrize('split',['train','validation'])
@pytest.mark.parametrize('reuse',['family','brief'])
def test_dataset_blocks_evaluation_contamination(split,reuse):
    path=Path(__file__).resolve().parents[1]/'datasets/qwen/repair-batch-001.jsonl'
    row=json.loads(path.read_text().splitlines()[0])
    case=catalog.load_suite()['cases'][0]
    row['split']=split
    if reuse=='family': row['family']=case['family']
    else: row['messages'][1]['content']='Different wrapper '+case['brief']
    with pytest.raises(DatasetError): validate_dataset(json.dumps(row).encode())


def test_no_run_flag_does_not_use_model_or_runner(monkeypatch,capsys):
    monkeypatch.setattr('sys.argv',['evaluate_qwen_repairs.py'])
    monkeypatch.setattr(evaluate,'configuration',lambda:pytest.fail('model setup'))
    assert evaluate.main()==0
    assert json.loads(capsys.readouterr().out)['model_invoked'] is False


@pytest.mark.parametrize('mode,expected',[
    ('pass','passed'),('fail','failed_tests'),('bad_json','invalid_output'),
    ('timeout','infrastructure_error'),('cleanup','infrastructure_error'),
])
def test_one_attempt_and_honest_failure_classification(monkeypatch,mode,expected):
    monkeypatch.setattr(evaluate,'ensure_idle',lambda:None)
    sources=[]
    calls=[]
    class Runner:
        def run(self,files,config,name):
            sources.append(dict(files))
            if len(sources)==1: return run_result(False)
            result=run_result(mode!='fail')
            if mode=='cleanup': result['cleanup_confirmed']=False
            return result
    class Model:
        def complete(self,messages):
            calls.append(messages)
            if mode=='timeout': raise TimeoutError()
            return {'content':'{}' if mode=='bad_json' else json.dumps({'source':'def fixed(): pass'})}
    case=catalog.load_suite()['cases'][0]
    result=evaluate.evaluate_case(case,Model(),Runner(),{})
    assert result['status']==expected
    assert len(calls)==1
    assert all(s['test_app.py']==case['tests'] for s in sources)
    assert 'review' not in result and 'split' not in result


def test_incomplete_evaluation_has_no_pass_rate():
    assert evaluate.summary([{'status':'passed'}],4)['pass_rate'] is None
    assert evaluate.summary([{'status':'infrastructure_error'}]*4,4)['pass_rate'] is None
    result=evaluate.summary([{'status':'passed'}]*3+[{'status':'failed_tests'}],4)
    assert result['complete'] and result['pass_rate']==.75


def test_archived_baseline_matches_frozen_suite_and_exact_sources():
    raw=(Path(__file__).resolve().parents[1]/'datasets/qwen/evaluation/baseline-001.json').read_bytes()
    assert sha256(raw).hexdigest()=='1a37f1f4802bee6680b079fcb4dc725a8f81cab3ed4fc8f91b7f76f004884be2'
    report=json.loads(raw)
    assert report['suite']==catalog.load_suite()
    assert report['suite_sha256']==catalog.CHECKSUM
    assert report['summary']==evaluate.summary(report['cases'],4)
    assert report['summary']['passed']==4
    assert report['training_started'] is False and report['training_examples_exported']==0
    for case,entry in zip(report['suite']['cases'],report['cases']):
        assert case['id']==entry['id']
        assert case['family']==entry['family']
        assert sha256(case['tests'].encode()).hexdigest()==entry['tests_sha256']
        assert sha256(case['broken'].encode()).hexdigest()==entry['source_before_sha256']
        source=evaluate.parse_source(entry['result']['content'])
        assert sha256(source.encode()).hexdigest()==entry['source_after_sha256']
        before=evaluate.inspect_run(entry['before'],False)
        evaluate.inspect_run(entry['after'],True)
        assert entry['messages']==evaluate.messages_for(case,before['tests_log'])
        assert entry['before']['profile']==entry['after']['profile']


def test_missing_catalog_prevents_dataset_export(monkeypatch):
    monkeypatch.setattr(catalog,'load_suite',lambda:(_ for _ in ()).throw(OSError()))
    with pytest.raises(DatasetError): validate_dataset(b'{}')
