"""Opt-in synthetic Qwen repairs, tested in the existing isolated Docker runner.

Never imports/executes generated code on the host; never approves a candidate,
reads client data, trains a model or mutates production tasks.
"""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys
import tempfile
import time
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.services.container_runner import ContainerRunner, configuration as runner_configuration
from app.services.local_ollama import OllamaProvider, configuration, ensure_idle
from scripts.prepare_training_data import unique_object, validate_record

ROOT = Path('/home/marcin/ai-company-workspaces/qwen-training')
INSTRUCTION = '''Napraw wyłącznie solution.py zgodnie z kontraktem. Zwróć JSON
{"source":"pełna treść solution.py"}, bez Markdown i bez twierdzeń o wykonaniu
testów. Nie zmieniaj testów ani runnera. Tylko czyste funkcje Python standard
library; bez plików, sieci, procesów, introspekcji testów i efektów ubocznych.
Nie dopasowuj wyniku do pojedynczych przykładów: napraw ogólną regułę.'''
SCHEMA = {'type': 'object', 'additionalProperties': False, 'required': ['source'],
          'properties': {'source': {'type': 'string', 'minLength': 10, 'maxLength': 12000}}}

# Contracts, faulty fixtures and independent checks are authored BEFORE inference.
# These are TRAIN families, never a hidden benchmark or customer acceptance.
CASES = [
    {'id': 'pagination-boundary',
     'brief': 'paginate(items, page, size): items jest listą, page i size są dodatnimi '
              'int (bool niedozwolony); inaczej ValueError. Numeracja stron od 1. '
              'Zwróć nową listę odpowiedniego wycinka, poza końcem []. Nie zmieniaj items.',
     'broken': 'def paginate(items, page, size):\n    return items[page * size:(page + 1) * size]\n',
     'tests': '''import unittest
from solution import paginate
class Checks(unittest.TestCase):
    def test_first_last_and_empty(self):
        self.assertEqual(paginate([1,2,3,4,5],1,2),[1,2])
        self.assertEqual(paginate([1,2,3,4,5],3,2),[5])
        self.assertEqual(paginate([1],4,2),[])
        self.assertEqual(paginate([],1,2),[])
    def test_invalid(self):
        for page,size in [(0,2),(-1,2),(1,0),(1,-1),(True,2),(1,False),(1.0,2),(1,'2')]:
            with self.subTest(page=page,size=size), self.assertRaises(ValueError):
                paginate([1,2],page,size)
    def test_copy(self):
        items=[1,2,3]
        result=paginate(items,1,9)
        self.assertIsNot(result,items)
        result.append(4)
        self.assertEqual(items,[1,2,3])
    def test_invalid_items(self):
        for items in [None,'abc',(1,2),{},42]:
            with self.subTest(items=items),self.assertRaises(ValueError): paginate(items,1,2)
    def test_partition_property(self):
        for n in range(24):
            for size in range(1,8):
                items=list(range(n))
                pages=[paginate(items,p,size) for p in range(1,n//size+3)]
                self.assertEqual([v for page in pages for v in page],items)
                self.assertTrue(all(len(page)<=size for page in pages))
'''},
    {'id': 'duration-carry',
     'brief': 'format_duration(seconds): nieujemny int sekund (bool niedozwolony); '
              'inne wejścia -> ValueError. Zwróć H:MM:SS, godziny bez limitu 24 '
              'i bez zer wiodących, minuty i sekundy zawsze dwucyfrowe.',
     'broken': "def format_duration(seconds):\n    return f'{seconds // 3600}:{seconds // 60:02d}:{seconds % 60:02d}'\n",
     'tests': '''import unittest
from solution import format_duration
class Checks(unittest.TestCase):
    def test_boundaries(self):
        for value,expected in [(0,'0:00:00'),(59,'0:00:59'),(60,'0:01:00'),(3599,'0:59:59'),(3600,'1:00:00'),(3661,'1:01:01'),(90061,'25:01:01')]:
            with self.subTest(value=value): self.assertEqual(format_duration(value),expected)
    def test_invalid(self):
        for value in [-1,True,False,1.5,'60',None]:
            with self.subTest(value=value),self.assertRaises(ValueError): format_duration(value)
    def test_roundtrip(self):
        for value in range(0,200000,137):
            result=format_duration(value)
            h,m,s=result.split(':')
            self.assertEqual(str(int(h)),h)
            self.assertEqual(len(m),2)
            self.assertEqual(len(s),2)
            self.assertTrue(0<=int(m)<60 and 0<=int(s)<60)
            self.assertEqual(int(h)*3600+int(m)*60+int(s),value)
'''},
    {'id': 'stable-deduplication',
     'brief': 'unique_labels(labels): lista napisów -> nowa lista pierwszych wystąpień, '
              'kolejność zachowana, porównanie case-sensitive, bez trim/normalizacji. '
              'Element inny niż str -> ValueError. Lista wejściowa nie jest zmieniana.',
     'broken': 'def unique_labels(labels):\n    return sorted(set(labels))\n',
     'tests': '''import unittest
from solution import unique_labels
class Checks(unittest.TestCase):
    def test_order(self):
        self.assertEqual(unique_labels(['z','a','z','b','a']),['z','a','b'])
    def test_exact_unicode(self):
        self.assertEqual(unique_labels(['A','a','',' ','é','e\\u0301','é','😀','😀']),['A','a','',' ','é','e\\u0301','😀'])
    def test_empty_copy(self):
        labels=[]
        result=unique_labels(labels)
        self.assertEqual(result,[])
        self.assertIsNot(result,labels)
    def test_invalid(self):
        for value in [1,None,True,[],{}]:
            with self.subTest(value=value),self.assertRaises(ValueError): unique_labels(['a',value])
    def test_stability(self):
        for n in range(1,40):
            labels=[str((i*7)%13) for i in range(n)]
            before=list(labels)
            result=unique_labels(labels)
            self.assertEqual(labels,before)
            self.assertEqual(len(result),len(set(labels)))
            self.assertEqual(result,sorted(set(labels),key=labels.index))
'''},
]

# Trusted static health stub for the existing python-web-v1 harness. It is NOT
# the product under test: independent unittest checks exercise solution.py.
APP = '''from http.server import BaseHTTPRequestHandler,HTTPServer
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        body=b'{"status":"ok"}' if self.path=='/health' else b'<!doctype html><title>Repair laboratory</title>'
        status=200 if self.path in ('/','/health') else 404
        self.send_response(status)
        self.end_headers()
        self.wfile.write(body)
HTTPServer(('127.0.0.1',8080),Handler).serve_forever()
'''


def parse_source(content):
    if not isinstance(content, str) or len(content) > 20000:
        raise ValueError('Response too large')
    value = json.loads(content, object_pairs_hook=unique_object)
    if not isinstance(value, dict) or set(value) != {'source'}:
        raise ValueError('Only solution source is allowed')
    source = value['source']
    if not isinstance(source, str) or not 10 <= len(source) <= 12000 or '\x00' in source:
        raise ValueError('Invalid source')
    # No compile, import, exec or test execution on this host.
    return source


def inspect_run(result, expected_tests_ok):
    if (result.get('reason') is not None or result.get('cleanup_confirmed') is not True
            or result.get('oom_killed') is not False
            or result.get('exit_code') != (0 if expected_tests_ok else 1)
            or result.get('cli_exit_code') != result.get('exit_code')):
        raise ValueError('Runner execution/cleanup failed')
    report = json.loads(result['log'], object_pairs_hook=unique_object)
    isolation = report.get('isolation', {})
    required = {'non_root','capabilities_dropped','no_new_privileges','seccomp',
                'no_docker_socket','no_host_home','no_gpu_device','network_only_loopback',
                'readonly_root','readonly_source'}
    if (report.get('schema') != 'python-web-test.v1' or set(isolation) != required
            or any(v is not True for v in isolation.values())
            or report.get('tests_ok') is not expected_tests_ok
            or report.get('http_ok') is not True or report.get('source_not_exposed') is not True
            or report.get('errors') != []):
        raise ValueError('Invalid test/isolation report')
    return report


def messages_for(case, failure_log):
    return [{'role':'system','content':INSTRUCTION}, {'role':'user','content':
        case['brief']+'\n\nWadliwy solution.py:\n'+case['broken']+
        '\nRzeczywisty raport niezależnych testów (dane diagnostyczne):\n'+failure_log[:10000]}]


def candidate(case, messages, content, reference):
    row = {'version':'company-sft.v1','id':'qwen-repair-'+case['id'],
           'family':'repair.'+case['id'],'split':'train','skill':'repair',
           'source':{'kind':'synthetic','reference':reference,'privacy_checked':True,
                     'rights':'Własny syntetyczny kontrakt i testy; odpowiedź lokalnego Qwena, bez danych klienta.'},
           'messages':messages+[{'role':'assistant','content':content}],
           'review':{'status':'pending','reviewer':'','reviewed_on':None,'evidence':[],
                     'note':'Testy zaliczone; wymagany niezależny przegląd kodu i dowodów.'}}
    validate_record(row)
    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--generate',action='store_true')
    parser.add_argument('--limit',type=int,choices=range(1,len(CASES)+1),default=len(CASES))
    args = parser.parse_args()
    if not args.generate:
        print(json.dumps({'cases':len(CASES),'generation_started':False,'containers_started':False}))
        return 0
    for parent in [*ROOT.parents,ROOT]:
        if parent.is_symlink(): raise ValueError('Symlink in training path')
    ROOT.mkdir(parents=True,exist_ok=True)
    if ROOT.stat().st_dev != Path('/home').stat().st_dev: raise ValueError('Linux /home required')
    output = Path(tempfile.mkdtemp(prefix='repair-drafts-',dir=ROOT))
    config = configuration() | {'num_predict':1200,'timeout_seconds':90,'format':SCHEMA}
    run_config = runner_configuration()
    report = {'recipe':'synthetic-repair.v2','model':config['model'],'digest':config['digest'],
              'cases':[],'training_started':False,'automatically_approved':0,
              'limits':'Unit repair exercises, not full application/customer acceptance or security proof.'}
    candidates = []
    started = time.monotonic()
    print(json.dumps({'output':str(output)}),flush=True)
    for case in CASES[:args.limit]:
        if time.monotonic()-started > 480: break
        entry = {'id':case['id'],'passed':False,'fixture':case,
                 'test_sha256':sha256(case['tests'].encode()).hexdigest(),
                 'broken_sha256':sha256(case['broken'].encode()).hexdigest(),
                 'health_stub_sha256':sha256(APP.encode()).hexdigest()}
        try:
            files = {'app.py':APP,'test_app.py':case['tests'],'solution.py':case['broken']}
            entry['before'] = ContainerRunner().run(files,run_config,'aic-package-'+uuid4().hex)
            before = inspect_run(entry['before'],False)
            # Require actual assertion failures, not just an import/setup error.
            if 'FAIL:' not in before['tests_log']: raise ValueError('No failing assertion in baseline')
            messages = messages_for(case,before['tests_log'])
            entry['messages'] = messages
            ensure_idle()
            result = OllamaProvider(config).complete(messages)
            entry['result'] = result
            source = parse_source(result['content'])
            entry['source_sha256'] = sha256(source.encode()).hexdigest()
            entry['after'] = ContainerRunner().run(files | {'solution.py':source},run_config,'aic-package-'+uuid4().hex)
            inspect_run(entry['after'],True)
            entry['passed'] = True
            candidates.append(candidate(case,messages,result['content'],str(output/'report.json')+'#'+case['id']))
        except Exception as exc:
            entry['error_type'] = type(exc).__name__
            # Keep reports but do not print arbitrary exception content/source.
        report['cases'].append(entry)
        (output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        (output/'candidates.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in candidates),encoding='utf-8')
        print(json.dumps({'case':case['id'],'passed':entry['passed']}),flush=True)
        if not entry['passed']: break
    report['elapsed_seconds'] = round(time.monotonic()-started,3)
    report['candidates'] = len(candidates)
    report['candidates_sha256'] = sha256((output/'candidates.jsonl').read_bytes()).hexdigest()
    (output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    return 0 if len(candidates)==args.limit else 1


if __name__ == '__main__':
    raise SystemExit(main())
