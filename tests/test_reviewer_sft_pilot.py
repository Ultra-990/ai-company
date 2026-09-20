import json
from hashlib import sha256

import pytest

from scripts import train_reviewer_pilot as pilot
from scripts.prepare_training_data import validate_dataset
from scripts.qwen_evaluation_catalog import load_reviewer_suite


def test_reserved_exam_has_no_answers_in_messages_and_cannot_be_training():
    suite=load_reviewer_suite()
    assert len(suite['cases'])==3
    sample=json.loads((pilot.base.REPO/'datasets/qwen/specialization-batch-001.jsonl').read_text().splitlines()[0])
    for case in suite['cases']:
        text=json.dumps(case['messages'])
        assert 'expected_issues' not in text and 'correct_controls' not in text
        for answer in case['expected_issues'].values():assert answer not in text
        sample['family']=case['family']
        with pytest.raises(ValueError,match='reserved evaluation family'):
            validate_dataset((json.dumps(sample)+'\n').encode())
        sample['family']='renamed-exam'
        sample['messages'][1]['content']=case['brief']
        with pytest.raises(ValueError,match='evaluation brief reused'):
            validate_dataset((json.dumps(sample)+'\n').encode())


@pytest.mark.parametrize('changed',['response.json','request.json','article.md','sources.json','assessment.json'])
def test_private_content_or_assessment_tampering_is_rejected(tmp_path,monkeypatch,changed):
    monkeypatch.setattr(pilot,'PRIVATE',tmp_path)
    request=[{'role':'system','content':'fixture'},{'role':'user','content':'fixture'}]
    response={'content':'fixture result','model':'fixture','digest':'fixture'}
    pilot.base.save(tmp_path/'request.json',request);pilot.base.save(tmp_path/'response.json',response)
    (tmp_path/'article.md').write_text('fixture article');pilot.base.save(tmp_path/'sources.json',[])
    report={'status':'structurally_valid','authorship':{'editorial_review':'local_model'},
            'synthetic_development_exercise':True,'model':'fixture','digest':'fixture',
            'response_sha256':sha256(response['content'].encode()).hexdigest()}
    for name,key in [('request.json','request_sha256'),('article.md','article_sha256'),('sources.json','sources_sha256')]:
        report[key]=sha256((tmp_path/name).read_bytes()).hexdigest()
    pilot.base.save(tmp_path/'report.json',report)
    assessment={key:value for key,value in report.items() if key.endswith('sha256')}
    assessment.update(decision='approved_for_synthetic_training',privacy_checked=True,
                      original_model_content_edited=False,report_sha256=sha256((tmp_path/'report.json').read_bytes()).hexdigest())
    pilot.base.save(tmp_path/'assessment.json',assessment)
    row={'source':{'reference':str(tmp_path/'report.json')},
         'messages':request+[{'role':'assistant','content':response['content']}],
         'review':{'evidence':[{'kind':'content_review','reference':str(tmp_path/'assessment.json'),
                               'sha256':sha256((tmp_path/'assessment.json').read_bytes()).hexdigest()}]}}
    pilot.verify_review_record(row)
    if changed=='article.md':(tmp_path/changed).write_text('changed')
    else:
        obj=json.loads((tmp_path/changed).read_text())
        if changed=='response.json':obj['content']='changed'
        elif changed=='request.json':obj[1]['content']='changed'
        elif changed=='sources.json':obj.append({'changed':True})
        else:obj['decision']='rejected'
        pilot.base.save(tmp_path/changed,obj)
    with pytest.raises(ValueError):pilot.verify_review_record(row)


def test_fixed_second_recipe_and_original_are_distinct():
    if not (pilot.PRIVATE/'curated-rk_wk_sw/approved-records.jsonl').exists():
        pytest.skip('Private local reviewed dataset not shipped with repository')
    plan,rows,gate,roles,exam=pilot.load_protocol()
    assert len(rows)==17 and len(roles['cases'])==12 and len(exam['cases'])==3
    assert plan['training']['max_length']==4096 and plan['training']['max_steps']==18
    assert gate['export_ready'] is False
    original,*_=pilot.base.load_protocol()
    assert original['training']['max_length']==2048 and original['records']==14
