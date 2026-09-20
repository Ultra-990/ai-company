import copy
import json

import pytest

from scripts import train_qwen_pilot as pilot
from scripts.prepare_training_data import MINIMUMS


def test_research_protocol_keeps_production_gate_and_reviewed_train_only():
    plan,rows,gate,suite=pilot.load_protocol()
    assert len(rows)==14 and len(suite['cases'])==12
    assert gate['export_ready'] is False and MINIMUMS=={'train':200,'validation':25,'test':50}
    assert all(r['review']['status']=='approved' and r['split']=='train' for r in rows)
    assert plan['production_ready'] is plan['automatic_promotion'] is False


@pytest.mark.parametrize('change',['data','steps','promotion','regression'])
def test_changed_inputs_and_unbounded_recipe_are_rejected(tmp_path,monkeypatch,change):
    plan=json.loads(pilot.PLAN.read_text())
    if change=='data':plan['datasets'][0]['sha256']='0'*64
    if change=='steps':plan['training']['max_steps']=100000
    if change=='promotion':plan['automatic_promotion']=True
    if change=='regression':plan['evaluation']['role_suite_sha256']='0'*64
    path=tmp_path/'plan.json';path.write_text(json.dumps(plan));monkeypatch.setattr(pilot,'PLAN',path)
    with pytest.raises(ValueError):pilot.load_protocol()


def test_comparison_records_regression_and_never_promotes():
    before=[{'id':'a','status':'passed'},{'id':'b','status':'wrong_decision'}]
    after=[{'id':'a','status':'invalid_output'},{'id':'b','status':'passed'}]
    compared=pilot.compare(before,after,2)
    assert compared['complete'] and compared['regressed_cases']==['a'] and compared['improved_cases']==['b']
    assert compared['production_ready'] is False and compared['expertise_proven'] is False
    assert pilot.compare(before,after[:1],2)['complete'] is False
    assert pilot.compare(before,[{'id':'x','status':'passed'},after[1]],2)['complete'] is False


class Values:
    def __init__(self,values):self.values=values
    def tolist(self):return self.values


def test_actual_trainer_labels_cannot_silently_include_prompt_loss():
    rows=[{'input_ids':[1,2,3],'attention_mask':[1,1,1],'labels':[-100,-100,3]}]
    class Trainer:
        train_dataset=copy.deepcopy(rows)
        def data_collator(self,batch):return {'labels':[Values(batch[0]['labels']+[-100])]}
    trainer=Trainer();pilot.verify_labels(trainer,rows)
    trainer.train_dataset[0]['labels']=[1,2,3]
    with pytest.raises(ValueError,match='changed tokens'):pilot.verify_labels(trainer,rows)
    trainer.train_dataset=copy.deepcopy(rows)
    trainer.data_collator=lambda batch:{'labels':[Values(batch[0]['labels']+[0])]}
    with pytest.raises(ValueError,match='padding'):pilot.verify_labels(trainer,rows)


def test_import_and_default_do_not_load_weights(monkeypatch,capsys):
    monkeypatch.setattr('sys.argv',['train_qwen_pilot.py'])
    monkeypatch.setattr(pilot,'configure',lambda:pytest.fail('GPU setup in dry run'))
    assert pilot.main()==0
    result=json.loads(capsys.readouterr().out)
    assert result['training_started'] is False and result['production_dataset_ready'] is False
