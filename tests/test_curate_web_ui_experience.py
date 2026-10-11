from datetime import datetime,timezone
from hashlib import sha256
import json

import pytest

from scripts import curate_web_ui_experience as curator
from scripts.prepare_training_data import validate_record


def write(path,value):
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8');return path


@pytest.fixture
def artifacts(tmp_path,monkeypatch):
    workspace=tmp_path/'workspace';workspace.mkdir();monkeypatch.setattr(curator,'WORKSPACE',workspace)
    before={'index.html':'<html>old</html>','style.css':'nav{top:100%}',
        'app.js':'toggle.classList.toggle("open")','app.py':'server','test_app.py':'tests','README.md':'run'}
    candidate={'schema':'web-code-repair-candidate.v2','family_id':curator.FAMILY,
        'split':'train_candidate','status':'pending_independent_learning_review','title':'CREMA UI',
        'brief':'Correct Restore copy and preserve the existing menu toggle.','completion_criterion':'Menu links render in viewport.',
        'feedback':'Change exactly index.html and style.css; preserve the other four files.',
        'incorrect_sources':{k:before[k] for k in ('index.html','style.css')},
        'preserved_sources':{k:before[k] for k in ('README.md','app.js','app.py','test_app.py')},
        'corrected_changes':{'index.html':'<html>Regeneracja</html>','style.css':'header{position:relative}'},
        'changed_files':['index.html','style.css'],
        'preserved_sha256':{k:sha256(before[k].encode()).hexdigest() for k in ('README.md','app.js','app.py','test_app.py')},
        'model':'fixture','digest':'a'*64,'output_profile':'python-web-repair-v1',
        'owner_accepted':False,'training_started':False,'ready_for_trainer':False}
    candidate_path=write(workspace/'candidate.json',candidate);candidate_sha=curator.digest(candidate_path)
    evidence={}
    for name in curator.EVIDENCE_FIELDS:
        path=write(workspace/(name+'.json'),{'proof':name})
        evidence[name]={'path':str(path),'sha256':curator.digest(path)}
    manifest={'schema':'web-code-ui-experience-review.v2','status':'pending_independent_learning_review',
        'reviewer':'system_review','family_id':curator.FAMILY,'split':'train_candidate',
        'sample_sha256':candidate_sha,'sample_file_sha256':candidate_sha,'evidence':evidence,
        'checks':{name:True for name in curator.CHECK_FIELDS},'heldout_inputs_in_sample':False,
        'owner_accepted':False,'accepted_for_training':False,'training_started':False,'ready_for_trainer':False}
    manifest_path=write(workspace/'manifest.json',manifest);manifest_sha=curator.digest(manifest_path)
    learning={'schema':'web-code-independent-learning-review.v1','decision':'eligible_for_curated_training',
        'reviewer':'independent_system_review','created_at':datetime.now(timezone.utc).isoformat(),
        'candidate_sha256':candidate_sha,'review_manifest_sha256':manifest_sha,'family_id':curator.FAMILY,
        'split':'train_candidate','quality_review':{name:'passed' for name in curator.QUALITY_FIELDS},
        'rationale':['Complete synthetic joint repair.'],'curation_constraints':['Training-only family.'],
        'owner_accepted':False,'training_permission_recorded_separately':True,
        'ready_for_trainer':False,'training_started':False}
    learning['quality_review']['heldout_transfer_separation']='passed_with_constraint'
    learning_path=write(workspace/'learning.json',learning)
    monkeypatch.setattr(curator,'collector_validate',lambda *paths:
        (candidate,{k:v for k,v in manifest.items() if k!='sample_file_sha256'}))
    return candidate_path,manifest_path,learning_path


def test_curates_full_six_file_context_and_exact_two_file_target(artifacts):
    row,receipt=curator.curate(*artifacts);validate_record(row)
    user=json.loads(row['messages'][1]['content']);answer=json.loads(row['messages'][2]['content'])
    assert set(user['files'])=={'app.py','test_app.py','index.html','style.css','app.js','README.md'}
    assert user['files']['app.js']=='toggle.classList.toggle("open")'
    assert set(answer['changes'])=={'index.html','style.css'}
    assert receipt['dataset_gate']['counts']=={'train':1,'validation':0,'test':0}
    assert receipt['dataset_gate']['export_ready'] is False
    assert receipt['dataset_gate']['blocking_reasons']==[
        'insufficient_train','insufficient_validation','insufficient_test']
    assert receipt['ready_for_trainer'] is receipt['training_started'] is False
    assert str(artifacts[0].parent) not in json.dumps(row['messages'])


@pytest.mark.parametrize('target,field,value,match',[
    ('candidate','owner_accepted',True,'candidate state'),
    ('manifest','accepted_for_training',True,'evidence manifest'),
    ('learning','ready_for_trainer',True,'correctly bound')])
def test_pending_boolean_states_fail_closed(artifacts,target,field,value,match):
    path=dict(candidate=artifacts[0],manifest=artifacts[1],learning=artifacts[2])[target]
    data=json.loads(path.read_text());data[field]=value;write(path,data)
    if target=='candidate':
        manifest=json.loads(artifacts[1].read_text());new=curator.digest(path)
        manifest['sample_sha256']=manifest['sample_file_sha256']=new;write(artifacts[1],manifest)
        learning=json.loads(artifacts[2].read_text());learning['candidate_sha256']=new
        learning['review_manifest_sha256']=curator.digest(artifacts[1]);write(artifacts[2],learning)
    elif target=='manifest':
        learning=json.loads(artifacts[2].read_text());learning['review_manifest_sha256']=curator.digest(path);write(artifacts[2],learning)
    with pytest.raises(ValueError,match=match):curator.curate(*artifacts)


def test_tampered_evidence_and_preserved_hash_fail_closed(artifacts):
    manifest=json.loads(artifacts[1].read_text());proof=manifest['evidence']['raw_response']
    with open(proof['path'],'a',encoding='utf-8') as stream:stream.write('tamper')
    with pytest.raises(ValueError,match='hash no longer matches'):curator.curate(*artifacts)


def test_preserved_source_hash_is_required(artifacts):
    candidate=json.loads(artifacts[0].read_text());candidate['preserved_sources']['app.js']='changed';write(artifacts[0],candidate)
    manifest=json.loads(artifacts[1].read_text());new=curator.digest(artifacts[0]);manifest['sample_sha256']=manifest['sample_file_sha256']=new;write(artifacts[1],manifest)
    learning=json.loads(artifacts[2].read_text());learning['candidate_sha256']=new;learning['review_manifest_sha256']=curator.digest(artifacts[1]);write(artifacts[2],learning)
    with pytest.raises(ValueError,match='candidate state'):curator.curate(*artifacts)


def test_bundle_is_private_new_and_immutable(artifacts):
    row,receipt=curator.curate(*artifacts);out=artifacts[0].parent/'curated'
    curator.write_bundle(out,row,receipt)
    assert out.stat().st_mode & 0o777==0o700
    assert all(path.stat().st_mode & 0o777==0o600 for path in out.iterdir())
    assert sha256((out/'train-candidate.jsonl').read_bytes()).hexdigest()==receipt['record_sha256']
    with pytest.raises(FileExistsError):curator.write_bundle(out,row,receipt)
