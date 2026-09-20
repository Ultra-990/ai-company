"""Exercise orchestration with inert sources; generated code never runs on host."""
import fcntl
import json

import pytest

from scripts.function_school import run
from scripts.function_school.curriculum import CASES
from scripts.qwen_evaluation_catalog import reserved_cases

CONFIG = {'model':'fixture','digest':'0'*64,'num_ctx':16384,'num_predict':3200,'num_thread':4}
SOURCE = '# Inert fake model response; not an implementation and never executed.\n'
ISOLATION = dict.fromkeys(('non_root','capabilities_dropped','no_new_privileges','seccomp',
    'no_docker_socket','no_host_home','no_gpu_device','network_only_loopback','readonly_root','readonly_source'), True)


def execution(passed=True, count=8, log='', cleanup=True):
    report = {'schema':'python-web-test.v1', 'isolation':ISOLATION,
              'tests_ok':passed,'http_ok':True,'source_not_exposed':True,'errors':[],
              'tests_log':log+f'\nRan {count} tests in 0.001s\n'+('OK' if passed else 'FAILED (failures=1)')}
    return {'reason':None,'cleanup_confirmed':cleanup,'oom_killed':False,
            'exit_code':0 if passed else 1,'cli_exit_code':0 if passed else 1,
            'log':json.dumps(report)}


class Provider:
    def __init__(self): self.messages = []
    def complete(self, messages):
        self.messages.append(messages)
        return {'content':json.dumps({'source':SOURCE}), 'model':CONFIG['model'],
                'digest':CONFIG['digest'],'elapsed_seconds':0,'eval_count':10}


class Runner:
    def __init__(self, results): self.results=iter(results); self.calls=[]
    def run(self, files, config, name):
        self.calls.append(files)
        assert files['solution.py']==SOURCE
        assert files['app.py']==run.APP
        return next(self.results)


def test_curriculum_is_train_only_and_not_reserved_evaluation():
    reserved = reserved_cases()
    assert not {c['family'] for c in CASES} & {c['family'] for c in reserved}
    assert [run.test_count(c) for c in CASES]==[8,7,8]
    assert len({c['family'] for c in CASES})==3
    assert all('broken' not in c and 'solution' not in c for c in CASES)


def test_failure_drives_model_repair_and_exact_pending_candidate(tmp_path):
    case=CASES[0]; provider=Provider(); preflights=[]
    runner=Runner([execution(False,log='FAIL: test_aggregate_stock (test_app.Checks.test_aggregate_stock)\n'),execution()])
    folder=tmp_path/case['id']
    entry=run.teach_case(case,folder,CONFIG,{},2,provider,runner,lambda:preflights.append(True))
    assert entry['status']=='passed' and len(provider.messages)==2 and len(preflights)==4
    retry=json.loads(provider.messages[1][-1]['content'])
    assert retry['previous_source']==SOURCE and 'FAIL: test_aggregate_stock' in retry['independent_feedback']
    assert entry['lessons']==[{'check':'test_aggregate_stock','lesson':case['lessons']['test_aggregate_stock']}]
    assert all(c['test_app.py']==case['tests'] for c in runner.calls)
    row=run.training_candidate(case,entry,folder,CONFIG,'course-fixture')
    assert row['messages']==provider.messages[-1]+[{'role':'assistant','content':json.dumps({'source':SOURCE})}]
    assert row['review']['status']=='pending' and row['source']['privacy_checked'] is False
    assert row['skill']=='repair' and row['split']=='train'
    (folder/'attempt-2/solution.py').write_text(SOURCE+'# Manual alteration')
    with pytest.raises(ValueError,match='Changed model'): run.training_candidate(case,entry,folder,CONFIG,'course-fixture')


@pytest.mark.parametrize('artifact',['request.json','execution.json'])
def test_collection_rejects_changed_evidence(tmp_path, artifact):
    case=CASES[0]; folder=tmp_path/case['id']
    entry=run.teach_case(case,folder,CONFIG,{},1,Provider(),Runner([execution()]),lambda:None)
    target=folder/'attempt-1'/artifact
    target.write_text(target.read_text()+'\n')
    with pytest.raises(ValueError,match='Changed'): run.training_candidate(case,entry,folder,CONFIG,'course-fixture')


@pytest.mark.parametrize('result',[execution(cleanup=False),execution(count=0),execution(count=1)])
def test_infrastructure_or_missing_tests_never_teach_or_retry(tmp_path,result):
    provider=Provider()
    entry=run.teach_case(CASES[0],tmp_path/'case',CONFIG,{},3,provider,Runner([result]),lambda:None)
    assert entry['status']=='infrastructure_error' and len(provider.messages)==1 and entry['lessons']==[]


def test_failed_exercise_does_not_become_experience(tmp_path):
    provider=Provider()
    entry=run.teach_case(CASES[0],tmp_path/'case',CONFIG,{},2,provider,
                         Runner([execution(False),execution(False)]),lambda:None)
    assert entry['status']=='failed_tests' and len(provider.messages)==2 and entry['lessons']==[]
    with pytest.raises(ValueError,match='Only passing'):run.training_candidate(CASES[0],entry,tmp_path/'case',CONFIG,'course-fixture')


def test_invalid_json_can_be_repaired_without_host_execution(tmp_path):
    class InvalidThenValid(Provider):
        def complete(self,messages):
            result=super().complete(messages)
            if len(self.messages)==1:result['content']='invalid'
            return result
    provider=InvalidThenValid();runner=Runner([execution()])
    entry=run.teach_case(CASES[0],tmp_path/'case',CONFIG,{},2,provider,runner,lambda:None)
    assert [a['status'] for a in entry['attempts']]==['invalid_output','passed']
    assert len(runner.calls)==1 and (tmp_path/'case/attempt-1/response.json').exists()


def test_deadline_stops_new_attempts(tmp_path):
    times=iter([0,61]);provider=Provider()
    entry=run.teach_case(CASES[0],tmp_path/'case',CONFIG,{},3,provider,Runner([execution(False)]),
                         lambda:None,deadline=60,clock=lambda:next(times))
    assert entry['status']=='budget_exhausted' and len(provider.messages)==1


def test_full_course_keeps_failures_and_collects_only_passes(tmp_path,monkeypatch):
    monkeypatch.setattr(run,'ROOT',tmp_path/'school')
    if tmp_path.stat().st_dev != run.Path('/home').stat().st_dev:pytest.skip('Different filesystem')
    provider=Provider()
    out,report=run.execute(CONFIG,{},max_attempts=1,provider=provider,
        runner=Runner([execution(),execution(False,count=7),execution()]),preflight=lambda:None)
    assert report['status']=='needs_more_learning' and report['complete'] is True
    assert report['final_passes']==report['first_attempt_passes']==report['candidates']==2
    rows=[json.loads(line) for line in (out/'candidates.jsonl').read_text().splitlines()]
    assert [r['family'] for r in rows]==[CASES[0]['family'],CASES[2]['family']]
    assert report['weights_trained'] is False and report['automatically_approved']==0


def test_busy_resources_stop_before_inference(tmp_path):
    provider=Provider()
    def busy():raise ValueError('resources busy')
    entry=run.teach_case(CASES[0],tmp_path/'case',CONFIG,{},2,provider,Runner([]),busy)
    assert entry['status']=='infrastructure_error' and provider.messages==[]


def test_concurrent_course_is_rejected(tmp_path,monkeypatch):
    monkeypatch.setattr(run,'ROOT',tmp_path)
    if tmp_path.stat().st_dev != run.Path('/home').stat().st_dev:pytest.skip('Different filesystem')
    with (tmp_path/'.course.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX | fcntl.LOCK_NB)
        with pytest.raises(BlockingIOError):
            run.execute(CONFIG,{},provider=Provider(),runner=Runner([]),preflight=lambda:None)
