"""Curate one independently reviewed, self-contained two-file web UI repair."""
import argparse
from datetime import date,datetime
from hashlib import sha256
import json
from pathlib import Path
import re
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.collect_web_ui_experience import validate as collector_validate
from scripts.curate_web_code_experience import (AUTHORIZATION,AUTHORIZATION_MARKER,MAX_ARTIFACT_BYTES,
    authorization_state)
from scripts.prepare_training_data import VERSION,validate_dataset,validate_record
from scripts.training_family_registry import load_training_only_families

FAMILY='service-crema-responsive-nav-copy-development'
WORKSPACE=Path('/home/marcin/ai-company-workspaces')
CANDIDATE_FIELDS={'schema','family_id','split','status','title','brief','completion_criterion','feedback',
    'incorrect_sources','preserved_sources','corrected_changes','changed_files','preserved_sha256',
    'model','digest','output_profile','owner_accepted','training_started','ready_for_trainer'}
MANIFEST_FIELDS={'schema','status','reviewer','family_id','split','sample_sha256','evidence','checks',
    'heldout_inputs_in_sample','owner_accepted','accepted_for_training','training_started',
    'ready_for_trainer','sample_file_sha256'}
EVIDENCE_FIELDS={'repair_report','before_browser','after_browser','technical_assessment','base_report',
    'raw_request','raw_response','model_authorship'}
CHECK_FIELDS={'raw_two_file_change_exact','four_files_preserved','frozen_7_tests_19_probes',
    'before_browser_failure_bound','after_browser_15_passed','technical_and_screenshots_reviewed'}
LEARNING_FIELDS={'schema','decision','reviewer','created_at','candidate_sha256','review_manifest_sha256',
    'family_id','split','quality_review','rationale','curation_constraints','owner_accepted',
    'training_permission_recorded_separately','ready_for_trainer','training_started'}
QUALITY_FIELDS={'task_feedback_target_alignment','no_test_or_contract_weakening',
    'full_six_file_self_contained_context','raw_model_authorship_and_exact_target_integrity',
    'technical_and_browser_evidence_integrity','synthetic_public_data_review',
    'hidden_examiner_input_exclusion','heldout_transfer_separation'}
INDEPENDENT_PROOFS=('repair_report','before_browser','after_browser','technical_assessment')


def digest(path):return sha256(Path(path).read_bytes()).hexdigest()


def exact_bool(value,expected):return type(value) is bool and value is expected


def checked_input(path):
    path=Path(path)
    if any(item.is_symlink() for item in (path,*path.parents)):
        raise ValueError('Symlink curation input is not allowed')
    resolved=path.resolve(strict=True);root=WORKSPACE.resolve(strict=True)
    if not resolved.is_relative_to(root) or not resolved.is_file():
        raise ValueError('Curation input must be a regular file in Linux workspace')
    return resolved


def checked_evidence(path):
    path=Path(path)
    if any(item.is_symlink() for item in (path,*path.parents)):raise ValueError('Symlink evidence is not allowed')
    resolved=path.resolve(strict=True);root=WORKSPACE.resolve(strict=True)
    if not resolved.is_relative_to(root) or not resolved.is_file():
        raise ValueError('Evidence must be a regular workspace file')
    return resolved


def snapshot(path):
    def unique(pairs):
        out={}
        for key,value in pairs:
            if key in out:raise ValueError('Duplicate JSON key')
            out[key]=value
        return out
    path=checked_input(path);raw=path.read_bytes()
    if len(raw)>MAX_ARTIFACT_BYTES:raise ValueError('Artifact exceeds offline curation limit')
    try:value=json.loads(raw.decode('utf-8'),object_pairs_hook=unique)
    except UnicodeError:raise ValueError('Artifact must be UTF-8 JSON') from None
    return value,sha256(raw).hexdigest(),raw


def validate_artifacts(candidate_path,manifest_path,learning_path):
    candidate,candidate_sha,candidate_raw=snapshot(candidate_path)
    manifest,manifest_sha,manifest_raw=snapshot(manifest_path)
    learning,learning_sha,learning_raw=snapshot(learning_path)
    if (not isinstance(candidate,dict) or set(candidate)!=CANDIDATE_FIELDS
            or candidate.get('schema')!='web-code-repair-candidate.v2' or candidate.get('family_id')!=FAMILY
            or candidate.get('split')!='train_candidate'
            or candidate.get('status')!='pending_independent_learning_review'
            or candidate.get('output_profile')!='python-web-repair-v1'
            or candidate.get('changed_files')!=['index.html','style.css']
            or set(candidate.get('incorrect_sources',{}))!={'index.html','style.css'}
            or set(candidate.get('corrected_changes',{}))!={'index.html','style.css'}
            or set(candidate.get('preserved_sources',{}))!={'README.md','app.js','app.py','test_app.py'}
            or set(candidate.get('preserved_sha256',{}))!=set(candidate['preserved_sources'])
            or any(not isinstance(candidate.get(k),str) or not candidate[k].strip()
                   for k in ('title','brief','completion_criterion','feedback','model'))
            or not re.fullmatch(r'[a-f0-9]{64}',candidate.get('digest',''))
            or any(sha256(v.encode()).hexdigest()!=candidate['preserved_sha256'].get(k)
                   for k,v in candidate['preserved_sources'].items())
            or not exact_bool(candidate.get('owner_accepted'),False)
            or not exact_bool(candidate.get('training_started'),False)
            or not exact_bool(candidate.get('ready_for_trainer'),False)):
        raise ValueError('Invalid web UI candidate state')
    if (not isinstance(manifest,dict) or set(manifest)!=MANIFEST_FIELDS
            or manifest.get('schema')!='web-code-ui-experience-review.v2'
            or manifest.get('status')!='pending_independent_learning_review'
            or manifest.get('reviewer')!='system_review' or manifest.get('family_id')!=FAMILY
            or manifest.get('split')!='train_candidate' or manifest.get('sample_sha256')!=candidate_sha
            or manifest.get('sample_file_sha256')!=candidate_sha
            or set(manifest.get('checks',{}))!=CHECK_FIELDS
            or not all(exact_bool(v,True) for v in manifest['checks'].values())
            or set(manifest.get('evidence',{}))!=EVIDENCE_FIELDS
            or not exact_bool(manifest.get('heldout_inputs_in_sample'),False)
            or not exact_bool(manifest.get('owner_accepted'),False)
            or not exact_bool(manifest.get('accepted_for_training'),False)
            or not exact_bool(manifest.get('training_started'),False)
            or not exact_bool(manifest.get('ready_for_trainer'),False)):
        raise ValueError('Invalid web UI evidence manifest')
    evidence={}
    for name,proof in manifest['evidence'].items():
        if (not isinstance(proof,dict) or set(proof)!={'path','sha256'}
                or not re.fullmatch(r'[a-f0-9]{64}',proof.get('sha256',''))):
            raise ValueError('Invalid evidence proof')
        path=checked_evidence(proof.get('path'));raw=path.read_bytes()
        if len(raw)>MAX_ARTIFACT_BYTES or sha256(raw).hexdigest()!=proof['sha256']:
            raise ValueError('Evidence hash no longer matches manifest')
        evidence[path]=raw
    if (not isinstance(learning,dict) or set(learning)!=LEARNING_FIELDS
            or learning.get('schema')!='web-code-independent-learning-review.v1'
            or learning.get('decision')!='eligible_for_curated_training'
            or learning.get('reviewer')!='independent_system_review'
            or learning.get('candidate_sha256')!=candidate_sha
            or learning.get('review_manifest_sha256')!=manifest_sha
            or learning.get('family_id')!=FAMILY or learning.get('split')!='train_candidate'
            or set(learning.get('quality_review',{}))!=QUALITY_FIELDS
            or any(v not in ('passed','passed_with_constraint') for v in learning['quality_review'].values())
            or not isinstance(learning.get('rationale'),list) or not learning['rationale']
            or not all(isinstance(v,str) and v.strip() for v in learning['rationale'])
            or not isinstance(learning.get('curation_constraints'),list) or not learning['curation_constraints']
            or not all(isinstance(v,str) and v.strip() for v in learning['curation_constraints'])
            or not exact_bool(learning.get('owner_accepted'),False)
            or not exact_bool(learning.get('training_permission_recorded_separately'),True)
            or not exact_bool(learning.get('ready_for_trainer'),False)
            or not exact_bool(learning.get('training_started'),False)):
        raise ValueError('Independent UI review is not eligible and correctly bound')
    try:reviewed=datetime.fromisoformat(learning['created_at']).date()
    except (TypeError,ValueError):raise ValueError('Invalid independent review timestamp') from None
    if reviewed>date.today():raise ValueError('Independent review timestamp is in the future')
    if FAMILY not in load_training_only_families():raise ValueError('Candidate family is not training-only')
    regenerated_candidate,regenerated_manifest=collector_validate(
        *(manifest['evidence'][name]['path'] for name in INDEPENDENT_PROOFS))
    regenerated_manifest=regenerated_manifest|{'sample_file_sha256':candidate_sha}
    if regenerated_candidate!=candidate or regenerated_manifest!=manifest:
        raise ValueError('Collector revalidation does not reproduce UI candidate and manifest')
    if (Path(candidate_path).read_bytes()!=candidate_raw or Path(manifest_path).read_bytes()!=manifest_raw
            or Path(learning_path).read_bytes()!=learning_raw
            or any(path.read_bytes()!=raw for path,raw in evidence.items())):
        raise ValueError('Curation inputs changed during validation')
    return candidate,manifest,learning,(candidate_sha,manifest_sha,learning_sha),reviewed


def curate(candidate_path,manifest_path,learning_path):
    candidate,manifest,learning,hashes,reviewed=validate_artifacts(candidate_path,manifest_path,learning_path)
    candidate_sha,manifest_sha,learning_sha=hashes
    before=candidate['preserved_sources']|candidate['incorrect_sources']
    user=json.dumps({'title':candidate['title'],'brief':candidate['brief'],
        'completion_criterion':candidate['completion_criterion'],'feedback':candidate['feedback'],
        'files':before},ensure_ascii=False,sort_keys=True,separators=(',',':'))
    assistant=json.dumps({'changes':candidate['corrected_changes']},ensure_ascii=False,
        sort_keys=True,separators=(',',':'))
    evidence=[{'kind':'independent_test','reference':'sha256:'+manifest['evidence'][name]['sha256']+'#'+name,
        'sha256':manifest['evidence'][name]['sha256']} for name in INDEPENDENT_PROOFS]
    evidence.append({'kind':'content_review','reference':'sha256:'+learning_sha+'#independent-learning-review',
        'sha256':learning_sha})
    row={'version':VERSION,'id':'web-ui-'+candidate_sha[:20],'family':FAMILY,'split':'train','skill':'repair',
        'source':{'kind':'synthetic','reference':'sha256:'+candidate_sha,
            'rights':'Project-owned synthetic development example; approved for local model curation.',
            'privacy_checked':True},
        'messages':[{'role':'system','content':('Repair the supplied six-file Python web application. '
            'Return only strict JSON with a changes object containing the complete corrected files named by the feedback.')},
            {'role':'user','content':user},{'role':'assistant','content':assistant}],
        'review':{'status':'approved','reviewer':'independent_system_review+system_curation',
            'reviewed_on':reviewed.isoformat(),'evidence':evidence,
            'note':'Training partition only; dataset and unseen transfer holdout gates remain pending.'}}
    validate_record(row);payload=(json.dumps(row,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n').encode()
    _,gate=validate_dataset(payload)
    receipt={'schema':'web-ui-curation-receipt.v2','candidate_sha256':candidate_sha,
        'review_manifest_sha256':manifest_sha,'learning_review_sha256':learning_sha,
        'record_sha256':sha256(payload).hexdigest(),'family_id':FAMILY,'split':'train',
        'review_status':'approved','authorization':authorization_state(),
        'dataset_gate':{'counts':gate['counts'],'export_ready':gate['export_ready'],
            'blocking_reasons':gate['blocking_reasons']},'ready_for_trainer':False,'training_started':False,
        'blocking_gates':['dataset_manifest_not_built','unseen_transfer_holdout_not_reserved']}
    return row,receipt


def write_bundle(output,row,receipt):
    output=Path(output);payload=json.dumps(row,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n'
    if sha256(payload.encode()).hexdigest()!=receipt.get('record_sha256'):
        raise ValueError('Receipt does not bind emitted record')
    _,gate=validate_dataset(payload.encode())
    if receipt.get('dataset_gate')!={'counts':gate['counts'],'export_ready':gate['export_ready'],
            'blocking_reasons':gate['blocking_reasons']}:
        raise ValueError('Receipt does not bind dataset gate')
    if output.exists():raise FileExistsError(str(output))
    if any(path.is_symlink() for path in output.parents):raise ValueError('Symlink output parent is not allowed')
    if not output.parent.resolve(strict=True).is_relative_to(WORKSPACE.resolve(strict=True)):
        raise ValueError('Output must remain in Linux workspace')
    output.mkdir(mode=0o700,parents=False)
    record_path=output/'train-candidate.jsonl';receipt_path=output/'curation-receipt.json'
    record_path.write_text(payload,encoding='utf-8');receipt_path.write_text(
        json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
    record_path.chmod(0o600);receipt_path.chmod(0o600)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('candidate',type=Path);parser.add_argument('review_manifest',type=Path)
    parser.add_argument('learning_review',type=Path);parser.add_argument('--output-dir',type=Path)
    args=parser.parse_args();row,receipt=curate(args.candidate,args.review_manifest,args.learning_review)
    if args.output_dir:write_bundle(args.output_dir,row,receipt)
    print(json.dumps({'validated':True,'written':bool(args.output_dir),'family':row['family'],
        'review_status':'approved','ready_for_trainer':False,'training_started':False}))
    return 0


if __name__=='__main__':raise SystemExit(main())
