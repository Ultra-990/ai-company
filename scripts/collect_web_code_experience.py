"""Validate or collect one independently evidenced web/code repair candidate."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import re
import sys
import tempfile

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.services.application_profile import REPAIR_PROFILE,REPAIR_SCHEMA,parse_sources
from app.services.package_runner import ISOLATION_KEYS
from app.services.workspace_packages import canonical_json

WORKSPACE=Path('/home/marcin/ai-company-workspaces')
FAMILY='rowerownia-query-parser-development'
PRESERVED=('README.md','app.js','index.html','style.css','test_app.py')
BROWSER_CHECKS={'required-content','labelled-fields','desktop-no-overflow','navigation',
    'quote-basic-1-False','quote-full-3-True','quote-basic-8-True','faq-opens',
    'mobile-no-overflow','mobile-menu-closed','mobile-menu-open','mobile-escape'}
BROWSER_REQUESTS={'/api/estimate?service=basic&bikes=1&express=0',
    '/api/estimate?service=full&bikes=3&express=1','/api/estimate?service=basic&bikes=8&express=1'}


def digest(path):return sha256(path.read_bytes()).hexdigest()


def unique(pairs):
    value={}
    for key,item in pairs:
        if key in value:raise ValueError('Duplicate JSON key')
        value[key]=item
    return value


def read(path):return json.loads(path.read_text(encoding='utf-8'),object_pairs_hook=unique)


def checked(path):
    path=Path(path)
    if any(item.is_symlink() for item in (path,*path.parents)):raise ValueError('Symlink evidence is not allowed')
    resolved=path.resolve(strict=True)
    if not resolved.is_relative_to(WORKSPACE.resolve(strict=True)):raise ValueError('Evidence must remain in Linux workspace')
    return resolved


def source_hashes(files):return {name:sha256(content.encode()).hexdigest() for name,content in files.items()}


def preview_response(raw):
    try:payload=json.loads(raw.get('log',''),object_pairs_hook=unique);response=payload['response'];profile=raw['profile']
    except (ValueError,KeyError,TypeError,json.JSONDecodeError) as exc:raise ValueError('Invalid raw preview evidence') from exc
    if (raw.get('cleanup_confirmed') is not True or raw.get('exit_code')!=0 or raw.get('cli_exit_code')!=0
            or raw.get('reason') is not None or raw.get('oom_killed') is not False
            or payload.get('schema')!='python-web-preview.v1' or profile.get('profile')!='python-web-preview-v1'
            or profile.get('network')!='none' or profile.get('stateless') is not True
            or not isinstance(profile.get('harness_checksum'),str)
            or not re.fullmatch(r'[0-9a-f]{64}',profile['harness_checksum'])
            or type(response.get('status')) is not int or not isinstance(response.get('body'),str)
            or not isinstance(response.get('content_type'),str)):
        raise ValueError('Raw preview did not prove a bounded successful request')
    return response


def exact_probe(report,name,status,passed):
    matches=[item for item in report.get('probes',[]) if item.get('name')==name]
    if len(matches)!=1:return False
    item=matches[0]
    try:response=preview_response(item.get('raw_run',{}))
    except ValueError:return False
    return (item.get('observed_status')==status and item.get('passed') is passed
            and item.get('response')==response and response['status']==status)


def package_test(repair,harness_path):
    revision=repair['revision'];matches=[row for row in repair.get('tests',[]) if row.get('id')==revision.get('test_run_id')]
    if len(matches)!=1:raise ValueError('Exact PackageRun snapshot missing')
    row=matches[0];profile=row.get('profile',{});raw=row.get('result',{})
    try:payload=json.loads(raw.get('log',''),object_pairs_hook=unique)
    except (ValueError,TypeError,json.JSONDecodeError) as exc:raise ValueError('Invalid frozen harness log') from exc
    if (row.get('state')!='passed' or row.get('package_id')!=revision.get('new_package_id')
            or row.get('package_checksum')!=revision.get('new_package_checksum')
            or profile.get('profile')!='python-web-v1' or profile.get('harness_checksum')!=digest(harness_path)
            or raw.get('profile')!=profile or raw.get('cleanup_confirmed') is not True
            or raw.get('exit_code')!=0 or raw.get('cli_exit_code')!=0 or raw.get('reason') is not None
            or raw.get('oom_killed') is not False or payload.get('schema')!='python-web-test.v1'
            or payload.get('tests_ok') is not True or payload.get('http_ok') is not True
            or payload.get('source_not_exposed') is not True or payload.get('errors')!=[]
            or set(payload.get('isolation',{}))!=ISOLATION_KEYS
            or not all(value is True for value in payload['isolation'].values())):
        raise ValueError('Matching successful frozen PackageRun required')
    return row


def evidence_paths(repair):
    model_root=checked(Path(repair.get('candidate_zip',''))).parent/'model-evidence'
    if not model_root.is_dir():raise ValueError('Model evidence directory missing')
    requests=list(model_root.glob('*/repair-request.json'));responses=list(model_root.glob('*/repair-response.json'))
    manifests=list(model_root.glob('*/manifest.json'))
    if not (len(requests)==len(responses)==len(manifests)==1
            and requests[0].parent==responses[0].parent==manifests[0].parent):
        raise ValueError('Exactly one raw repair conversation required')
    return checked(Path(repair['source_report'])),checked(requests[0]),checked(responses[0]),checked(manifests[0])


def validate(repair_report,failing_edge_report,passing_edge_report,browser_report):
    paths={name:checked(path) for name,path in {
        'repair_report':repair_report,'failing_edge_report':failing_edge_report,
        'passing_edge_report':passing_edge_report,'browser_report':browser_report}.items()}
    repair=read(paths['repair_report']);base_path,request_path,response_path,model_manifest_path=evidence_paths(repair)
    harness_path=checked(base_path.parent.parent/'independent-harness.py')
    base=read(base_path);failing=read(paths['failing_edge_report']);passing=read(paths['passing_edge_report'])
    browser=read(paths['browser_report']);request=read(request_path);response=read(response_path);model_manifest=read(model_manifest_path)
    base_files=base.get('final_sources',{});final_files=repair.get('final_sources',{})
    parse_sources(json.dumps({'files':base_files},ensure_ascii=False));parse_sources(json.dumps({'files':final_files},ensure_ascii=False))
    revision=repair.get('revision',{})
    if (repair.get('schema')!='business-website-edge-repair.v1' or repair.get('status')!='awaiting_review'
            or repair.get('only_app_changed') is not True or repair.get('candidate_created') is not True
            or repair.get('owner_accepted') is not False or revision.get('accepted') is not False
            or revision.get('test_state')!='passed' or not revision.get('new_package_id')
            or not revision.get('new_package_checksum') or repair.get('source_report_sha256')!=digest(base_path)):
        raise ValueError('Complete unaccepted tested repair required')
    base_revision=base.get('revision',{})
    if (repair.get('source_package_id')!=base_revision.get('new_package_id')
            or repair.get('source_package_checksum')!=base_revision.get('new_package_checksum')
            or repair.get('frozen_harness_sha256')!=digest(harness_path)):
        raise ValueError('Repair does not originate from the exact tested base package')
    package_test(repair,harness_path)
    if (set(final_files)!=set(base_files) or final_files['app.py']==base_files['app.py']
            or any(final_files[name]!=base_files[name] for name in PRESERVED)
            or repair.get('preserved_sha256')!={name:sha256(base_files[name].encode()).hexdigest() for name in PRESERVED}):
        raise ValueError('Only app.py may change; frontend and model tests must be byte-identical')
    base_hashes=source_hashes(base_files);final_hashes=source_hashes(final_files)
    if (failing.get('schema')!='business-website-edge-check.v1' or failing.get('source_report_sha256')!=digest(base_path)
            or failing.get('source_sha256')!=base_hashes or failing.get('gate_passed') is not False
            or not exact_probe(failing,'valid-control',200,True)
            or not exact_probe(failing,'extra-empty-rejected',200,False)
            or not exact_probe(failing,'duplicate-value-diagnostic',200,False)):
        raise ValueError('Bound failing edge evidence required')
    if (passing.get('schema')!='business-website-edge-check.v1'
            or passing.get('source_report_sha256')!=digest(paths['repair_report'])
            or passing.get('source_sha256')!=final_hashes or passing.get('gate_passed') is not True
            or passing.get('diagnostic_passed') is not True
            or not exact_probe(passing,'valid-control',200,True)
            or not exact_probe(passing,'extra-empty-rejected',400,True)
            or not exact_probe(passing,'duplicate-value-diagnostic',400,True)):
        raise ValueError('Bound passing edge and diagnostic evidence required')
    checks=browser.get('checks',[]);requests=browser.get('requests',[])
    if (browser.get('schema')!='business-website-browser.v1' or browser.get('status')!='passed'
            or browser.get('source_report_sha256')!=digest(paths['repair_report'])
            or browser.get('source_sha256')!=final_hashes or browser.get('accepted') is not False
            or browser.get('runtime_errors')!=[] or browser.get('blocked_requests')!=[]
            or len(checks)!=len(BROWSER_CHECKS) or {item.get('name') for item in checks}!=BROWSER_CHECKS
            or not all(item.get('passed') is True for item in checks)
            or len(requests)!=len(BROWSER_REQUESTS) or {item.get('path') for item in requests}!=BROWSER_REQUESTS):
        raise ValueError('Bound passing browser evidence required')
    try:
        if any(preview_response(item.get('run',{})).get('status')!=200 for item in requests):
            raise ValueError('Browser API request failed')
    except ValueError as exc:raise ValueError('Bound passing browser evidence required') from exc
    config=request.get('config',{});raw=response.get('content')
    if (not isinstance(raw,str) or config.get('format')!=REPAIR_SCHEMA
            or not isinstance(config.get('model'),str) or not config['model'].strip()
            or not isinstance(config.get('digest'),str) or not re.fullmatch(r'[0-9a-f]{64}',config['digest'])
            or config.get('model')!=response.get('model') or config.get('digest')!=response.get('digest')
            or response.get('done_reason')!='stop'):
        raise ValueError('Pinned completed repair response required')
    parsed=json.loads(raw,object_pairs_hook=unique)
    if (not isinstance(parsed,dict) or set(parsed)!={'changes'} or set(parsed['changes'])!={'app.py'}
            or parsed['changes']['app.py']!=final_files['app.py']):
        raise ValueError('Raw model change must exactly equal final app.py')
    inference=[item for item in repair.get('inferences',[]) if item.get('id')==revision.get('inference_id')]
    if len(inference)!=1:raise ValueError('Exact LocalInference snapshot missing')
    row=inference[0];metrics=row.get('metrics',{});assembly=metrics.get('assembly',{})
    if (row.get('state')!='awaiting_review' or row.get('error_code') is not None
            or metrics.get('output_profile')!=REPAIR_PROFILE or metrics.get('package_id')!=revision['new_package_id']
            or metrics.get('package_checksum')!=revision['new_package_checksum']
            or assembly.get('changed_files')!=['app.py'] or sorted(assembly.get('preserved_files',[]))!=sorted(PRESERVED)
            or assembly.get('raw_response_checksum')!=sha256(raw.encode()).hexdigest()
            or assembly.get('tests_checksum')!=base_hashes['test_app.py']
            or not isinstance(row.get('result_content'),str)
            or sha256(row['result_content'].encode()).hexdigest()!=row.get('result_checksum')
            or parse_sources(row['result_content'])!=final_files):
        raise ValueError('LocalInference snapshot does not bind this exact repaired package')
    if (model_manifest.get('schema')!='filewise-application-provider.v1'
            or model_manifest.get('status')!='repair_delegated'
            or model_manifest.get('model')!=response['model'] or model_manifest.get('digest')!=response['digest']
            or model_manifest.get('repair_response_sha256')!=sha256(json.dumps(response,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
            or model_manifest.get('authorship')!={'code':'local_model','orchestration':'assistant'}):
        raise ValueError('Model authorship manifest missing or changed')
    brief=('Repair a Python standard-library web API so it accepts exactly one value for each required '
           'query parameter, rejects unknown fields including empty values, and preserves existing behavior.')
    feedback=('The previous implementation lost explicit empty fields and accepted duplicate values. Preserve '
              'the application contract and unchanged files; correct only the query-validation implementation.')
    sample={'schema':'web-code-repair-candidate.v1','family_id':FAMILY,'split':'train_candidate',
        'status':'pending_independent_learning_review','brief':brief,
        'incorrect_source':base_files['app.py'],'feedback':feedback,'corrected_source':final_files['app.py'],
        'model':response['model'],'digest':response['digest'],'output_profile':REPAIR_PROFILE,
        'owner_accepted':False,'training_started':False,'ready_for_trainer':False}
    proof_paths=paths|{'base_report':base_path,'raw_request':request_path,'raw_response':response_path,
                       'model_authorship':model_manifest_path}
    review={'schema':'web-code-experience-review.v1','status':'pending_independent_learning_review',
        'reviewer':'system_review','family_id':FAMILY,'split':'train_candidate',
        'sample_sha256':sha256(canonical_json(sample).encode()).hexdigest(),
        'evidence':{name:{'path':str(path),'sha256':digest(path)} for name,path in proof_paths.items()},
        'checks':{'raw_model_change_exact':True,'only_app_changed':True,'model_tests_preserved':True,
                  'frontend_preserved':True,'failing_edge_bound':True,'passing_edge_bound':True,
                  'duplicate_diagnostic_passed':True,'browser_checks_passed':True},
        'heldout_inputs_in_sample':False,'owner_accepted':False,'accepted_for_training':False,
        'training_started':False,'ready_for_trainer':False}
    return sample,review


def collect(args):
    sample,review=validate(args.repair_report,args.failing_edge_report,args.passing_edge_report,args.browser_report)
    out=Path(tempfile.mkdtemp(prefix='web-code-experience-',dir=WORKSPACE))
    sample_path=out/'candidate.json';review_path=out/'review-manifest.json'
    sample_path.write_text(canonical_json(sample),encoding='utf-8')
    review['sample_file_sha256']=digest(sample_path)
    review_path.write_text(json.dumps(review,ensure_ascii=False,indent=2),encoding='utf-8')
    return out


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('repair_report','failing_edge_report','passing_edge_report','browser_report'):
        parser.add_argument('--'+name.replace('_','-'),type=Path,required=True)
    parser.add_argument('--collect',action='store_true',help='write a private candidate bundle; does not train')
    args=parser.parse_args();sample,review=validate(
        args.repair_report,args.failing_edge_report,args.passing_edge_report,args.browser_report)
    if not args.collect:
        print(json.dumps({'validated':True,'written':False,'family_id':sample['family_id'],
            'split':sample['split'],'status':review['status'],'training_started':False,
            'ready_for_trainer':False,'required_flag':'--collect'}));return 0
    out=collect(args);print(json.dumps({'output':str(out),'status':'pending_independent_learning_review',
        'training_started':False,'ready_for_trainer':False}));return 0


if __name__=='__main__':raise SystemExit(main())
