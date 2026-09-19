"""Trusted prototype harness: ONLY for an isolated container, never import on host.

Not wired into the production runner. Requires a real isolation pilot before
activation. Sources are stdlib Python under modules/ and unittest under tests/.
"""
import http.client
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

WORKSPACE = Path('/workspace')
ENV = {'PATH': '/usr/local/bin:/usr/bin:/bin', 'HOST': '127.0.0.1',
       'PORT': '8080', 'LANG': 'C.UTF-8'}
TEST_LOADER = """import sys,unittest
sys.path.insert(0,'/workspace')
suite=unittest.defaultTestLoader.discover('/workspace/tests',pattern='test_*.py',top_level_dir='/workspace')
if suite.countTestCases()<1:sys.exit(3)
result=unittest.TextTestRunner(verbosity=2).run(suite)
sys.exit(0 if result.wasSuccessful() else 1)
"""
# -I intentionally drops script-directory imports. Add ONLY the approved source
# root, inside the container, after importing trusted stdlib bootstrap modules.
APP_LOADER = """import sys,runpy
sys.path.insert(0,'/workspace')
runpy.run_path('/workspace/app.py',run_name='__main__')
"""


def isolation_checks():
    fields = dict(line.split(':', 1) for line in Path('/proc/self/status').read_text().splitlines() if ':' in line)
    checks = {
        'non_root': os.geteuid() != 0,
        'capabilities_dropped': int(fields['CapEff'].strip(), 16) == 0,
        'no_new_privileges': fields['NoNewPrivs'].strip() == '1',
        'seccomp': fields['Seccomp'].strip() == '2',
        'no_docker_socket': not Path('/var/run/docker.sock').exists(),
        'no_host_home': not Path('/home/marcin').exists(),
        'no_gpu_device': not Path('/dev/nvidia0').exists(),
        'network_only_loopback': set(os.listdir('/sys/class/net')) == {'lo'},
    }
    for name, path in [('readonly_root', '/root-write-probe'), ('readonly_source', '/workspace/write-probe')]:
        try:
            with open(path, 'x') as stream:
                stream.write('probe')
            checks[name] = False
        except OSError as exc:
            checks[name] = exc.errno in (13, 30)
    return checks


def fetch(path):
    connection = http.client.HTTPConnection('127.0.0.1', 8080, timeout=.5)
    try:
        connection.request('GET', path)
        response = connection.getresponse()
        raw = response.read(262145)
        if len(raw) > 262144:
            raise ValueError('HTTP response too large')
        return response.status, raw.decode('utf-8')
    finally:
        connection.close()


def private_paths():
    # Read-only mount; inventory taken before untrusted tests or app can run.
    paths = ['/runner_harness.py', '/modules/', '/tests/', '/../etc/passwd', '/%2e%2e/etc/passwd']
    for path in sorted(WORKSPACE.rglob('*')):
        if path.is_symlink():
            raise ValueError('Unexpected source symlink')
        relative = path.relative_to(WORKSPACE).as_posix()
        if path.is_file() and relative not in {'index.html', 'style.css', 'app.js', 'runner_harness.py'} and not relative.startswith('static/'):
            paths.append('/' + relative)
    if len(paths) > 105:
        raise ValueError('Too many probe targets')
    return paths


def main():
    signal.alarm(35)
    report = dict(schema='python-web-multifile-test.v1', isolation=isolation_checks(),
                  tests_ok=False, http_ok=False, source_not_exposed=False, tests_log='', errors=[])
    app = None
    try:
        if not all(report['isolation'].values()):
            raise ValueError('Isolation preflight failed; application NOT executed')
        probes = private_paths()
        with open('/tmp/tests.log', 'w+b') as log:
            tests = subprocess.run([sys.executable, '-I', '-S', '-B', '-c', TEST_LOADER],
                                   cwd=WORKSPACE, env=ENV, stdout=log, stderr=log, timeout=15, check=False)
            log.seek(0)
            report['tests_log'] = log.read(4096).decode('utf-8', errors='replace')
        report['tests_ok'] = tests.returncode == 0
        if not report['tests_ok']:
            raise ValueError('Unit tests failed or no tests discovered; HTTP startup skipped')
        app = subprocess.Popen([sys.executable, '-I', '-S', '-B', '-c', APP_LOADER],
                               cwd=WORKSPACE, env=ENV, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        deadline = time.monotonic() + 8
        while time.monotonic() < deadline:
            if app.poll() is not None:
                raise ValueError('Application exited before health check')
            try:
                status, body = fetch('/health')
                if status == 200 and json.loads(body).get('status') == 'ok':
                    break
            except (OSError, ValueError, AttributeError, http.client.HTTPException):
                pass
            time.sleep(.1)
        else:
            raise ValueError('Health check timeout')
        status, body = fetch('/')
        report['http_ok'] = status == 200 and '<!doctype html' in body.lower()
        report['source_not_exposed'] = all(fetch(path)[0] in (400, 403, 404) for path in probes)
    except (OSError, ValueError, subprocess.TimeoutExpired, http.client.HTTPException) as exc:
        report['errors'].append(type(exc).__name__ + ': ' + str(exc)[:300])
    finally:
        if app is not None:
            app.terminate()
            try:
                app.wait(timeout=1)
            except subprocess.TimeoutExpired:
                app.kill()
                app.wait(timeout=1)
    print(json.dumps(report, ensure_ascii=True))
    return 0 if report['tests_ok'] and report['http_ok'] and report['source_not_exposed'] and not report['errors'] else 1


if __name__ == '__main__':
    sys.exit(main())
