"""Guards for authorship, immutable evidence and feedback-driven local repair."""
from pathlib import Path
import json
import pytest
from scripts.web_school import run

SOURCES = {
    'index.html':'<!doctype html><html><h1>Test</h1><script src="app.js" defer></script></html>',
    'style.css':'body { margin: 0; color: #123456; }',
    'app.js':'document.body.dataset.example = "fixture";',
}
CONFIG = {'model':'fixture','digest':'0'*64,'num_ctx':16384,'num_predict':4096,'num_thread':4}


@pytest.mark.parametrize('raw',[
    '{"content":"'+('a'*31)+'","content":"'+('b'*31)+'"}',
    json.dumps({'content':'a'*31,'filename':'../../escape.js'}),
    json.dumps({'content':'```javascript\n'+'a'*40+'\n```'}),
    json.dumps({'content':'a'*30+'\x00'}), json.dumps({'content':123}),
])
def test_source_contract_rejects_ambiguous_or_wrapped_responses(raw):
    with pytest.raises(ValueError): run.parse_source(raw)


@pytest.mark.parametrize('extra',[
    '<script>alert(1)</script>','<iframe src="app.js"></iframe>',
    '<img src="http://127.0.0.1:8000/api/tasks">','<a href="https://example.com">X</a>',
    '<button onclick="x()">X</button>','<meta http-equiv="refresh" content="0;url=//bad">',
])
def test_html_cannot_request_other_services_or_inline_execution(extra):
    with pytest.raises(ValueError):run.validate_sources(SOURCES|{'index.html':SOURCES['index.html']+extra})


def test_wrong_file_type_and_duplicate_ids_cannot_pass_as_a_website():
    with pytest.raises(ValueError):run.validate_sources(SOURCES|{'style.css':SOURCES['index.html']})
    with pytest.raises(ValueError):run.validate_sources(SOURCES|{
        'index.html':SOURCES['index.html']+'<section id="checkout"><button id="checkout">Go</button></section>'})


def test_learning_facts_require_failed_then_passing_independent_checks():
    failure = {'evaluation':{'passed':False,'checks':[{'name':'cart-two-items','passed':False}]}}
    success = {'evaluation':{'passed':True,'checks':[{'name':'cart-two-items','passed':True}]}}
    assert run.failure_lessons([failure])==[]
    assert run.failure_lessons([success])==[]
    assert run.failure_lessons([failure,success])==[{'skill':'cart','lesson':run.LESSONS['cart']}]


def test_repair_authorship_and_tamper_rejection(tmp_path,monkeypatch):
    monkeypatch.setattr(run,'ROOT',tmp_path/'school')
    monkeypatch.setattr(run,'check_idle',lambda:None)
    calls=[]
    class Provider:
        def complete(self,messages):
            text=messages[-1]['content']
            request=json.JSONDecoder().raw_decode(text[text.index('{"brief"'):])[0];calls.append(request)
            if request.get('task')=='diagnose':
                return {'content':json.dumps({'content':'Diagnose the state update and preserve the complete acceptance contract.'}),
                        'elapsed_seconds':0,'eval_count':1}
            source=SOURCES[request['requested_file']]+(' ' if len(calls)>3 else '')
            return {'content':json.dumps({'content':source}),'elapsed_seconds':0,'eval_count':1,
                    'model':CONFIG['model'],'digest':CONFIG['digest']}
    evaluations=[]
    def examiner(files,folder,variant):
        passed=bool(evaluations)
        result={'passed':passed,'checks':[{'name':'cart-two-items','passed':passed}],
                'source_sha256':{n:run.digest(s) for n,s in files.items()},
                'examiner_sha256':run.examiner_hash()}
        evaluations.append(result);return result
    # tmp_path can reside on /tmp; production filesystem check is specifically /home.
    home_dev=Path('/home').stat().st_dev
    if tmp_path.stat().st_dev!=home_dev:pytest.skip('Test temporary filesystem differs from /home')
    out,report=run.teach(CONFIG,0,2,[],Provider(),examiner)
    assert report['status']=='functional_pass' and report['weights_trained'] is False
    assert len(calls)==7 and not calls[0]['independent_failures']
    assert calls[3]['independent_failures']==evaluations[0]['checks']
    assert calls[3]['task']=='diagnose' and calls[4]['local_model_diagnosis']
    for number in [1,2]:
        for name in run.FILES:
            raw=json.loads((out/f'attempt-{number}'/(name+'.response.json')).read_text())
            assert (out/f'attempt-{number}'/name).read_text()==run.parse_source(raw['content'])
    assert run.load_experience(out)==report['experience']
    from scripts.web_school.collect import collect
    collected=collect(out)
    assert collected['records']==3 and collected['auto_approved'] is False
    records=[json.loads(line) for line in (out/'training-candidates.jsonl').read_text().splitlines()]
    assert all(r['review']['status']=='pending' and r['split']=='train' for r in records)
    assert len({r['family'] for r in records})==1
    with pytest.raises(FileExistsError):collect(out)
    from scripts.web_school import recheck
    monkeypatch.setattr(recheck,'ROOT',run.ROOT)
    replay,replayed=recheck.recheck(out,examiner)
    assert replayed['inference_performed'] is False and replayed['status']=='functional_pass'
    assert (replay/'attempt-2/app.js').read_bytes()==(out/'attempt-2/app.js').read_bytes()
    (out/'attempt-2/app.js').write_text(SOURCES['app.js']+'changed')
    with pytest.raises(ValueError,match='Source changed'):run.load_experience(out)


def test_false_self_approval_never_becomes_experience(tmp_path,monkeypatch):
    monkeypatch.setattr(run,'ROOT',tmp_path)
    run.save(tmp_path/'report.json',{'schema':'local-web-school.v1','status':'functional_pass',
        'examiner_sha256':run.examiner_hash(),'attempts':[{'evaluation':{'passed':True,'checks':[]}}]})
    with pytest.raises((ValueError,FileNotFoundError)):run.load_experience(tmp_path)


def test_static_failure_lesson_replays_exact_model_response(tmp_path,monkeypatch):
    monkeypatch.setattr(run,'ROOT',tmp_path)
    out=tmp_path/'run';out.mkdir()
    for i in (1,2):
        folder=out/f'attempt-{i}';folder.mkdir()
        for name,source in SOURCES.items():
            if i==1 and name=='style.css':source=SOURCES['index.html']
            (folder/name).write_text(source)
            run.save(folder/(name+'.response.json'),{'content':json.dumps({'content':source})})
    evaluation={'passed':True,'checks':[{'name':'example','passed':True}],
                'source_sha256':{n:run.digest(s) for n,s in SOURCES.items()},
                'examiner_sha256':run.examiner_hash()}
    run.save(out/'attempt-2/evaluation.json',evaluation)
    run.save(out/'report.json',{'schema':'local-web-school.v1','status':'functional_pass',
        'examiner_sha256':run.examiner_hash(),'experience':[],
        'attempts':[{'contract_failure':[{'name':'source-contract','passed':False}]},
                    {'evaluation':evaluation}]})
    assert run.load_experience(out)[0]['skill']=='source'
    (out/'attempt-1/style.css').write_text(SOURCES['style.css'])
    with pytest.raises(ValueError,match='Failed source changed'):run.load_experience(out)
    # A failed run can seed a model revision only with exact source/evaluation evidence.
    evaluation['passed']=False;evaluation['checks'][0]['passed']=False
    run.save(out/'attempt-2/evaluation.json',evaluation)
    report=json.loads((out/'report.json').read_text())
    report.update(status='needs_more_learning',variant=0)
    report['attempts'][-1]['evaluation']=evaluation
    run.save(out/'report.json',report)
    revision=run.load_revision(out)
    assert revision['files']==SOURCES and revision['feedback']==evaluation['checks']
    (out/'attempt-2/app.js').write_text(SOURCES['app.js']+'changed')
    with pytest.raises(ValueError,match='Edited model source'):run.load_revision(out)
