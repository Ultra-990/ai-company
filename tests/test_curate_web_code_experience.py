from datetime import datetime, timezone
from hashlib import sha256
import json

import pytest

from scripts import curate_web_code_experience as curator
from scripts.prepare_training_data import validate_record
from scripts.training_family_registry import assert_evaluation_families_allowed, load_training_only_families


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    return path


@pytest.fixture
def artifacts(tmp_path,monkeypatch):
    workspace=tmp_path/'workspace';workspace.mkdir();monkeypatch.setattr(curator,'WORKSPACE',workspace)
    candidate = {'schema':'web-code-repair-candidate.v1',
        'family_id':'rowerownia-query-parser-development','split':'train_candidate',
        'status':'pending_independent_learning_review','brief':'Repair exact query parsing.',
        'incorrect_source':'def parse(query):\n    return broken(query)\n',
        'feedback':'Preserve blank values and reject duplicate fields.',
        'corrected_source':'def parse(query):\n    return strict(query)\n','model':'synthetic-model',
        'digest':'a'*64,'output_profile':'python-web-repair-v1','owner_accepted':False,
        'training_started':False,'ready_for_trainer':False}
    candidate_path=write(workspace/'candidate.json',candidate);candidate_sha=curator.digest(candidate_path)
    evidence={}
    for index,name in enumerate(sorted(curator.MANIFEST_EVIDENCE),1):
        proof=workspace/(name+'.json');proof.write_text(json.dumps({'synthetic':name}))
        evidence[name]={'path':str(proof),'sha256':curator.digest(proof)}
    manifest={'schema':'web-code-experience-review.v1','status':'pending_independent_learning_review',
        'reviewer':'system_review','family_id':candidate['family_id'],'split':'train_candidate',
        'sample_sha256':candidate_sha,'sample_file_sha256':candidate_sha,
        'evidence':evidence,'checks':{name:True for name in curator.MANIFEST_CHECKS},
        'heldout_inputs_in_sample':False,'owner_accepted':False,'accepted_for_training':False,
        'training_started':False,'ready_for_trainer':False}
    manifest_path=write(workspace/'manifest.json',manifest);manifest_sha=curator.digest(manifest_path)
    learning={'schema':'web-code-independent-learning-review.v1',
        'decision':'eligible_for_curated_training','reviewer':'independent_system_review',
        'created_at':datetime.now(timezone.utc).isoformat(),'candidate_sha256':candidate_sha,
        'review_manifest_sha256':manifest_sha,'family_id':candidate['family_id'],'split':'train_candidate',
        'quality_review':{name:'passed' for name in curator.QUALITY_FIELDS},
        'rationale':['Synthetic material is self-contained and independently evidenced.'],
        'curation_constraints':['Keep this family in training only.'],'owner_accepted':False,
        'training_permission_recorded_separately':True,'ready_for_trainer':False,
        'training_started':False}
    learning['quality_review']['heldout_transfer_separation']='passed_with_constraint'
    learning_path=write(workspace/'learning.json',learning)
    monkeypatch.setattr(curator,'collector_validate',lambda *paths:
        (candidate,{key:value for key,value in manifest.items() if key!='sample_file_sha256'}))
    return candidate_path,manifest_path,learning_path


def test_curator_emits_approved_repair_record_without_private_paths_or_probes(artifacts):
    row,receipt=curator.curate(*artifacts);validate_record(row)
    assert row['split']=='train' and row['review']['status']=='approved'
    user=json.loads(row['messages'][1]['content']);answer=json.loads(row['messages'][2]['content'])
    assert set(user)=={'brief','feedback','incorrect_source'}
    assert answer=={'changes':{'app.py':'def parse(query):\n    return strict(query)\n'}}
    messages=json.dumps(row['messages'])
    assert str(artifacts[0].parent) not in messages
    assert receipt['ready_for_trainer'] is receipt['training_started'] is False
    assert receipt['authorization']['owner_product_acceptance_asserted'] is False
    assert receipt['authorization']['clause']=='2026-10-10-development-and-training'
    assert receipt['dataset_gate']['export_ready'] is False
    assert receipt['dataset_gate']['counts']=={'train':1,'validation':0,'test':0}
    assert receipt['blocking_gates']==['dataset_manifest_not_built','unseen_transfer_holdout_not_reserved']


@pytest.mark.parametrize('target,field,value,match',[
    ('candidate','training_started',1,'candidate state'),
    ('manifest','accepted_for_training',True,'pending candidate'),
    ('learning','ready_for_trainer',True,'correctly bound'),
    ('learning','training_permission_recorded_separately','true','correctly bound'),
])
def test_boolean_types_and_pending_states_fail_closed(artifacts,target,field,value,match):
    path={'candidate':artifacts[0],'manifest':artifacts[1],'learning':artifacts[2]}[target]
    data=json.loads(path.read_text());data[field]=value;write(path,data)
    if target=='candidate':
        manifest=json.loads(artifacts[1].read_text());new=curator.digest(artifacts[0])
        manifest['sample_sha256']=manifest['sample_file_sha256']=new;write(artifacts[1],manifest)
        learning=json.loads(artifacts[2].read_text());learning['candidate_sha256']=new
        learning['review_manifest_sha256']=curator.digest(artifacts[1]);write(artifacts[2],learning)
    elif target=='manifest':
        learning=json.loads(artifacts[2].read_text());learning['review_manifest_sha256']=curator.digest(artifacts[1]);write(artifacts[2],learning)
    with pytest.raises(ValueError,match=match):curator.curate(*artifacts)


def test_each_of_three_artifact_hash_bindings_is_enforced(artifacts):
    learning=json.loads(artifacts[2].read_text());learning['candidate_sha256']='f'*64;write(artifacts[2],learning)
    with pytest.raises(ValueError,match='correctly bound'):curator.curate(*artifacts)


def test_manifest_requires_exact_checks_and_rehashes_real_evidence(artifacts):
    manifest=json.loads(artifacts[1].read_text());manifest['checks']={'foo':True};write(artifacts[1],manifest)
    learning=json.loads(artifacts[2].read_text());learning['review_manifest_sha256']=curator.digest(artifacts[1]);write(artifacts[2],learning)
    with pytest.raises(ValueError,match='pending candidate'):curator.curate(*artifacts)


def test_changed_or_missing_evidence_is_rejected_before_collector(artifacts):
    manifest=json.loads(artifacts[1].read_text());proof=next(iter(manifest['evidence'].values()))
    with open(proof['path'],'a',encoding='utf-8') as stream:stream.write('changed')
    with pytest.raises(ValueError,match='hash no longer matches'):curator.curate(*artifacts)


def test_bundle_write_is_new_and_receipt_hashes_exact_record(artifacts,tmp_path):
    row,receipt=curator.curate(*artifacts);out=artifacts[0].parent/'bundle';curator.write_bundle(out,row,receipt)
    raw=(out/'train-candidate.jsonl').read_bytes()
    assert sha256(raw).hexdigest()==receipt['record_sha256']
    with pytest.raises(FileExistsError):curator.write_bundle(out,row,receipt)


def test_main_inputs_must_be_regular_workspace_files_without_symlinks(artifacts):
    link=artifacts[0].parent/'candidate-link.json';link.symlink_to(artifacts[0])
    with pytest.raises(ValueError,match='Symlink curation input'):
        curator.curate(link,artifacts[1],artifacts[2])


def test_learning_review_cannot_assert_product_owner_acceptance(artifacts):
    learning=json.loads(artifacts[2].read_text());learning['owner_accepted']=True;write(artifacts[2],learning)
    with pytest.raises(ValueError,match='correctly bound'):curator.curate(*artifacts)


def test_specific_authorization_clause_is_required(artifacts,tmp_path,monkeypatch):
    fake=tmp_path/'AGENTS.md';fake.write_text('generic permission');monkeypatch.setattr(curator,'AUTHORIZATION',fake)
    with pytest.raises(ValueError,match='2026-10-10'):curator.curate(*artifacts)


def test_output_must_be_new_under_workspace_and_hash_checked_before_mkdir(artifacts,tmp_path):
    row,receipt=curator.curate(*artifacts);receipt['record_sha256']='f'*64
    outside=tmp_path/'outside'
    with pytest.raises(ValueError,match='does not bind'):curator.write_bundle(outside,row,receipt)
    assert not outside.exists()
    row,receipt=curator.curate(*artifacts)
    with pytest.raises(ValueError,match='Linux workspace'):curator.write_bundle(outside,row,receipt)


def test_training_only_registry_blocks_eval_and_allows_unrelated_family():
    assert 'rowerownia-query-parser-development' in load_training_only_families()
    assert assert_evaluation_families_allowed([{'family':'fresh-transfer-family'}]) is True
    with pytest.raises(ValueError,match='training-only'):
        assert_evaluation_families_allowed([{'family':'rowerownia-query-parser-development'}])
    for invalid in (None,'family',{'family':'fresh-transfer-family'}):
        with pytest.raises(ValueError,match='sequence'):
            assert_evaluation_families_allowed(invalid)
