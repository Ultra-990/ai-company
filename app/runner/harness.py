"""Runs ONLY inside the disposable Python container.

Based on a local Qwen draft, reviewed/hardened independently: bounded files,
zero-test refusal, isolated imports, independent HTTP probes and process cleanup.
Never import this module into the application server.
"""
import http.client
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

WORKSPACE=Path('/workspace')
ENV={'PATH':'/usr/local/bin:/usr/bin:/bin','HOST':'127.0.0.1','PORT':'8080','LANG':'C.UTF-8'}


def isolation_checks():
    status=Path('/proc/self/status').read_text()
    fields=dict(line.split(':',1) for line in status.splitlines() if ':' in line)
    checks={'non_root':os.geteuid()!=0,'capabilities_dropped':int(fields['CapEff'].strip(),16)==0,
            'no_new_privileges':fields['NoNewPrivs'].strip()=='1','seccomp':fields['Seccomp'].strip()=='2',
            'no_docker_socket':not Path('/var/run/docker.sock').exists(),
            'no_host_home':not Path('/home/marcin').exists(),
            'no_gpu_device':not Path('/dev/nvidia0').exists(),
            'network_only_loopback':set(os.listdir('/sys/class/net'))=={'lo'}}
    for name,path in [('readonly_root','/root-write-probe'),('readonly_source','/workspace/write-probe')]:
        try:
            with open(path,'x') as stream:stream.write('probe')
            checks[name]=False
        except PermissionError:checks[name]=True
        except OSError as exc:checks[name]=exc.errno==30
    return checks


def fetch(path):
    conn=http.client.HTTPConnection('127.0.0.1',8080,timeout=.5)
    try:
        conn.request('GET',path);response=conn.getresponse();raw=response.read(262145)
        if len(raw)>262144:raise ValueError('HTTP response too large')
        return response.status,raw.decode('utf-8')
    finally:conn.close()


def main():
    signal.alarm(35)
    report={'schema':'python-web-test.v1','isolation':isolation_checks(),
            'tests_ok':False,'http_ok':False,'source_not_exposed':False,'tests_log':'','errors':[]}
    if not all(report['isolation'].values()):
        report['errors'].append('Isolation preflight failed; application NOT executed')
        print(json.dumps(report));return 2
    loader="""import sys,unittest
sys.path.insert(0,'/workspace')
suite=unittest.defaultTestLoader.discover('/workspace',pattern='test_app.py')
if suite.countTestCases()<1:sys.exit(3)
result=unittest.TextTestRunner(verbosity=2).run(suite)
sys.exit(0 if result.wasSuccessful() else 1)
"""
    with open('/tmp/tests.log','w+') as log:
        try:
            tests=subprocess.run([sys.executable,'-I','-S','-B','-c',loader],cwd=WORKSPACE,
                                 env=ENV,stdout=log,stderr=log,timeout=15,check=False)
            report['tests_ok']=tests.returncode==0
        except subprocess.TimeoutExpired:report['errors'].append('Unit-test timeout')
        log.seek(0);report['tests_log']=log.read(12000)
    app=None
    try:
        app=subprocess.Popen([sys.executable,'-I','-S','-B','/workspace/app.py'],cwd=WORKSPACE,
                             env=ENV,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        deadline=time.monotonic()+8
        while time.monotonic()<deadline:
            if app.poll() is not None:raise ValueError('Application exited before health check')
            try:
                status,body=fetch('/health')
                if status==200 and json.loads(body).get('status')=='ok':break
            except (OSError,ValueError,http.client.HTTPException):pass
            time.sleep(.1)
        else:raise ValueError('Health check timeout')
        status,body=fetch('/')
        report['http_ok']=status==200 and '<!doctype html' in body.lower()
        report['source_not_exposed']=all(fetch(path)[0] in (400,403,404) for path in
            ('/app.py','/test_app.py','/../etc/passwd','/%2e%2e/etc/passwd'))
    except (OSError,ValueError,http.client.HTTPException) as exc:
        report['errors'].append(type(exc).__name__+': '+str(exc)[:400])
    finally:
        if app is not None:
            app.terminate()
            try:app.wait(timeout=1)
            except subprocess.TimeoutExpired:app.kill();app.wait(timeout=1)
    print(json.dumps(report,ensure_ascii=True))
    return 0 if report['tests_ok'] and report['http_ok'] and report['source_not_exposed'] else 1


if __name__=='__main__':sys.exit(main())
