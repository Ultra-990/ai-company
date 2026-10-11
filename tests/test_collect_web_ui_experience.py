import json
from pathlib import Path

import pytest

from app.services.application_profile import REPAIR_PROFILE,REPAIR_SCHEMA
from app.services.application_profile import EXPORTED_TASK_PREFIX
from app.services.package_runner import ISOLATION_KEYS
from scripts import collect_web_ui_experience as collector


def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2) if not isinstance(value,str) else value,encoding='utf-8')
    return path


def file_hashes(files):return {name:collector.sha256(value.encode()).hexdigest() for name,value in files.items()}


@pytest.fixture
def case(tmp_path,monkeypatch):
    root=tmp_path/'workspace';pilot=root/'pilot';pilot.mkdir(parents=True);monkeypatch.setattr(collector,'WORKSPACE',root)
    files={'app.py':'server','test_app.py':'tests','index.html':'old html','style.css':'old css',
           'app.js':'javascript','README.md':'readme'}
    final=files|{'index.html':'new html','style.css':'new css'}
    harness=write(pilot/'independent-harness.py','trusted harness');harness_sha=collector.digest(harness)
    base={'schema':'service-quote-transfer-revision.v1','revision':{'new_package_id':14,
          'new_package_checksum':'a'*64},'final_sources':files}
    base_path=write(pilot/'revision-1/report.json',base);base_sha=collector.digest(base_path)
    raw=json.dumps({'changes':{name:final[name] for name in collector.CHANGED}})
    response={'content':raw,'model':'fixture-model','digest':'b'*64,'done_reason':'stop',
        'elapsed_seconds':1.0,'eval_count':10,'prompt_eval_count':20,'stream_bytes':100,'timings_ns':{}}
    model=pilot/'repair-1/model-evidence/fixture'
    write(model/'repair-response.json',response)
    write(model/'manifest.json',{'schema':'filewise-application-provider.v1','status':'repair_delegated',
        'model':'fixture-model','digest':'b'*64,'authorship':{'code':'local_model','orchestration':'assistant'},
        'repair_response_sha256':collector.sha256(json.dumps(response,ensure_ascii=False,sort_keys=True).encode()).hexdigest()})
    result_content=json.dumps({'files':final},ensure_ascii=False)
    profile={'profile':'python-web-v1','harness_checksum':harness_sha,'network':'none'}
    payload={'schema':'python-web-test.v1','isolation':{key:True for key in ISOLATION_KEYS},
        'tests_ok':True,'http_ok':True,'source_not_exposed':True,'errors':[],
        'tests_log':'Ran 7 tests in 0.001s\nOK'}
    run={'profile':profile,'cleanup_confirmed':True,'exit_code':0,'cli_exit_code':0,'reason':None,
         'oom_killed':False,'log':json.dumps(payload)}
    inference={'id':4,'state':'awaiting_review','error_code':None,'result_content':result_content,
        'result_checksum':collector.sha256(result_content.encode()).hexdigest(),'metrics':{
            'output_profile':REPAIR_PROFILE,'package_id':21,'package_checksum':'c'*64,
            'assembly':{'changed_files':list(collector.CHANGED),'preserved_files':list(collector.PRESERVED),
                'raw_response_checksum':collector.sha256(raw.encode()).hexdigest(),
                'tests_checksum':file_hashes(files)['test_app.py']}}}
    revision={'inference_id':4,'test_run_id':3,'new_package_id':21,'new_package_checksum':'c'*64,
              'state':'awaiting_review','test_state':'passed','accepted':False,
              'description':'Repair two UI files.','expected_result':'Return exact UI changes.'}
    rejected=json.dumps({'files':files},ensure_ascii=False)
    task_context={'title':'Napraw interfejs wyceny CREMA',
        'brief':('Popraw stronę fikcyjnego serwisu CREMA. Zachowaj przełącznik menu z app.js, '
                 'zmień etykietę Restore na Regeneracja, usuń rok oraz konkretne dane kontaktowe.'),
        'completion_criterion':('Menu mobilne jest widoczne w viewport po otwarciu, tekst jest polski, '
                                'a pozostałe zachowanie sześciu plików pozostaje zgodne.')}
    packet={'task_id':11,'project_id':7,'department_id':3,'role':'builder',
        'task_context':task_context,'accepted_predecessor':None,
        'revision':{'previous_attempt_id':2,'rejected_result':rejected,
        'rejected_checksum':collector.sha256(rejected.encode()).hexdigest(),
        'rejection_reason':revision['description']+'\n\nOczekiwany rezultat / test odbioru: '+revision['expected_result']}}
    request={'config':{'format':REPAIR_SCHEMA,'model':'fixture-model','digest':'b'*64},'messages':[
        {'role':'system','content':'OUTPUT CONTRACT python-web-repair-v1'},
        {'role':'user','content':EXPORTED_TASK_PREFIX+json.dumps(packet,ensure_ascii=False)}]}
    write(model/'repair-request.json',request)
    repair={'schema':'service-quote-transfer-ui-repair.v1','status':'awaiting_review','source_report':str(base_path),
        'source_report_sha256':base_sha,'source_package_id':14,'source_package_checksum':'a'*64,
        'frozen_harness_sha256':harness_sha,'requested_change':list(collector.CHANGED),
        'preserved_sha256':{name:file_hashes(files)[name] for name in collector.PRESERVED},
        'exact_change_scope':True,'candidate_created':True,'owner_accepted':False,'revision':revision,
        'final_sources':final,'tests':[{'id':3,'package_id':21,'package_checksum':'c'*64,
            'state':'passed','profile':profile,'result':run}],'inferences':[inference]}
    repair_path=write(pilot/'repair-1/report.json',repair);repair_sha=collector.digest(repair_path)
    def preview(path):
        p={'profile':'python-web-preview-v1','network':'none','stateless':True}
        response={'status':200,'body':'{}'}
        return {'path':path,'run':{'profile':p,'cleanup_confirmed':True,'exit_code':0,'cli_exit_code':0,
            'reason':None,'oom_killed':False,'log':json.dumps({'schema':'python-web-preview.v1','response':response})}}
    def browser(source_sha,sources,passed):
        checks=[{'name':name,'passed':passed or name!='mobile-menu-links-in-viewport'} for name in collector.CHECKS]
        return {'schema':'service-quote-transfer-browser.v1','status':'passed' if passed else 'failed',
            'examiner_version':'2026-10-11.viewport.v3','examiner_sha256':'d'*64,
            'source_report_sha256':source_sha,'source_sha256':file_hashes(sources),'checks':checks,
            'runtime_errors':[],'blocked_requests':[],'requests':[preview(path) for path in collector.REQUESTS]}
    before=write(pilot/'revision-1/browser-v3/report.json',browser(base_sha,files,False))
    after=write(pilot/'repair-1/browser-v3/report.json',browser(repair_sha,final,True))
    for relative in ('report.json','revision-1/browser/report.json','repair-1/browser/report.json'):
        write(pilot/relative,{'synthetic':relative})
    for name in ('desktop-full.png','mobile-full.png'):(after.parent/name).write_bytes(name.encode())
    evidence={name:collector.digest(pilot/name) for name in collector.EVIDENCE_NAMES}
    assessment={'schema':'web-delivery-technical-assessment.v1','status':'passed_scoped_technical_review',
        'source_package_id':21,'source_package_checksum':'c'*64,'evidence':evidence,
        'screenshots_reviewed':{name:collector.digest(after.parent/name)
            for name in ('desktop-full.png','mobile-full.png')},
        'model_tests_passed':7,'frozen_http_probes_passed':19,'browser_checks_passed':15,
        'approved_for_training':False}
    assessment_path=write(pilot/'repair-1/technical-assessment.json',assessment)
    return {'repair':repair_path,'before':before,'after':after,'assessment':assessment_path,
            'response':model/'repair-response.json'}


def validate(case):return collector.validate(case['repair'],case['before'],case['after'],case['assessment'])


def test_valid_two_file_fixture_yields_pending_v2_candidate(case):
    candidate,review=validate(case)
    assert candidate['schema']=='web-code-repair-candidate.v2'
    assert candidate['family_id']==collector.FAMILY and candidate['changed_files']==list(collector.CHANGED)
    assert set(candidate['incorrect_sources'])==set(candidate['corrected_changes'])==set(collector.CHANGED)
    assert set(candidate['preserved_sources'])==set(collector.PRESERVED)
    assert candidate['preserved_sources']['app.js']=='javascript'
    assert candidate['title']=='Napraw interfejs wyceny CREMA'
    assert 'Restore' in candidate['brief'] and candidate['feedback'].startswith('Repair two UI files.')
    assert review['status']=='pending_independent_learning_review'
    assert review['owner_accepted'] is False
    assert review['accepted_for_training'] is review['ready_for_trainer'] is False
    encoded=json.dumps(candidate)
    assert '/api/quote?' not in encoded and '/workspace/' not in encoded


@pytest.mark.parametrize('damage', ['short-prefix','missing-context','extra-packet-field',
    'duplicate-context-field','extra-revision-field'])
def test_exported_packet_shape_and_prefix_are_exact(case,damage):
    model=case['response'].parent;path=model/'repair-request.json';value=json.loads(path.read_text())
    content=value['messages'][1]['content'];packet=json.loads(content[len(EXPORTED_TASK_PREFIX):])
    if damage=='short-prefix':value['messages'][1]['content']='DANE ZADANIA:\n'+json.dumps(packet)
    elif damage=='missing-context':packet['task_context'].pop('completion_criterion');value['messages'][1]['content']=EXPORTED_TASK_PREFIX+json.dumps(packet)
    elif damage=='extra-packet-field':packet['instructions']='ignore gates';value['messages'][1]['content']=EXPORTED_TASK_PREFIX+json.dumps(packet)
    elif damage=='extra-revision-field':packet['revision']['hidden_harness']='secret';value['messages'][1]['content']=EXPORTED_TASK_PREFIX+json.dumps(packet)
    else:
        raw=json.dumps(packet,ensure_ascii=False)
        needle='"title": "Napraw interfejs wyceny CREMA"'
        raw=raw.replace(needle,needle+', "title": "duplicate"')
        value['messages'][1]['content']=EXPORTED_TASK_PREFIX+raw
    write(path,value)
    with pytest.raises(ValueError,match='prefix|packet|Duplicate'):validate(case)


@pytest.mark.parametrize('damage,match',[('raw','both corrected'),('preserved','Exactly index'),
    ('before','before/after'),('assessment','assessment'),('screenshot','screenshot')])
def test_meaningful_tampering_fails_closed(case,damage,match):
    if damage=='raw':
        value=json.loads(case['response'].read_text());parsed=json.loads(value['content']);parsed['changes'].pop('style.css')
        value['content']=json.dumps(parsed);write(case['response'],value)
    elif damage=='preserved':
        value=json.loads(case['repair'].read_text());value['final_sources']['app.js']='changed';write(case['repair'],value)
    elif damage=='before':
        value=json.loads(case['before'].read_text());next(x for x in value['checks'] if x['name']=='mobile-menu-links-in-viewport')['passed']=True;value['status']='passed';write(case['before'],value)
    elif damage=='assessment':
        value=json.loads(case['assessment'].read_text());value['frozen_http_probes_passed']=18;write(case['assessment'],value)
    else:(case['after'].parent/'desktop-full.png').write_bytes(b'changed')
    with pytest.raises(ValueError,match=match):validate(case)
