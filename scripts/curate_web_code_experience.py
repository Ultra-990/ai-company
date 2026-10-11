"""Convert one independently approved web-code experience into a reviewed train candidate."""
import argparse
from datetime import date, datetime
from hashlib import sha256
import json
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.prepare_training_data import VERSION, validate_record, validate_dataset
from scripts.training_family_registry import load_training_only_families
from scripts.collect_web_code_experience import validate as collector_validate

REPO = Path(__file__).resolve().parents[1]
AUTHORIZATION = REPO / 'AGENTS.md'
WORKSPACE = Path('/home/marcin/ai-company-workspaces')
MAX_ARTIFACT_BYTES = 16 * 1024 * 1024
AUTHORIZATION_MARKER = ("## Zgoda na rozwój i trening po naprawie GPU — 2026-10-10\n\n"
    "- Właściciel jawnie polecił dalszą rozbudowę całości AI Company oraz zezwolił\n"
    "  na trening modelu.")
CANDIDATE_FIELDS = {'schema','family_id','split','status','brief','incorrect_source','feedback',
    'corrected_source','model','digest','output_profile','owner_accepted','training_started','ready_for_trainer'}
MANIFEST_FIELDS = {'schema','status','reviewer','family_id','split','sample_sha256','evidence','checks',
    'heldout_inputs_in_sample','owner_accepted','accepted_for_training','training_started',
    'ready_for_trainer','sample_file_sha256'}
LEARNING_FIELDS = {'schema','decision','reviewer','created_at','candidate_sha256','review_manifest_sha256',
    'family_id','split','quality_review','rationale','curation_constraints','owner_accepted',
    'training_permission_recorded_separately','ready_for_trainer','training_started'}
QUALITY_FIELDS = {'task_feedback_target_alignment','no_test_or_contract_weakening',
    'self_contained_with_incorrect_source','raw_model_authorship_and_evidence_integrity',
    'synthetic_and_private_data_review','heldout_transfer_separation'}
INDEPENDENT_PROOFS = ('repair_report','failing_edge_report','passing_edge_report','browser_report')
MANIFEST_CHECKS = {'raw_model_change_exact','only_app_changed','model_tests_preserved',
    'frontend_preserved','failing_edge_bound','passing_edge_bound','duplicate_diagnostic_passed',
    'browser_checks_passed'}
MANIFEST_EVIDENCE = {'repair_report','failing_edge_report','passing_edge_report','browser_report',
    'base_report','raw_request','raw_response','model_authorship'}


def digest(path): return sha256(Path(path).read_bytes()).hexdigest()


def checked_input(path):
    path=Path(path)
    if any(item.is_symlink() for item in (path,*path.parents)):
        raise ValueError('Symlink curation input is not allowed')
    resolved=path.resolve(strict=True);root=WORKSPACE.resolve(strict=True)
    if not resolved.is_relative_to(root) or not resolved.is_file():
        raise ValueError('Curation input must be a regular file in Linux workspace')
    return resolved


def snapshot(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result: raise ValueError('Duplicate JSON key')
            result[key] = value
        return result
    path=checked_input(path);raw=path.read_bytes()
    if len(raw)>MAX_ARTIFACT_BYTES:raise ValueError('Artifact exceeds offline curation limit')
    try:value=json.loads(raw.decode('utf-8'), object_pairs_hook=unique)
    except UnicodeError:raise ValueError('Artifact must be UTF-8 JSON') from None
    return value,sha256(raw).hexdigest(),raw


def checked_evidence(path):
    path=Path(path)
    if any(item.is_symlink() for item in (path,*path.parents)):
        raise ValueError('Symlink evidence is not allowed')
    resolved=path.resolve(strict=True);root=WORKSPACE.resolve(strict=True)
    if not resolved.is_relative_to(root):raise ValueError('Evidence must remain in Linux workspace')
    return resolved


def exact_bool(value, expected): return type(value) is bool and value is expected


def authorization_state():
    raw=AUTHORIZATION.read_bytes()
    marker=AUTHORIZATION_MARKER.encode()
    if marker not in raw:
        raise ValueError('Pinned 2026-10-10 training authorization clause is missing')
    return {'kind':'repository_owner_training_authorization','reference':'AGENTS.md',
            'sha256':sha256(raw).hexdigest(),'clause':'2026-10-10-development-and-training',
            'clause_sha256':sha256(marker).hexdigest(),'owner_product_acceptance_asserted':False}


def validate_artifacts(candidate_path, manifest_path, learning_path):
    candidate,candidate_sha,candidate_raw=snapshot(candidate_path)
    manifest,manifest_sha,manifest_raw=snapshot(manifest_path)
    learning,learning_sha,learning_raw=snapshot(learning_path)
    if not isinstance(candidate, dict) or set(candidate) != CANDIDATE_FIELDS:
        raise ValueError('Invalid web-code candidate fields')
    if (candidate['schema'] != 'web-code-repair-candidate.v1'
            or candidate['split'] != 'train_candidate'
            or candidate['status'] != 'pending_independent_learning_review'
            or candidate['output_profile'] != 'python-web-repair-v1'
            or not isinstance(candidate['family_id'],str)
            or not re.fullmatch(r'[a-z0-9][a-z0-9._-]{0,99}', candidate['family_id'])
            or any(not isinstance(candidate[key], str) or not candidate[key].strip()
                   for key in ('brief','incorrect_source','feedback','corrected_source','model'))
            or not isinstance(candidate['digest'],str)
            or not re.fullmatch(r'[a-f0-9]{64}', candidate['digest'])
            or not exact_bool(candidate['training_started'], False)
            or not exact_bool(candidate['ready_for_trainer'], False)
            or type(candidate['owner_accepted']) is not bool):
        raise ValueError('Invalid web-code candidate state')
    if not isinstance(manifest, dict) or set(manifest) != MANIFEST_FIELDS:
        raise ValueError('Invalid evidence manifest fields')
    if (manifest['schema'] != 'web-code-experience-review.v1'
            or manifest['status'] != 'pending_independent_learning_review'
            or manifest['family_id'] != candidate['family_id'] or manifest['split'] != candidate['split']
            or manifest['sample_sha256'] != candidate_sha or manifest['sample_file_sha256'] != candidate_sha
            or manifest['reviewer']!='system_review'
            or not isinstance(manifest['checks'], dict) or set(manifest['checks'])!=MANIFEST_CHECKS
            or not all(exact_bool(value, True) for value in manifest['checks'].values())
            or not isinstance(manifest['evidence'], dict) or set(manifest['evidence'])!=MANIFEST_EVIDENCE
            or not exact_bool(manifest['heldout_inputs_in_sample'], False)
            or not exact_bool(manifest['accepted_for_training'], False)
            or not exact_bool(manifest['training_started'], False)
            or not exact_bool(manifest['ready_for_trainer'], False)
            or type(manifest['owner_accepted']) is not bool):
        raise ValueError('Evidence manifest does not bind a pending candidate')
    evidence_snapshots={}
    for proof in manifest['evidence'].values():
        if (not isinstance(proof, dict) or set(proof) != {'path','sha256'}
                or not isinstance(proof['path'], str) or not proof['path']
                or not isinstance(proof['sha256'], str) or not re.fullmatch(r'[a-f0-9]{64}', proof['sha256'])):
            raise ValueError('Invalid evidence manifest proof')
        proof_path=checked_evidence(proof['path'])
        raw=proof_path.read_bytes()
        if len(raw)>MAX_ARTIFACT_BYTES:
            raise ValueError('Evidence exceeds offline curation limit')
        if sha256(raw).hexdigest()!=proof['sha256']:
            raise ValueError('Evidence hash no longer matches manifest')
        evidence_snapshots[proof_path]=raw
    if not isinstance(learning, dict) or set(learning) != LEARNING_FIELDS:
        raise ValueError('Invalid independent learning review fields')
    if (learning['schema'] != 'web-code-independent-learning-review.v1'
            or learning['decision'] != 'eligible_for_curated_training'
            or learning['reviewer'] != 'independent_system_review'
            or learning['candidate_sha256'] != candidate_sha
            or learning['review_manifest_sha256'] != manifest_sha
            or learning['family_id'] != candidate['family_id'] or learning['split'] != candidate['split']
            or not isinstance(learning['quality_review'],dict)
            or set(learning['quality_review']) != QUALITY_FIELDS
            or any(value not in ('passed','passed_with_constraint') for value in learning['quality_review'].values())
            or not isinstance(learning['rationale'], list) or not learning['rationale']
            or not all(isinstance(value, str) and value.strip() for value in learning['rationale'])
            or not isinstance(learning['curation_constraints'], list) or not learning['curation_constraints']
            or not all(isinstance(value, str) and value.strip() for value in learning['curation_constraints'])
            or type(learning['owner_accepted']) is not bool
            or not exact_bool(learning['training_permission_recorded_separately'], True)
            or not exact_bool(learning['owner_accepted'], False)
            or not exact_bool(learning['ready_for_trainer'], False)
            or not exact_bool(learning['training_started'], False)):
        raise ValueError('Independent review is not eligible and correctly bound')
    try:
        reviewed = datetime.fromisoformat(learning['created_at']).date()
    except (TypeError, ValueError):
        raise ValueError('Invalid independent review timestamp') from None
    if reviewed > date.today(): raise ValueError('Independent review timestamp is in the future')
    if candidate['family_id'] not in load_training_only_families():
        raise ValueError('Candidate family is not reserved as training-only')
    regenerated_candidate,regenerated_manifest=collector_validate(
        manifest['evidence']['repair_report']['path'],manifest['evidence']['failing_edge_report']['path'],
        manifest['evidence']['passing_edge_report']['path'],manifest['evidence']['browser_report']['path'])
    regenerated_manifest=regenerated_manifest|{'sample_file_sha256':candidate_sha}
    if regenerated_candidate!=candidate or regenerated_manifest!=manifest:
        raise ValueError('Collector revalidation does not reproduce candidate and manifest')
    # Detect replacement during validation; snapshots above remain the parsed authority.
    if (Path(candidate_path).read_bytes()!=candidate_raw or Path(manifest_path).read_bytes()!=manifest_raw
            or Path(learning_path).read_bytes()!=learning_raw
            or any(path.read_bytes()!=raw for path,raw in evidence_snapshots.items())):
        raise ValueError('Curation inputs changed during validation')
    return candidate, manifest, learning, (candidate_sha, manifest_sha, learning_sha), reviewed


def curate(candidate_path, manifest_path, learning_path):
    candidate, manifest, learning, hashes, reviewed = validate_artifacts(
        candidate_path, manifest_path, learning_path)
    candidate_sha, manifest_sha, learning_sha = hashes
    user = json.dumps({'brief': candidate['brief'], 'feedback': candidate['feedback'],
                       'incorrect_source': candidate['incorrect_source']},
                      ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    assistant = json.dumps({'changes': {'app.py': candidate['corrected_source']}},
                           ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    evidence = [{'kind':'independent_test','reference':'sha256:'+manifest['evidence'][name]['sha256']+'#'+name,
                 'sha256':manifest['evidence'][name]['sha256']} for name in INDEPENDENT_PROOFS]
    evidence.append({'kind':'content_review','reference':'sha256:'+learning_sha+'#independent-learning-review',
                     'sha256':learning_sha})
    row = {'version':VERSION,'id':'web-code-'+candidate_sha[:20],
        'family':candidate['family_id'],'split':'train','skill':'repair',
        'source':{'kind':'synthetic','reference':'sha256:'+candidate_sha,
                  'rights':'Project-owned synthetic development example; approved for local model curation.',
                  'privacy_checked':True},
        'messages':[
            {'role':'system','content':('Repair the supplied Python web application. Return only strict JSON '
                '{"changes":{"app.py":"complete corrected source"}} and preserve the stated contract.')},
            {'role':'user','content':user},{'role':'assistant','content':assistant}],
        'review':{'status':'approved','reviewer':'independent_system_review+system_curation',
                  'reviewed_on':reviewed.isoformat(),'evidence':evidence,
                  'note':('Eligible for the training partition only. Family is reserved from evaluation; '
                          'dataset and unseen transfer holdout gates remain pending.')}}
    validate_record(row)
    payload=(json.dumps(row,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n').encode()
    _,gate=validate_dataset(payload)
    receipt = {'schema':'web-code-curation-receipt.v1','candidate_sha256':candidate_sha,
        'review_manifest_sha256':manifest_sha,'learning_review_sha256':learning_sha,
        'record_sha256':sha256(payload).hexdigest(),
        'family_id':candidate['family_id'],'split':'train','review_status':'approved',
        'authorization':authorization_state(),
        'dataset_gate':{'counts':gate['counts'],'export_ready':gate['export_ready'],
                        'blocking_reasons':gate['blocking_reasons']},
        'ready_for_trainer':False,'training_started':False,
        'blocking_gates':['dataset_manifest_not_built','unseen_transfer_holdout_not_reserved']}
    return row, receipt


def write_bundle(output, row, receipt):
    output = Path(output)
    payload=json.dumps(row,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n'
    if sha256(payload.encode()).hexdigest()!=receipt['record_sha256']:
        raise ValueError('Curation receipt does not bind the emitted record')
    _,gate=validate_dataset(payload.encode())
    expected={'counts':gate['counts'],'export_ready':gate['export_ready'],
              'blocking_reasons':gate['blocking_reasons']}
    if receipt.get('dataset_gate')!=expected:
        raise ValueError('Curation receipt does not bind the dataset gate')
    if output.exists():raise FileExistsError(str(output))
    if any(item.is_symlink() for item in output.parents):
        raise ValueError('Symlink output parent is not allowed')
    parent=output.parent.resolve(strict=True);root=WORKSPACE.resolve(strict=True)
    if not parent.is_relative_to(root):raise ValueError('Output must remain in Linux workspace')
    output.mkdir(mode=0o700, parents=False, exist_ok=False)
    (output/'train-candidate.jsonl').write_text(payload,encoding='utf-8')
    (output/'curation-receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('candidate',type=Path);parser.add_argument('review_manifest',type=Path)
    parser.add_argument('learning_review',type=Path);parser.add_argument('--output-dir',type=Path)
    args=parser.parse_args();row,receipt=curate(args.candidate,args.review_manifest,args.learning_review)
    if args.output_dir: write_bundle(args.output_dir,row,receipt)
    print(json.dumps({'validated':True,'written':bool(args.output_dir),'family':row['family'],
        'review_status':'approved','ready_for_trainer':False,'training_started':False}))
    return 0


if __name__=='__main__': raise SystemExit(main())
