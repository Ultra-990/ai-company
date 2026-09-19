"""Opt-in synthetic Qwen -> modules -> independent container checks.

No generated code is imported on the host. Reports are evidence of this single
case, not an owner acceptance, training dataset or general capability score.
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
from app.services.multifile_generation import INSTRUCTION, SOURCE_SCHEMA, parse_sources
from app.services.local_ollama import configuration, ensure_idle, OllamaProvider, generation_options
from app.services.execution_profiles import multifile_configuration
from app.services.multifile_pilot import MultifilePilotRunner
from app.services.multifile_preview import MultifilePreviewRunner, certified_configuration
from app.services.package_runner import ISOLATION_KEYS

ROOT = Path('/home/marcin/ai-company-workspaces/qwen-training')
BRIEF = '''Build a Polish project quote calculator. Function
modules.logic.quote(hours, rate) returns the product as a finite number.
Accept numeric strings or numbers, including zero and decimals; reject booleans,
negative values, missing/invalid/non-finite input and non-finite products with
ValueError. GET /api/quote?hours=8&rate=322 returns {"total":2576}.
Invalid or missing query values return HTTP 400 and JSON {"error":"..."}.
UI: labelled inputs #hours and #rate, button #calculate, output #result;
button uses the current input values, shows returned total or visible error.
Do not replace inputs with constants. CSS and JavaScript may be inline.
Small stateless demo: no tax, currency conversion, databases or external APIs.
Write unittest tests for the logic, README with limitations. Keep it compact.'''

# Fixed before generation; model never receives or rewrites these assertions.
ACCEPTANCE = '''import unittest
from modules.logic import quote
class IndependentAcceptance(unittest.TestCase):
 def test_values(self):
  for h,r,want in [(8,322,2576),(2.5,20,50),(0,322,0),(8,0,0),('3','7',21)]:
   with self.subTest(h=h,r=r):self.assertEqual(quote(h,r),want)
 def test_invalid(self):
  for h,r in [(-1,2),(1,-2),('x',2),(1,''),(None,2),(True,2),(2,False),('nan',2),(1,'inf'),(1e308,1e308)]:
   with self.subTest(h=h,r=r):
    with self.assertRaises(ValueError):quote(h,r)
'''
PROBES = [('/', 200, None), ('/api/quote?hours=8&rate=322', 200, 2576),
          ('/api/quote?hours=2.5&rate=20', 200, 50),
          ('/api/quote?hours=0&rate=20', 200, 0),
          ('/api/quote?hours=-1&rate=2', 400, None),
          ('/api/quote?hours=nan&rate=2', 400, None),
          ('/api/quote?hours=8', 400, None)]


def checked_report(result, schema):
    report = json.loads(result.get('log', ''))
    if not (result.get('exit_code') == 0 and result.get('cli_exit_code') == 0
            and result.get('cleanup_confirmed') is True and result.get('reason') is None
            and report.get('schema') == schema and report.get('errors') == []
            and set(report.get('isolation', {})) == ISOLATION_KEYS
            and all(v is True for v in report['isolation'].values())):
        raise ValueError('Execution, tests or isolation report failed')
    return report


def verify_response(report, path, status, total):
    response = report['response']
    if response['status'] != status:
        raise ValueError('Unexpected HTTP status: ' + path)
    if path == '/':
        if '<!doctype html' not in response['body'].lower():
            raise ValueError('Missing HTML document')
    else:
        payload = json.loads(response['body'])
        if status == 200:
            if type(payload.get('total')) not in (int, float) or payload['total'] != total:
                raise ValueError('Incorrect calculation: ' + path)
        elif not isinstance(payload.get('error'), str) or not payload['error'].strip():
            raise ValueError('Missing input validation error')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', action='store_true')
    args = parser.parse_args(argv)
    if not args.run:
        print(json.dumps({'model_invoked': False, 'brief': BRIEF,
                          'independent_tests_sha256': sha256(ACCEPTANCE.encode()).hexdigest(),
                          'http_checks': len(PROBES)}))
        return 0
    for parent in [*ROOT.parents, ROOT]:
        if parent.is_symlink():
            raise ValueError('Symlink in pilot path')
    ROOT.mkdir(parents=True, exist_ok=True)
    if ROOT.stat().st_dev != Path('/home').stat().st_dev:
        raise ValueError('Linux /home filesystem required')
    output = Path(tempfile.mkdtemp(prefix='multifile-generation-', dir=ROOT))
    config = configuration() | {'format': SOURCE_SCHEMA}
    report = {'schema': 'qwen-multifile-pilot.v1', 'status': 'incomplete',
              'brief': BRIEF, 'instruction': INSTRUCTION, 'schema_contract': SOURCE_SCHEMA,
              'model': config['model'], 'digest': config['digest'],
              'sampling': generation_options(config), 'attempts': 1,
              'independent_tests': ACCEPTANCE, 'probes': [], 'training_started': False,
              'accepted': False, 'deployed': False,
              'limitations': 'Single public synthetic case; no training export, no general quality claim. Browser interaction not checked by this script.'}
    def save():
        (output / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'report': str(output / 'report.json')}), flush=True)
    save()
    start = time.monotonic()
    stage = 'model'
    try:
        ensure_idle()
        report['generation'] = OllamaProvider(config).complete([
            {'role': 'system', 'content': INSTRUCTION}, {'role': 'user', 'content': BRIEF}])
        save()
        stage = 'parse'
        files = parse_sources(report['generation']['content'])
        if 'tests/test_independent_acceptance.py' in files:
            raise ValueError('Reserved acceptance path')
        report['source_checksums'] = {k: sha256(v.encode()).hexdigest() for k,v in files.items()}
        checked_files = files | {'tests/test_independent_acceptance.py': ACCEPTANCE}
        stage = 'tests'
        report['test_run'] = MultifilePilotRunner().run(checked_files, multifile_configuration(), 'aic-package-' + uuid4().hex)
        save()
        result = checked_report(report['test_run'], 'python-web-multifile-test.v1')
        if not all(result.get(k) is True for k in ('tests_ok', 'http_ok', 'source_not_exposed')):
            raise ValueError('Tests or source exposure check failed')
        stage = 'http'
        for path,status,total in PROBES:
            run = MultifilePreviewRunner(path).run(files, certified_configuration() | {'request_path':path}, 'aic-package-' + uuid4().hex)
            probe = {'path':path, 'expected_status':status, 'expected_total':total, 'run':run, 'passed':False}
            report['probes'].append(probe)
            save()
            result = checked_report(run, 'python-web-multifile-preview.v1')
            verify_response(result, path, status, total)
            probe['passed'] = True
            save()
        report['status'] = 'passed'
    except Exception as exc:
        report.update(status='failed', error_stage=stage, error_type=type(exc).__name__, error=str(exc)[:500])
    finally:
        report['elapsed_seconds'] = round(time.monotonic()-start, 3)
        save()
    print(json.dumps({k:report[k] for k in ('status','elapsed_seconds')}), flush=True)
    return 0 if report['status']=='passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
