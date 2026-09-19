import json
from pathlib import Path
import pytest
from app.services.local_ollama import ModelFailure
from scripts import evaluate_qwen_roles as evaluate,qwen_evaluation_catalog as catalog
from scripts.prepare_training_data import validate_dataset,DatasetError


def response(case):return json.dumps(case['expected']|{'reason':'Wynik oparty wyłącznie na danych scenariusza.'})


def test_frozen_suite_and_no_expected_answers_in_messages():
    suite=catalog.load_role_suite()
    assert len(suite['cases'])==12
    assert len({c['family'] for c in suite['cases']})==12
    assert {c['role'] for c in suite['cases']}=={'analyst','manager','reviewer','delivery'}
    for case in suite['cases']:
        assert evaluate.messages_for(suite,case)==[
            {'role':'system','content':suite['instruction']},{'role':'user','content':case['brief']}]
        assert evaluate.check_response(case,response(case))[1]


@pytest.mark.parametrize('split',['train','validation'])
@pytest.mark.parametrize('reuse',['family','brief'])
def test_role_cases_cannot_become_training_examples(split,reuse):
    row=json.loads((Path(__file__).resolve().parents[1]/'datasets/qwen/repair-batch-001.jsonl').read_text().splitlines()[0])
    case=catalog.load_role_suite()['cases'][0]
    row['split']=split
    if reuse=='family':row['family']=case['family']
    else:row['messages'][1]['content']='Wrapper '+case['brief']
    with pytest.raises(DatasetError):validate_dataset(json.dumps(row).encode())


def test_changed_or_missing_role_suite_prevents_export(tmp_path,monkeypatch):
    path=tmp_path/'roles.json';path.write_text('{}')
    monkeypatch.setattr(catalog,'ROLE_SUITE',path)
    with pytest.raises(ValueError):catalog.load_role_suite()
    with pytest.raises(DatasetError):validate_dataset(b'{}')


def test_no_run_does_not_contact_model(monkeypatch,capsys):
    monkeypatch.setattr('sys.argv',['evaluate_qwen_roles.py'])
    monkeypatch.setattr(evaluate,'configuration',lambda:pytest.fail('model config'))
    assert evaluate.main()==0
    assert json.loads(capsys.readouterr().out)['model_invoked'] is False


@pytest.mark.parametrize('mode,status',[('ok','passed'),('wrong','wrong_decision'),
    ('bad','invalid_output'),('truncated','invalid_output'),('timeout','infrastructure_error')])
def test_single_attempt_and_failure_classification(monkeypatch,mode,status):
    monkeypatch.setattr(evaluate,'ensure_idle',lambda:None)
    suite=catalog.load_role_suite();case=suite['cases'][0];calls=[]
    class Provider:
        def complete(self,messages):
            calls.append(messages)
            if mode=='truncated':raise ModelFailure('truncated_output')
            if mode=='timeout':raise TimeoutError()
            raw=response(case)
            if mode=='wrong':raw=raw.replace('SUPPORTED','UNSUPPORTED')
            if mode=='bad':raw='{}'
            return {'content':raw}
    result=evaluate.evaluate_case(suite,case,Provider())
    assert result['status']==status and len(calls)==1 and result['reason_reviewed'] is False


@pytest.mark.parametrize('patch',[{'target_ids':['Z11','Z11']},{'target_ids':'Z11'},
    {'reason':'x'},{'reason':42},{'decision':'PUBLISH'},{'extra':'value'}])
def test_invalid_contract(patch):
    case=catalog.load_role_suite()['cases'][0]
    data=json.loads(response(case))|patch
    with pytest.raises(ValueError):evaluate.check_response(case,json.dumps(data))


def test_partial_results_do_not_appear_as_complete_scores():
    suite=catalog.load_role_suite()
    entries=[{'role':'analyst','status':'passed'}]
    result=evaluate.summarize(suite,entries)
    assert result['overall']['decision_pass_rate'] is None
    assert result['roles']['analyst']['decision_pass_rate'] is None
    assert result['roles']['manager']['attempted']==0
    assert result['production_assignment_allowed'] is False
    entries=[{'role':c['role'],'status':'passed'} for c in suite['cases']]
    entries[-1]['status']='wrong_decision'
    result=evaluate.summarize(suite,entries)
    assert result['overall']['decision_pass_rate']==11/12
    assert result['roles']['delivery']['decision_pass_rate']==2/3
