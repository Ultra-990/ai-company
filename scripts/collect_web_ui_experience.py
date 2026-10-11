"""Validate one independently evidenced two-file CREMA UI repair candidate."""
from hashlib import sha256
import argparse
import json
from pathlib import Path
import re
import sys
import tempfile

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.services.application_profile import REPAIR_PROFILE,REPAIR_SCHEMA,parse_sources
from app.services.application_profile import EXPORTED_TASK_PREFIX
from app.services.package_runner import ISOLATION_KEYS
from app.services.workspace_packages import canonical_json

WORKSPACE=Path('/home/marcin/ai-company-workspaces')
FAMILY='service-crema-responsive-nav-copy-development'
CHANGED=('index.html','style.css')
PRESERVED=('README.md','app.js','app.py','test_app.py')
PACKET_FIELDS={'task_id','project_id','department_id','role','task_context',
    'accepted_predecessor','revision'}
TASK_CONTEXT_FIELDS={'title','brief','completion_criterion'}
REVISION_FIELDS={'previous_attempt_id','rejected_result','rejected_checksum','rejection_reason'}
CHECKS=('required-content','labelled-fields','desktop-no-overflow','navigation',
    'quote-check-2-False','quote-restore-1-True','quote-restore-6-True','faq-opens',
    'mobile-no-overflow','mobile-menu-closed','mobile-menu-open','mobile-menu-links-in-viewport',
    'mobile-escape','mobile-escape-hides-links','file-mode-safe')
REQUESTS={'/api/quote?plan=check&machines=2&onsite=0',
    '/api/quote?plan=restore&machines=1&onsite=1','/api/quote?plan=restore&machines=6&onsite=1'}
EVIDENCE_NAMES={'report.json','revision-1/report.json','revision-1/browser/report.json',
    'revision-1/browser-v3/report.json','repair-1/report.json','repair-1/browser/report.json',
    'repair-1/browser-v3/report.json','independent-harness.py'}


def digest(path):return sha256(Path(path).read_bytes()).hexdigest()


def unique(pairs):
    result={}
    for key,value in pairs:
        if key in result:raise ValueError('Duplicate JSON key')
        result[key]=value
    return result


def read(path):return json.loads(Path(path).read_text(encoding='utf-8'),object_pairs_hook=unique)


def checked(path):
    path=Path(path)
    if any(item.is_symlink() for item in (path,*path.parents)):raise ValueError('Symlink evidence is not allowed')
    resolved=path.resolve(strict=True);root=WORKSPACE.resolve(strict=True)
    if not resolved.is_relative_to(root) or not resolved.is_file() or resolved.stat().st_size>16*1024*1024:
        raise ValueError('Evidence must be a bounded regular workspace file')
    return resolved


def hashes(files):return {name:sha256(value.encode()).hexdigest() for name,value in files.items()}


def model_paths(repair_path):
    roots=list(repair_path.parent.glob('model-evidence/*'))
    roots=[root for root in roots if root.is_dir()]
    if len(roots)!=1:raise ValueError('Exactly one raw repair evidence directory required')
    root=roots[0]
    return tuple(checked(root/name) for name in ('repair-request.json','repair-response.json','manifest.json'))


def validate_browser(data,source_report_sha,source_hashes,passed):
    checks=data.get('checks',[]) if isinstance(data,dict) else []
    by_name={row.get('name'):row for row in checks if isinstance(row,dict)}
    expected_failed=[] if passed else ['mobile-menu-links-in-viewport']
    actual_failed=[name for name in CHECKS if by_name.get(name,{}).get('passed') is not True]
    if (data.get('schema')!='service-quote-transfer-browser.v1'
            or data.get('examiner_version')!='2026-10-11.viewport.v3'
            or not re.fullmatch(r'[a-f0-9]{64}',data.get('examiner_sha256',''))
            or data.get('source_report_sha256')!=source_report_sha
            or data.get('source_sha256')!=source_hashes or set(by_name)!=set(CHECKS)
            or len(checks)!=len(CHECKS) or actual_failed!=expected_failed
            or data.get('status')!=('passed' if passed else 'failed')
            or data.get('runtime_errors')!=[] or data.get('blocked_requests')!=[]
            or {item.get('path') for item in data.get('requests',[])}!=REQUESTS
            or len(data.get('requests',[]))!=3):
        raise ValueError('Browser evidence does not prove the exact before/after UI behavior')
    for item in data['requests']:
        run=item.get('run',{});profile=run.get('profile',{})
        try:payload=json.loads(run['log'],object_pairs_hook=unique);response=payload['response']
        except (KeyError,TypeError,ValueError,json.JSONDecodeError):raise ValueError('Invalid browser preview evidence') from None
        if (run.get('exit_code')!=0 or run.get('cli_exit_code')!=0 or run.get('cleanup_confirmed') is not True
                or run.get('reason') is not None or run.get('oom_killed') is not False
                or profile.get('profile')!='python-web-preview-v1' or profile.get('network')!='none'
                or profile.get('stateless') is not True or payload.get('schema')!='python-web-preview.v1'
                or response.get('status')!=200 or not isinstance(response.get('body'),str)):
            raise ValueError('Invalid browser preview evidence')


def validate_package(repair,harness):
    revision=repair['revision'];rows=[row for row in repair.get('tests',[]) if row.get('id')==revision.get('test_run_id')]
    if len(rows)!=1:raise ValueError('Exact frozen PackageRun missing')
    row=rows[0];run=row.get('result',{});profile=row.get('profile',{})
    try:payload=json.loads(run['log'],object_pairs_hook=unique)
    except (KeyError,TypeError,ValueError,json.JSONDecodeError):raise ValueError('Invalid PackageRun log') from None
    if (row.get('state')!='passed' or row.get('package_id')!=revision.get('new_package_id')
            or row.get('package_checksum')!=revision.get('new_package_checksum')
            or profile.get('harness_checksum')!=digest(harness) or run.get('profile')!=profile
            or run.get('cleanup_confirmed') is not True or run.get('exit_code')!=0 or run.get('cli_exit_code')!=0
            or run.get('reason') is not None or run.get('oom_killed') is not False
            or payload.get('schema')!='python-web-test.v1' or payload.get('tests_ok') is not True
            or payload.get('http_ok') is not True or payload.get('source_not_exposed') is not True
            or payload.get('errors')!=[] or set(payload.get('isolation',{}))!=ISOLATION_KEYS
            or not all(value is True for value in payload['isolation'].values())
            or not re.search(r'Ran 7 tests',payload.get('tests_log',''))):
        raise ValueError('Passed frozen 7-test and 19-probe PackageRun required')


def validate(repair_report,before_browser,after_browser,assessment_path):
    repair_path,before_path,after_path,assessment_path=map(checked,
        (repair_report,before_browser,after_browser,assessment_path))
    repair=read(repair_path);assessment=read(assessment_path)
    base_path=checked(repair.get('source_report',''));harness=checked(base_path.parent.parent/'independent-harness.py')
    base=read(base_path);before=read(before_path);after=read(after_path)
    request_path,response_path,manifest_path=model_paths(repair_path)
    request,response,model_manifest=map(read,(request_path,response_path,manifest_path))
    base_files=base.get('final_sources',{});final_files=repair.get('final_sources',{})
    parse_sources(json.dumps({'files':base_files},ensure_ascii=False));parse_sources(json.dumps({'files':final_files},ensure_ascii=False))
    revision=repair.get('revision',{});base_revision=base.get('revision',{})
    if (repair.get('schema')!='service-quote-transfer-ui-repair.v1' or repair.get('status')!='awaiting_review'
            or repair.get('exact_change_scope') is not True or repair.get('candidate_created') is not True
            or repair.get('requested_change')!=list(CHANGED) or repair.get('owner_accepted') is not False
            or revision.get('state')!='awaiting_review' or revision.get('accepted') is not False
            or revision.get('test_state')!='passed' or repair.get('source_report_sha256')!=digest(base_path)
            or repair.get('source_package_id')!=base_revision.get('new_package_id')
            or repair.get('source_package_checksum')!=base_revision.get('new_package_checksum')
            or repair.get('frozen_harness_sha256')!=digest(harness)):
        raise ValueError('Complete unaccepted two-file UI repair required')
    base_hashes,final_hashes=hashes(base_files),hashes(final_files)
    if (set(base_files)!=set(final_files) or any(base_files[name]==final_files[name] for name in CHANGED)
            or any(base_files[name]!=final_files[name] for name in PRESERVED)
            or repair.get('preserved_sha256')!={name:base_hashes[name] for name in PRESERVED}):
        raise ValueError('Exactly index.html and style.css must change')
    validate_package(repair,harness)
    validate_browser(before,digest(base_path),base_hashes,False)
    validate_browser(after,digest(repair_path),final_hashes,True)
    raw=response.get('content');config=request.get('config',{});messages=request.get('messages')
    response_fields={'content','model','digest','done_reason','elapsed_seconds','eval_count',
                     'prompt_eval_count','stream_bytes','timings_ns'}
    if (set(request)!={'config','messages'} or not isinstance(messages,list) or len(messages)!=2
            or [message.get('role') for message in messages]!=['system','user']
            or REPAIR_PROFILE not in messages[0].get('content','') or set(response)!=response_fields
            or config.get('format')!=REPAIR_SCHEMA or not isinstance(raw,str)
            or not isinstance(config.get('model'),str) or not config['model'].strip()
            or not re.fullmatch(r'[a-f0-9]{64}',config.get('digest',''))
            or response.get('model')!=config['model'] or response.get('digest')!=config['digest']
            or response.get('done_reason')!='stop'):
        raise ValueError('Pinned raw repair request/response required')
    user_content=messages[1].get('content','')
    if not isinstance(user_content,str) or not user_content.startswith(EXPORTED_TASK_PREFIX):
        raise ValueError('Raw repair request does not use the exact exported task prefix')
    try:
        packet=json.loads(user_content[len(EXPORTED_TASK_PREFIX):],object_pairs_hook=unique)
        packet_revision=packet['revision'];task_context=packet['task_context']
    except (KeyError,TypeError,ValueError,json.JSONDecodeError):
        raise ValueError('Raw repair request does not contain the bound revision packet') from None
    if (not isinstance(packet,dict) or set(packet)!=PACKET_FIELDS
            or not isinstance(task_context,dict) or set(task_context)!=TASK_CONTEXT_FIELDS
            or any(not isinstance(task_context[name],str) or not task_context[name].strip()
                   for name in TASK_CONTEXT_FIELDS)
            or not isinstance(packet_revision,dict) or set(packet_revision)!=REVISION_FIELDS
            or type(packet_revision.get('previous_attempt_id')) is not int
            or packet_revision['previous_attempt_id'] < 1):
        raise ValueError('Raw repair request has an invalid exported packet shape')
    rejection=(revision.get('description')+'\n\nOczekiwany rezultat / test odbioru: '
               +revision.get('expected_result'))
    rejected=packet_revision.get('rejected_result')
    if (not isinstance(rejected,str) or parse_sources(rejected)!=base_files
            or packet_revision.get('rejected_checksum')!=sha256(rejected.encode()).hexdigest()
            or packet_revision.get('rejection_reason')!=rejection):
        raise ValueError('Raw repair request does not bind exact base sources and feedback')
    parsed=json.loads(raw,object_pairs_hook=unique)
    if (isinstance(parsed,dict) and set(parsed)=={'changes'} and isinstance(parsed['changes'],dict)):
        changes=parsed['changes']
    else:raise ValueError('Raw response must contain only changes')
    if set(changes)!=set(CHANGED) or any(changes[name]!=final_files[name] for name in CHANGED):
        raise ValueError('Raw response must exactly contain both corrected UI files')
    inference=[row for row in repair.get('inferences',[]) if row.get('id')==revision.get('inference_id')]
    if len(inference)!=1:raise ValueError('Exact LocalInference missing')
    row=inference[0];metrics=row.get('metrics',{});assembly=metrics.get('assembly',{})
    if (row.get('state')!='awaiting_review' or row.get('error_code') is not None
            or metrics.get('output_profile')!=REPAIR_PROFILE or metrics.get('package_id')!=revision['new_package_id']
            or metrics.get('package_checksum')!=revision['new_package_checksum']
            or assembly.get('changed_files')!=list(CHANGED) or sorted(assembly.get('preserved_files',[]))!=sorted(PRESERVED)
            or assembly.get('raw_response_checksum')!=sha256(raw.encode()).hexdigest()
            or assembly.get('tests_checksum')!=base_hashes['test_app.py']
            or sha256(row.get('result_content','').encode()).hexdigest()!=row.get('result_checksum')
            or parse_sources(row['result_content'])!=final_files):
        raise ValueError('Inference assembly does not bind the exact two-file repair')
    if (model_manifest.get('schema')!='filewise-application-provider.v1'
            or model_manifest.get('status')!='repair_delegated' or model_manifest.get('model')!=response['model']
            or model_manifest.get('digest')!=response['digest']
            or model_manifest.get('repair_response_sha256')!=sha256(json.dumps(response,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
            or model_manifest.get('authorship')!={'code':'local_model','orchestration':'assistant'}):
        raise ValueError('Raw model authorship manifest missing')
    evidence=assessment.get('evidence',{})
    pilot=base_path.parent.parent
    if (assessment.get('schema')!='web-delivery-technical-assessment.v1'
            or assessment.get('status')!='passed_scoped_technical_review'
            or assessment.get('source_package_id')!=revision.get('new_package_id')
            or assessment.get('source_package_checksum')!=revision.get('new_package_checksum')
            or set(evidence)!=EVIDENCE_NAMES or assessment.get('model_tests_passed')!=7
            or assessment.get('frozen_http_probes_passed')!=19 or assessment.get('browser_checks_passed')!=15
            or assessment.get('approved_for_training') is not False
            or set(assessment.get('screenshots_reviewed',{}))!={'desktop-full.png','mobile-full.png'}):
        raise ValueError('Independent technical assessment is incomplete')
    for name,value in evidence.items():
        if digest(checked(pilot/name))!=value:raise ValueError('Technical assessment evidence changed')
    for name,value in assessment.get('screenshots_reviewed',{}).items():
        if name not in ('desktop-full.png','mobile-full.png') or digest(checked(after_path.parent/name))!=value:
            raise ValueError('Reviewed screenshot evidence changed')
    candidate={'schema':'web-code-repair-candidate.v2','family_id':FAMILY,'split':'train_candidate',
        'status':'pending_independent_learning_review','title':task_context['title'],
        'brief':task_context['brief'],'completion_criterion':task_context['completion_criterion'],
        'feedback':packet_revision['rejection_reason'],
        'incorrect_sources':{name:base_files[name] for name in CHANGED},
        'preserved_sources':{name:base_files[name] for name in PRESERVED},
        'corrected_changes':{name:final_files[name] for name in CHANGED},'changed_files':list(CHANGED),
        'preserved_sha256':{name:base_hashes[name] for name in PRESERVED},
        'model':response['model'],'digest':response['digest'],'output_profile':REPAIR_PROFILE,
        'owner_accepted':False,'training_started':False,'ready_for_trainer':False}
    proof={'repair_report':repair_path,'before_browser':before_path,'after_browser':after_path,
        'technical_assessment':assessment_path,'base_report':base_path,'raw_request':request_path,
        'raw_response':response_path,'model_authorship':manifest_path}
    review={'schema':'web-code-ui-experience-review.v2','status':'pending_independent_learning_review',
        'reviewer':'system_review','family_id':FAMILY,'split':'train_candidate',
        'sample_sha256':sha256(canonical_json(candidate).encode()).hexdigest(),
        'evidence':{name:{'path':str(path),'sha256':digest(path)} for name,path in proof.items()},
        'checks':{'raw_two_file_change_exact':True,'four_files_preserved':True,'frozen_7_tests_19_probes':True,
                  'before_browser_failure_bound':True,'after_browser_15_passed':True,
                  'technical_and_screenshots_reviewed':True},
        'heldout_inputs_in_sample':False,'owner_accepted':False,'accepted_for_training':False,
        'training_started':False,'ready_for_trainer':False}
    return candidate,review


def collect(args):
    candidate,review=validate(args.repair_report,args.before_browser,args.after_browser,
                              args.technical_assessment)
    out=Path(tempfile.mkdtemp(prefix='web-ui-experience-',dir=WORKSPACE))
    candidate_path=out/'candidate.json';candidate_path.write_text(canonical_json(candidate),encoding='utf-8')
    review['sample_file_sha256']=digest(candidate_path)
    (out/'review-manifest.json').write_text(json.dumps(review,ensure_ascii=False,indent=2),encoding='utf-8')
    return out


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('repair_report','before_browser','after_browser','technical_assessment'):
        parser.add_argument('--'+name.replace('_','-'),type=Path,required=True)
    parser.add_argument('--collect',action='store_true')
    args=parser.parse_args();candidate,review=validate(args.repair_report,args.before_browser,
        args.after_browser,args.technical_assessment)
    if not args.collect:
        print(json.dumps({'validated':True,'written':False,'schema':candidate['schema'],
            'family_id':FAMILY,'status':review['status'],'ready_for_trainer':False}))
        return 0
    out=collect(args);print(json.dumps({'output':str(out),'status':'pending_independent_learning_review',
        'ready_for_trainer':False,'training_started':False}));return 0


if __name__=='__main__':raise SystemExit(main())
