import json

import pytest

from scripts import check_technical_reviewer as lab


def response():
    return {'comments':[{'line':6,'quote':lab.ARTICLE.splitlines()[5], 'severity':'critical',
                        'issue':'Fixture issue','recommendation':'Fixture recommendation','source_ids':['qlora']}],
            'top_fixes':['Fixture top fix'], 'citation_needs':[{'line':10,
                'claim':lab.ARTICLE.splitlines()[9], 'evidence_required':'Dated provider pricing and terms'}],
            'additions':['Fixture example'], 'verdict':'needs_technical_revision',
            'reader_intent':'Fixture intent', 'uncertainty':'Fixture uncertainty'}


def test_expected_rubric_never_enters_model_messages():
    messages=lab.messages_for(lab.ARTICLE)
    assert len(messages)==2
    content=json.loads(messages[1]['content'])
    assert set(content)=={'review_date','audience','source_cards','article_lines'}
    assert content['source_cards']==lab.SOURCES
    assert len(content['article_lines'])==14
    for answer in lab.EXPECTED_ISSUES.values():assert answer not in messages[1]['content']


@pytest.mark.parametrize('change', ['quote','line','source','duplicate','type','extra','claim'])
def test_false_anchors_and_sources_are_rejected(change):
    value=response()
    if change=='quote':value['comments'][0]['quote']='Invented quote'
    if change=='line':value['comments'][0]['line']=999
    if change=='source':value['comments'][0]['source_ids']=['invented-source']
    if change=='duplicate':value['comments']*=2
    if change=='type':value['comments'][0]['line']=True
    if change=='extra':value['automatically_approved']=True
    if change=='claim':value['citation_needs'][0]['claim']='Not in the article'
    with pytest.raises(ValueError):lab.check_response(json.dumps(value),lab.ARTICLE)


def test_duplicate_json_keys_are_rejected():
    raw=json.dumps(response())
    with pytest.raises(ValueError):lab.check_response(raw[:-1]+',"verdict":"should_be_rewritten"}',lab.ARTICLE)


def test_coverage_is_not_semantic_acceptance():
    value=response()
    value['comments']=[dict(value['comments'][0],line=n,quote=lab.ARTICLE.splitlines()[n-1])
                       for n in lab.EXPECTED_ISSUES]
    review=lab.check_response(json.dumps(value),lab.ARTICLE)
    coverage=lab.coverage(review)
    assert coverage['missing_issue_lines']==[] and coverage['semantic_review']=='pending'
    assert 'passed' not in coverage


def test_markdown_preserves_model_wording_and_uses_verified_links():
    value=response();review=lab.check_response(json.dumps(value),lab.ARTICLE)
    markdown=lab.render(review)
    for key in ('issue','recommendation','quote'):assert value['comments'][0][key] in markdown
    assert 'https://arxiv.org/abs/2305.14314v1' in markdown
    assert '## Claims needing evidence' in markdown


@pytest.mark.parametrize('custom_sources',[False,True])
def test_run_preserves_raw_response_without_training_or_acceptance(tmp_path,monkeypatch,custom_sources):
    monkeypatch.setattr(lab,'ROOT',tmp_path)
    if tmp_path.stat().st_dev!=lab.Path('/home').stat().st_dev:pytest.skip('Different filesystem')
    config={'model':'fixture','digest':'0'*64,'num_ctx':16384,'num_predict':6000,'num_thread':4}
    sources=lab.SOURCES
    value=response()
    if custom_sources:
        from scripts.technical_review_curriculum import CASES
        sources=CASES[2]['sources']
        value['comments'][0]['source_ids']=[sources[0]['id']]
    raw=json.dumps(value)
    class Provider:
        def complete(self,messages):
            return {'content':raw,'model':config['model'],'digest':config['digest'],'eval_count':1,'elapsed_seconds':0}
    out,report=lab.execute(lab.ARTICLE,True,config,Provider(),lambda:None,sources=sources)
    assert report['status']=='structurally_valid' and report['semantic_review']=='pending'
    assert report['accepted'] is report['weights_trained'] is report['training_exported'] is False
    assert json.loads((out/'response.json').read_text())['content']==raw
    assert (out/'review.md').read_text()==lab.render(lab.check_response(raw,lab.ARTICLE,sources),sources)
    assert not (out/'candidates.jsonl').exists()
    feedback={'schema_version':'technical-review-feedback.v1',
              'parent_report_sha256':lab.sha256((out/'report.json').read_bytes()).hexdigest(),
              'parent_response_sha256':report['response_sha256'], 'decision':'needs_revision',
              'findings':[{'line':6,'problem':'Fixture issue','required_improvement':'Fixture instruction'}]}
    feedback_path=out/'teacher-feedback.json';lab.save(feedback_path,feedback)
    revision=lab.load_revision(out,feedback_path)
    assert revision['sources']==sources
    revised_messages=lab.messages_for(lab.ARTICLE,revision,sources)
    supplied=json.loads(revised_messages[1]['content'])
    assert supplied['previous_model_review']==value
    assert supplied['source_cards']==sources
    assert supplied['independent_feedback']==feedback
    revised,second_report=lab.execute(lab.ARTICLE,True,config,Provider(),lambda:None,revision,sources)
    assert revised!=out and second_report['revision_origin']['path']==str(out)
    assert second_report['status']=='unchanged_revision' and second_report['revision_changed'] is False
    assert json.loads((out/'response.json').read_text())['content']==raw
    assert second_report['accepted'] is False
    if custom_sources:
        with pytest.raises(ValueError,match='preserve'):
            lab.execute(lab.ARTICLE,True,config,Provider(),lambda:None,revision)
    (out/'article.md').write_text(lab.ARTICLE+'Changed')
    with pytest.raises(ValueError,match='Changed parent'):lab.load_revision(out,feedback_path)


def test_parent_feedback_cannot_authorize_other_report(tmp_path,monkeypatch):
    monkeypatch.setattr(lab,'ROOT',tmp_path/'reviews')
    outside=tmp_path/'outside';outside.mkdir()
    with pytest.raises(ValueError,match='Private non-symlink'):
        lab.load_revision(outside,tmp_path/'feedback.json')


def test_custom_evidence_pack_rejects_default_sources():
    from scripts.technical_review_curriculum import CASES
    sources=CASES[2]['sources']
    value=response()
    with pytest.raises(ValueError,match='Unknown'):
        lab.check_response(json.dumps(value),lab.ARTICLE,sources)
    value['comments'][0]['source_ids']=[sources[0]['id']]
    review=lab.check_response(json.dumps(value),lab.ARTICLE,sources)
    assert '(provided evidence card)' in lab.render(review,sources)
    assert 'arxiv.org' not in lab.render(review,sources)
    with pytest.raises(ValueError,match='Duplicate'):
        lab.validate_sources(sources*2)


def test_curriculum_rubrics_are_not_model_input():
    from scripts.technical_review_curriculum import CASES
    assert len({c['family'] for c in CASES})==6
    for case in CASES:
        user=json.loads(lab.messages_for(case['article'],sources=case['sources'])[1]['content'])
        assert user['source_cards']==case['sources']
        assert 'issues' not in user and 'controls' not in user
        assert set(case['issues']).isdisjoint(case['controls'])
        assert max([*case['issues'],*case['controls']])<=len(case['article'].splitlines())


def test_invalid_citation_anchor_can_be_revised_without_approving_original(tmp_path,monkeypatch):
    monkeypatch.setattr(lab,'ROOT',tmp_path)
    if tmp_path.stat().st_dev!=lab.Path('/home').stat().st_dev:pytest.skip('Different filesystem')
    config={'model':'fixture','digest':'0'*64,'num_ctx':16384,'num_predict':6000,'num_thread':4}
    value=response();value['citation_needs'][0]['claim']='Paraphrase absent from original'
    class Provider:
        def complete(self,messages):
            return {'content':json.dumps(value),'model':config['model'],'digest':config['digest'],
                    'elapsed_seconds':0,'eval_count':1}
    out,report=lab.execute(lab.ARTICLE,True,config,Provider(),lambda:None)
    assert report['status']=='invalid_output' and report['accepted'] is False
    feedback={'schema_version':'technical-review-feedback.v1',
              'parent_report_sha256':lab.sha256((out/'report.json').read_bytes()).hexdigest(),
              'parent_response_sha256':report['response_sha256'],'decision':'needs_revision',
              'findings':[{'line':10,'problem':'Invalid anchor','required_improvement':'Copy exact substring'}]}
    lab.save(out/'teacher-feedback.json',feedback)
    revision=lab.load_revision(out,out/'teacher-feedback.json')
    assert revision['previous_review']==value
    value['citation_needs'][0]['claim']=lab.ARTICLE.splitlines()[9]
    revised,result=lab.execute(lab.ARTICLE,True,config,Provider(),lambda:None,revision)
    assert result['status']=='structurally_valid' and result['accepted'] is False
    assert json.loads((out/'report.json').read_text())['status']=='invalid_output'
