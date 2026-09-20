"""Trusted binary bundle audit. Execute ONLY in the restricted container."""
from hashlib import sha256
import http.client
import json
from pathlib import Path
import signal
import subprocess
import sys
import time

sys.path.insert(0, '/workspace')
from runner_support import isolation_checks, TEST_LOADER, APP_LOADER, ENV


def fetch(path):
    connection = http.client.HTTPConnection('127.0.0.1', 8080, timeout=2)
    try:
        connection.request('GET', path)
        response = connection.getresponse()
        raw = response.read(4_000_001)
        if len(raw) > 4_000_000:
            raise ValueError('Response size limit')
        return response.status, raw, response.getheader('Content-Type', '')
    finally:
        connection.close()


def main():
    signal.alarm(35)
    report = dict(schema='studio-bundle-test.v1', isolation=isolation_checks(),
                  errors=[], checks=[], tests_ok=False, tests_log='')
    app = None
    try:
        if not all(report['isolation'].values()):
            raise ValueError('Isolation failed before execution')
        control = json.loads(Path('/workspace/bundle_control.json').read_bytes())
        hashes = control['checksums']
        if any(sha256((Path('/workspace') / name).read_bytes()).hexdigest() != digest for name, digest in hashes.items()):
            raise ValueError('Staged bytes changed')
        if control['path'] is None:
            with open('/tmp/tests.log', 'w+b') as log:
                result = subprocess.run([sys.executable, '-I', '-S', '-B', '-c', TEST_LOADER],
                    cwd='/workspace', env=ENV, stdout=log, stderr=log, timeout=15, check=False)
                log.seek(0)
                report['tests_log'] = log.read(4096).decode('utf-8', errors='replace')
            if result.returncode:
                raise ValueError('Independent or package tests failed')
            report['tests_ok'] = True
        app = subprocess.Popen([sys.executable, '-I', '-S', '-B', '-c', APP_LOADER],
            cwd='/workspace', env=ENV, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        deadline = time.monotonic() + 8
        while time.monotonic() < deadline:
            if app.poll() is not None:
                raise ValueError('App exited')
            try:
                status, raw, _ = fetch('/health')
                if status == 200 and json.loads(raw).get('status') == 'ok':
                    break
            except (OSError, ValueError, http.client.HTTPException):
                pass
            time.sleep(.1)
        else:
            raise ValueError('Health timeout')
        if control['path'] is not None:
            status, raw, content_type = fetch(control['path'])
            if len(raw) > 12000 or not content_type.startswith('application/json'):
                raise ValueError('Invalid API reply')
            report['response'] = dict(status=status, body=raw.decode(), content_type=content_type)
        else:
            for path, (name, content_type) in control['public'].items():
                status, raw, actual_type = fetch(path)
                if status != 200 or sha256(raw).hexdigest() != hashes[name] or actual_type != content_type:
                    raise ValueError('Public route bytes/type mismatch: ' + path)
                report['checks'].append(path)
            private = ['/' + name for name in hashes if '/' + name not in control['public'] and name != 'index.html']
            private += ['/bundle.json', '/runner_harness.py', '/runner_support.py', '/bundle_control.json',
                '/tests/test_independent_acceptance.py', '/static/', '/modules/', '/api/tasks',
                '/../etc/passwd', '/%2e%2e/etc/passwd', '/static/../app.py', '/static/%2e%2e/app.py']
            for path in private:
                if fetch(path)[0] != 404:
                    raise ValueError('Private route exposed: ' + path)
            report['checks'].append('private-routes-denied')
            for path, expected, total in control['probes']:
                status, raw, _ = fetch(path)
                payload = json.loads(raw)
                if status != expected or (expected == 200 and payload.get('total') != total) or (expected == 400 and not payload.get('error')):
                    raise ValueError('API regression: ' + path)
            report['checks'].append('independent-http-cases')
    except Exception as exc:
        report['errors'].append(type(exc).__name__ + ': ' + str(exc)[:200])
    finally:
        if app is not None:
            app.terminate()
            try:
                app.wait(timeout=1)
            except subprocess.TimeoutExpired:
                app.kill()
                app.wait(timeout=1)
    print(json.dumps(report))
    return 1 if report['errors'] else 0


if __name__ == '__main__':
    sys.exit(main())
