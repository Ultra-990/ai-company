import json
from hashlib import sha256

import pytest

from scripts import run_technical_review_school as school


def test_revision_manifest_preserves_json_roundtrip_and_rejects_tampering(tmp_path,monkeypatch):
    monkeypatch.setattr(school.lab,'ROOT',tmp_path)
    school.lab.save(tmp_path/'curriculum-snapshot.json',school.CASES)
    runs=[]
    for case in school.CASES:
        path=tmp_path/case['id'];path.mkdir()
        school.lab.save(path/'report.json',{'fixture':case['id']})
        runs.append({'case':case['id'],'path':str(path),
                     'report_sha256':sha256((path/'report.json').read_bytes()).hexdigest()})
    report={'schema':'technical-review-school.v1','status':'awaiting_independent_review',
            'runs':runs,'curriculum_sha256':sha256((tmp_path/'curriculum-snapshot.json').read_bytes()).hexdigest()}
    school.lab.save(tmp_path/'report.json',report)
    def load_revision(path,feedback):
        case=next(c for c in school.CASES if c['id']==path.name)
        return {'article':case['article'],'sources':case['sources']}
    monkeypatch.setattr(school.lab,'load_revision',load_revision)
    assert len(school.load_school_revisions(tmp_path))==6
    (tmp_path/'evaluation'/'report.json').write_text('{}')
    with pytest.raises(ValueError,match='Changed source school run'):
        school.load_school_revisions(tmp_path)


def test_pending_candidate_preserves_exact_output_and_rejects_changed_request(tmp_path):
    case=school.CASES[2]
    value={'comments':[],'top_fixes':['Fixture'], 'citation_needs':[],
           'additions':['Fixture'],'verdict':'needs_technical_revision',
           'reader_intent':'Fixture','uncertainty':'Fixture'}
    raw=json.dumps(value)
    request=school.lab.messages_for(case['article'],sources=case['sources'])
    school.lab.save(tmp_path/'request.json',request)
    school.lab.save(tmp_path/'response.json',{'content':raw})
    report={'status':'structurally_valid','response_sha256':sha256(raw.encode()).hexdigest(),
            'request_sha256':sha256((tmp_path/'request.json').read_bytes()).hexdigest()}
    row=school.candidate(case,tmp_path,report)
    assert row['review']['status']=='pending' and row['source']['privacy_checked'] is False
    assert row['messages']==request+[{'role':'assistant','content':raw}]
    (tmp_path/'request.json').write_text('[]')
    with pytest.raises(ValueError,match='intact'):school.candidate(case,tmp_path,report)


def test_feedback_only_omits_rejected_answer_and_keeps_teacher_findings():
    case=school.CASES[0]
    revision={'context_mode':'feedback_only','previous_review':{'rejected':'DO_NOT_COPY'},
              'feedback':{'findings':[{'required_improvement':'Fixture correction'}]}}
    messages=school.lab.messages_for(case['article'],revision,case['sources'])
    payload=json.loads(messages[1]['content'])
    assert 'previous_model_review' not in payload
    assert 'DO_NOT_COPY' not in json.dumps(messages)
    assert payload['independent_feedback']==revision['feedback']
    assert payload['source_cards']==case['sources']
