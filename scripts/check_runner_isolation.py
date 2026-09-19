"""Explicit real Docker canary, only our disposable labelled container is removed."""
import json
import argparse
import sys
from pathlib import Path
from uuid import uuid4
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.services.container_runner import ContainerRunner, configuration

parser=argparse.ArgumentParser();parser.add_argument('--scenario',choices=['success','timeout','no-tests'],default='success')
args=parser.parse_args()

files={
'app.py':'''import os,json
from http.server import BaseHTTPRequestHandler,HTTPServer
class Handler(BaseHTTPRequestHandler):
 def do_GET(self):
  if self.path not in ('/','/health'):self.send_error(404);return
  body=json.dumps({'status':'ok'}).encode() if self.path=='/health' else b'<!doctype html><html><title>Canary</title><h1>Isolation canary</h1></html>'
  self.send_response(200);self.end_headers();self.wfile.write(body)
if __name__=='__main__':HTTPServer((os.environ['HOST'],int(os.environ['PORT'])),Handler).serve_forever()
''',
'test_app.py':'''import os,socket,unittest
class IsolationTests(unittest.TestCase):
 def test_no_privileges(self):self.assertNotEqual(os.geteuid(),0)
 def test_no_host_socket(self):self.assertFalse(os.path.exists('/var/run/docker.sock'))
 def test_read_only_source(self):
  with self.assertRaises(OSError):open('/workspace/forbidden','w')
 def test_no_external_network(self):
  with self.assertRaises(OSError):socket.create_connection(('1.1.1.1',443),timeout=.2)
''',
'index.html':'<!doctype html><html><title>Canary</title><h1>Isolation canary</h1></html>',
'README.md':'Known canary fixture, not a customer application.'}
if args.scenario=='timeout':
    files['test_app.py']='import unittest\nclass TimeoutTest(unittest.TestCase):\n def test_stuck(self):\n  while True:pass\n'
elif args.scenario=='no-tests':files['test_app.py']='# No tests; must fail, not count as success.\n'
runner=ContainerRunner();result=runner.run(files,configuration(),'aic-package-'+uuid4().hex)
print(json.dumps(result,ensure_ascii=False,indent=2))
expected=0 if args.scenario=='success' else 1
if result.get('exit_code')!=expected or result.get('cleanup_confirmed') is not True:sys.exit(1)
