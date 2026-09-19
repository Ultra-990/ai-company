import copy
import json
from hashlib import sha256
from pathlib import Path

import pytest

from scripts import draft_repair_examples as lab
from scripts.prepare_training_data import validate_dataset


def run_result(ok=True):
    isolation = dict.fromkeys(('non_root','capabilities_dropped','no_new_privileges',
        'seccomp','no_docker_socket','no_host_home','no_gpu_device',
        'network_only_loopback','readonly_root','readonly_source'),True)
    return {'reason':None,'cleanup_confirmed':True,'oom_killed':False,
            'exit_code':0 if ok else 1,'cli_exit_code':0 if ok else 1,
            'log':json.dumps({'schema':'python-web-test.v1','isolation':isolation,
                'tests_ok':ok,'http_ok':True,'source_not_exposed':True,
                'errors':[],'tests_log':'OK' if ok else 'FAIL: regression'})}


def test_default_has_no_inference_or_container(monkeypatch,capsys):
    monkeypatch.setattr('sys.argv',['draft_repair_examples.py'])
    monkeypatch.setattr(lab,'configuration',lambda: pytest.fail('Unexpected inference setup'))
    monkeypatch.setattr(lab,'runner_configuration',lambda: pytest.fail('Unexpected runner setup'))
    assert lab.main()==0
    assert json.loads(capsys.readouterr().out)['containers_started'] is False


@pytest.mark.parametrize('content',[
    '{"source":"short"}', '{"source":null}', '{"source":42}',
    '{"source":"def f(): pass","test_app.py":"pass"}',
    '{"source":"def f(): pass","source":"def g(): pass"}',
    '[]', 'x'*20001,
])
def test_rejects_extra_files_bad_content_and_duplicates(content):
    with pytest.raises(ValueError): lab.parse_source(content)


def test_source_is_only_returned_never_executed():
    source="raise RuntimeError('must not execute on host')\n"
    assert lab.parse_source(json.dumps({'source':source}))==source


@pytest.mark.parametrize('patch',[
    {'reason':'timeout'},{'cleanup_confirmed':False},{'oom_killed':True},
    {'exit_code':1},{'cli_exit_code':1},
])
def test_runner_failures_do_not_become_training_success(patch):
    with pytest.raises(ValueError): lab.inspect_run(run_result()|patch,True)


@pytest.mark.parametrize('patch',[
    {'tests_ok':False},{'http_ok':False},{'source_not_exposed':False},
    {'isolation':{}},{'errors':['timeout']},{'schema':'fake'},
])
def test_guest_failures_do_not_become_training_success(patch):
    result=run_result()
    result['log']=json.dumps(json.loads(result['log'])|patch)
    with pytest.raises(ValueError): lab.inspect_run(result,True)


def test_passing_reports_do_not_auto_approve():
    case=lab.CASES[0]
    assert lab.inspect_run(run_result(False),False)['tests_ok'] is False
    assert lab.inspect_run(run_result(),True)['tests_ok'] is True
    row=lab.candidate(case,lab.messages_for(case,'FAIL: baseline'),
                      '{"source":"def placeholder(): pass"}','synthetic-unit-test')
    assert row['review']['status']=='pending'
    assert row['review']['evidence']==[]
    assert row['skill']=='repair' and row['split']=='train'


def test_run_preserves_tests_and_leaves_production_alone(monkeypatch,tmp_path):
    monkeypatch.setattr('sys.argv',['draft_repair_examples.py','--generate','--limit','1'])
    monkeypatch.setattr(lab,'ROOT',tmp_path)
    # Only the /home filesystem check is substituted for this isolated tmp fixture.
    original_stat=lab.Path.stat
    def stat(path,*args,**kwargs):
        if str(path)=='/home': return original_stat(tmp_path,*args,**kwargs)
        return original_stat(path,*args,**kwargs)
    monkeypatch.setattr(lab.Path,'stat',stat)
    monkeypatch.setattr(lab,'configuration',lambda:{'model':'fake','digest':'fake'})
    monkeypatch.setattr(lab,'runner_configuration',lambda:{})
    monkeypatch.setattr(lab,'ensure_idle',lambda:None)
    calls=[]
    class Runner:
        def run(self,files,config,name):
            calls.append(copy.deepcopy(files))
            return run_result(len(calls)==2)
    class Model:
        def __init__(self,config): pass
        def complete(self,messages): return {'content':json.dumps({'source':'def fixed(): pass\n'})}
    monkeypatch.setattr(lab,'ContainerRunner',Runner)
    monkeypatch.setattr(lab,'OllamaProvider',Model)
    assert lab.main()==0
    assert len(calls)==2
    assert calls[0]['test_app.py']==calls[1]['test_app.py']==lab.CASES[0]['tests']
    assert calls[0]['app.py']==calls[1]['app.py']==lab.APP
    assert calls[0]['solution.py']!=calls[1]['solution.py']
    report=json.loads(next(tmp_path.glob('repair-drafts-*/report.json')).read_text())
    assert report['automatically_approved']==0
    assert report['training_started'] is False


def test_curated_repairs_bind_exact_code_tests_and_reports():
    root=Path(__file__).resolve().parents[1]
    raw=(root/'datasets/qwen/repair-batch-001.jsonl').read_bytes()
    rows,report=validate_dataset(raw)
    assert report['reviews']=={'approved':3}
    assert not report['export_ready']
    for row,fixture in zip(rows,lab.CASES):
        proof=row['review']['evidence'][0]
        proof_raw=(root/proof['reference'].split('#')[0]).read_bytes()
        assert sha256(proof_raw).hexdigest()==proof['sha256']
        entry=next(c for c in json.loads(proof_raw)['cases'] if c['id']==fixture['id'])
        assert entry['fixture']==fixture
        source=lab.parse_source(row['messages'][-1]['content'])
        assert source==entry['source']
        assert sha256(source.encode()).hexdigest()==entry['source_sha256']
        assert sha256(fixture['tests'].encode()).hexdigest()==entry['test_sha256']
        assert sha256(fixture['broken'].encode()).hexdigest()==entry['broken_sha256']
        assert sha256(lab.APP.encode()).hexdigest()==entry['health_stub_sha256']
        before=lab.inspect_run(entry['before'],False)
        lab.inspect_run(entry['after'],True)
        assert row['messages'][:2]==lab.messages_for(fixture,before['tests_log'])
        assert entry['before']['profile']==entry['after']['profile']
        assert proof['kind']=='independent_test'
        assert row['review']['reviewer']=='assistant-independent-code-review'
    _,combined=validate_dataset((root/'datasets/qwen/specialization-batch-001.jsonl').read_bytes()+b'\n'+raw)
    assert combined['counts']=={'train':12,'validation':0,'test':0}
    assert combined['reviews']=={'approved':12}
