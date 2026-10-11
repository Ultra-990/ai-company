import json
from pathlib import Path
import shutil
import pytest
from app.services.application_profile import REPAIR_PROFILE,REPAIR_SCHEMA
from app.services.package_runner import ISOLATION_KEYS
from scripts import collect_web_code_experience as collector

def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,ensure_ascii=False,indent=2))
def hashes(files):return {n:collector.sha256(v.encode()).hexdigest() for n,v in files.items()}
def preview(status,body='{}'):
    profile={'profile':'python-web-preview-v1','image':'sha256:'+'1'*64,'harness_checksum':'2'*64,
        'timeout_seconds':45,'memory_bytes':536870912,'cpus':1,'pids':64,'network':'none','stateless':True}
    return {'profile':profile,'cleanup_confirmed':True,'exit_code':0,'cli_exit_code':0,'reason':None,
        'oom_killed':False,'log':json.dumps({'schema':'python-web-preview.v1','response':
        {'status':status,'body':body,'content_type':'application/json'}})}
def edge(source_hash,files,statuses):
    spec=(('valid-control',200,True),('extra-empty-rejected',400,True),('duplicate-value-diagnostic',400,False));probes=[]
    for (name,expected,gate),status in zip(spec,statuses):
        raw=preview(status);response=json.loads(raw['log'])['response'];probes.append({'name':name,'gate':gate,
            'expected_status':expected,'observed_status':status,'passed':status==expected,'response':response,'raw_run':raw})
    return {'schema':'business-website-edge-check.v1','source_report_sha256':source_hash,
        'source_sha256':hashes(files),'gate_passed':all(p['passed'] for p in probes if p['gate']),
        'diagnostic_passed':all(p['passed'] for p in probes if not p['gate']),'probes':probes}

@pytest.fixture
def case(tmp_path,monkeypatch):
    root=tmp_path/'workspace';pilot=root/'pilot';pilot.mkdir(parents=True);monkeypatch.setattr(collector,'WORKSPACE',root)
    shutil.copyfile(Path(__file__).parents[1]/'app/runner/harness.py',pilot/'independent-harness.py')
    harness_sha=collector.digest(pilot/'independent-harness.py')
    base_files={'app.py':'# incorrect synthetic source\nQUERY="drops blanks"\n','test_app.py':'# locked synthetic tests\n',
        'index.html':'<!doctype html><html>Synthetic</html>','style.css':'body{color:#123}',
        'app.js':'const synthetic=true;','README.md':'# Synthetic server'}
    final_files=base_files|{'app.py':'# corrected synthetic source\nQUERY="rejects duplicates"\n'}
    base={'schema':'business-website-revision.v1','status':'awaiting_review','revision':
        {'new_package_id':17,'new_package_checksum':'a'*64,'test_state':'passed'},'final_sources':base_files}
    base_path=pilot/'revision-1/report.json';write(base_path,base);base_sha=collector.digest(base_path)
    model_dir=pilot/'repair-1/model-evidence/synthetic';model_dir.mkdir(parents=True)
    model='teacher-fixture-model';model_digest='b'*64
    request={'config':{'model':model,'digest':model_digest,'format':REPAIR_SCHEMA},'messages':
        [{'role':'system','content':'synthetic teacher fixture'},{'role':'user','content':'repair opaque source'}]}
    raw=json.dumps({'changes':{'app.py':final_files['app.py']}});response={
        'content':raw,'model':model,'digest':model_digest,'done_reason':'stop'}
    write(model_dir/'repair-request.json',request);write(model_dir/'repair-response.json',response)
    write(model_dir/'manifest.json',{'schema':'filewise-application-provider.v1','status':'repair_delegated',
        'model':model,'digest':model_digest,'authorship':{'code':'local_model','orchestration':'assistant'},
        'repair_response_sha256':collector.sha256(json.dumps(response,ensure_ascii=False,sort_keys=True).encode()).hexdigest()})
    result_content=json.dumps({'files':final_files},ensure_ascii=False)
    profile={'profile':'python-web-v1','image':'sha256:'+'3'*64,'harness_checksum':harness_sha,
        'timeout_seconds':45,'memory_bytes':536870912,'cpus':1,'pids':64,'network':'none'}
    payload={'schema':'python-web-test.v1','isolation':{k:True for k in ISOLATION_KEYS},'tests_ok':True,
        'http_ok':True,'source_not_exposed':True,'tests_log':'synthetic tests passed','errors':[]}
    test_result={'profile':profile,'cleanup_confirmed':True,'exit_code':0,'cli_exit_code':0,
        'reason':None,'oom_killed':False,'log':json.dumps(payload)}
    inference={'id':4,'state':'awaiting_review','error_code':None,'result_content':result_content,
        'result_checksum':collector.sha256(result_content.encode()).hexdigest(),'metrics':{'output_profile':REPAIR_PROFILE,
        'package_id':24,'package_checksum':'c'*64,'assembly':{'changed_files':['app.py'],
        'preserved_files':list(collector.PRESERVED),'raw_response_checksum':collector.sha256(raw.encode()).hexdigest(),
        'tests_checksum':hashes(base_files)['test_app.py']}}}
    repair_dir=pilot/'repair-1';candidate=repair_dir/'candidate.zip';candidate.parent.mkdir(parents=True,exist_ok=True);candidate.touch()
    repair={'schema':'business-website-edge-repair.v1','status':'awaiting_review','source_report':str(base_path),
        'source_report_sha256':base_sha,'source_package_id':17,'source_package_checksum':'a'*64,
        'frozen_harness_sha256':harness_sha,'preserved_sha256':{n:hashes(base_files)[n] for n in collector.PRESERVED},
        'only_app_changed':True,'candidate_created':True,'candidate_zip':str(candidate),'owner_accepted':False,
        'final_sources':final_files,'revision':{'inference_id':4,'test_run_id':9,'new_package_id':24,
        'new_package_checksum':'c'*64,'test_state':'passed','accepted':False},'tests':[{'id':9,'package_id':24,
        'package_checksum':'c'*64,'state':'passed','profile':profile,'result':test_result,'report_id':10}],
        'inferences':[inference]}
    repair_path=repair_dir/'report.json';write(repair_path,repair);repair_sha=collector.digest(repair_path)
    failing=pilot/'edge-check-1/report.json';passing=pilot/'edge-check-2/report.json'
    write(failing,edge(base_sha,base_files,(200,200,200)));write(passing,edge(repair_sha,final_files,(200,400,400)))
    paths=(('/api/estimate?service=basic&bikes=1&express=0',90),('/api/estimate?service=full&bikes=3&express=1',690),('/api/estimate?service=basic&bikes=8&express=1',1120))
    browser={'schema':'business-website-browser.v1','status':'passed','source_report_sha256':repair_sha,
        'source_sha256':hashes(final_files),'accepted':False,'runtime_errors':[],'blocked_requests':[],
        'checks':[{'name':n,'passed':True} for n in collector.BROWSER_CHECKS],
        'requests':[{'path':p,'run':preview(200,json.dumps({'total':t}))} for p,t in paths]}
    browser_path=repair_dir/'browser/report.json';write(browser_path,browser)
    return {'repair':repair_path,'failing':failing,'passing':passing,'browser':browser_path,
        'response':model_dir/'repair-response.json','request':model_dir/'repair-request.json'}

def validate(c):return collector.validate(c['repair'],c['failing'],c['passing'],c['browser'])
def rebind(c):
    for n in ('passing','browser'):
        v=json.loads(c[n].read_text());v['source_report_sha256']=collector.digest(c['repair']);write(c[n],v)

def test_validates_self_contained_teacher_fixture(case):
    sample,review=validate(case);encoded=json.dumps(sample)
    assert sample['split']=='train_candidate' and review['reviewer']=='system_review'
    assert 'coupon=' not in encoded and 'service=basic&service=full' not in encoded
    assert review['accepted_for_training'] is sample['ready_for_trainer'] is False

@pytest.mark.parametrize('change,match',[('raw','Raw model change'),('profile','Pinned completed'),
    ('raw_hash','LocalInference snapshot'),('edge_package','Bound passing edge'),('edge_raw','Bound passing edge'),
    ('package_run','frozen PackageRun'),('browser_redacted','browser evidence'),
    ('manifest_hash','authorship manifest'),('result_checksum','LocalInference snapshot'),('frontend','Only app.py')])
def test_rejects_tampered_synthetic_evidence(case,change,match):
    if change=='raw':
        v=json.loads(case['response'].read_text());p=json.loads(v['content']);p['changes']['app.py']+='x';v['content']=json.dumps(p);write(case['response'],v)
    elif change=='profile':
        v=json.loads(case['request'].read_text());v['config']['format']={};write(case['request'],v)
    elif change=='edge_package':
        v=json.loads(case['passing'].read_text());v['source_sha256']['app.py']='f'*64;write(case['passing'],v)
    elif change=='edge_raw':
        v=json.loads(case['passing'].read_text());p=next(x for x in v['probes'] if x['name']=='extra-empty-rejected');raw=json.loads(p['raw_run']['log']);raw['response']['status']=200;p['raw_run']['log']=json.dumps(raw);write(case['passing'],v)
    elif change=='browser_redacted':
        v=json.loads(case['browser'].read_text());v['checks'].pop();write(case['browser'],v)
    elif change=='manifest_hash':
        m=case['request'].parent/'manifest.json';v=json.loads(m.read_text());v['repair_response_sha256']='f'*64;write(m,v)
    else:
        v=json.loads(case['repair'].read_text());inf=v['inferences'][0]
        if change=='raw_hash':inf['metrics']['assembly']['raw_response_checksum']='f'*64
        elif change=='result_checksum':inf['result_checksum']='f'*64
        elif change=='frontend':v['final_sources']['index.html']+='x'
        else:
            row=v['tests'][0];p=json.loads(row['result']['log']);p['tests_ok']=False;row['result']['log']=json.dumps(p)
        write(case['repair'],v);rebind(case)
    with pytest.raises(ValueError,match=match):validate(case)

def test_collect_writes_unique_pending_bundles(case):
    class Args:
        repair_report=case['repair'];failing_edge_report=case['failing'];passing_edge_report=case['passing'];browser_report=case['browser']
    first=collector.collect(Args);second=collector.collect(Args)
    assert first!=second and first.name.startswith('web-code-experience-')
    sample=json.loads((first/'candidate.json').read_text());review=json.loads((first/'review-manifest.json').read_text())
    assert review['sample_file_sha256']==collector.digest(first/'candidate.json')
    assert sample['training_started'] is review['ready_for_trainer'] is False
