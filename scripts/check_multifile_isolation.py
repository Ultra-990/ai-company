"""Default: read-only plan. --run --rental-ended: real bounded CPU-only Docker pilot.

Do NOT run the real pilot while Vast.ai rental is active. No models, production
DB, networking, installation, existing services or other containers are touched.
"""
import argparse
import json
from pathlib import Path
import sys
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.services.multifile_profile import inspect_sources


def sources(scenario):
    files = {
        'app.py': '''import os,json
from http.server import BaseHTTPRequestHandler,HTTPServer
from modules.logic import total
class Handler(BaseHTTPRequestHandler):
 def do_GET(self):
  if self.path not in ('/','/health'):self.send_error(404);return
  data=json.dumps({'status':'ok'}).encode() if self.path=='/health' else ('<!doctype html><title>Pilot</title>'+str(total(8,322))).encode()
  self.send_response(200);self.end_headers();self.wfile.write(data)
if __name__=='__main__':HTTPServer((os.environ['HOST'],int(os.environ['PORT'])),Handler).serve_forever()
''',
        'modules/__init__.py': '',
        'modules/logic.py': 'def total(hours,rate):\n return hours*rate\n',
        'tests/__init__.py': '',
        'tests/nested/__init__.py': '',
        'tests/nested/test_logic.py': '''import os,socket,unittest
from modules.logic import total
class Checks(unittest.TestCase):
 def test_total(self):self.assertEqual(total(8,322),2576)
 def test_non_root(self):self.assertNotEqual(os.geteuid(),0)
 def test_readonly_nested_file(self):
  with self.assertRaises(OSError):open('/workspace/modules/logic.py','w')
 def test_no_network(self):
  with self.assertRaises(OSError):socket.create_connection(('1.1.1.1',443),timeout=.2)
''',
        'index.html': '<!doctype html><title>Pilot fixture</title>',
        'README.md': 'Synthetic isolation pilot. Not a customer delivery.',
        'static/site.css': 'body { color: blue; }',
    }
    if scenario == 'no-tests':
        files['tests/nested/test_logic.py'] = '# No tests: must fail.\n'
    elif scenario == 'failed-test':
        files['modules/logic.py'] = 'def total(hours,rate):\n return 0\n'
    elif scenario == 'timeout':
        files['tests/nested/test_logic.py'] = 'import unittest,time\nclass Checks(unittest.TestCase):\n def test_stuck(self):time.sleep(60)\n'
    elif scenario == 'source-leak':
        files['app.py'] = files['app.py'].replace("  if self.path not in", "  if self.path=='/modules/logic.py':self.send_response(200);self.end_headers();self.wfile.write(b'leaked');return\n  if self.path not in")
    return files


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', action='store_true')
    parser.add_argument('--rental-ended', action='store_true', help='Explicit operator confirmation; never infer from GPU utilization.')
    parser.add_argument('--scenario', choices=['success', 'no-tests', 'failed-test', 'timeout', 'source-leak'], default='success')
    args = parser.parse_args(argv)
    if args.run and not args.rental_ended:
        parser.error('Nie uruchomiono: wymagane potwierdzenie zakończenia wynajmu --rental-ended.')
    files = sources(args.scenario)
    plan = inspect_sources(files)
    if not args.run:
        print(json.dumps(plan | {'mode': 'inspection_only', 'scenario': args.scenario}, ensure_ascii=False, indent=2))
        return 0 if plan['compatible'] else 1
    # Lazy import; the default inspection cannot accidentally touch Docker.
    from app.services.multifile_pilot import MultifilePilotRunner, pilot_configuration
    from app.services.package_runner import ISOLATION_KEYS
    result = MultifilePilotRunner().run(files, pilot_configuration(), 'aic-package-' + uuid4().hex)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    try:
        report = json.loads(result.get('log', ''))
        expected = 0 if args.scenario == 'success' else 1
        valid = (result.get('cleanup_confirmed') is True and result.get('reason') is None
                 and result.get('exit_code') == expected and result.get('cli_exit_code') == expected
                 and report.get('schema') == 'python-web-multifile-test.v1'
                 and set(report.get('isolation', {})) == ISOLATION_KEYS
                 and all(v is True for v in report['isolation'].values()))
        if args.scenario == 'success':
            valid = valid and all(report.get(k) is True for k in ('tests_ok', 'http_ok', 'source_not_exposed')) and report.get('errors') == []
        elif args.scenario == 'source-leak':
            valid = valid and report.get('tests_ok') is True and report.get('http_ok') is True and report.get('source_not_exposed') is False
        else:
            valid = valid and report.get('tests_ok') is False and bool(report.get('errors'))
    except (ValueError, TypeError, AttributeError, KeyError):
        valid = False
    return 0 if valid else 1


if __name__ == '__main__':
    sys.exit(main())
