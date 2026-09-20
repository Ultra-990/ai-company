"""Container only: PNG inventory bytes, private routes, unittest and stateless preview."""
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


def fetch(path, limit=4_000_000):
    connection = http.client.HTTPConnection('127.0.0.1', 8080, timeout=2)
    try:
        connection.request('GET', path)
        response = connection.getresponse()
        raw = response.read(limit + 1)
        if len(raw) > limit:
            raise ValueError('Response too large')
        return response.status, raw, response.getheader('Content-Type', '')
    finally:
        connection.close()


def main():
    signal.alarm(35)
    report = dict(schema='python-web-media-test.v1', isolation=isolation_checks(), errors=[],
        tests_ok=False, http_ok=False, source_not_exposed=False, assets_ok=False, tests_log='')
    app = None
    try:
        if not all(report['isolation'].values()):
            raise ValueError('Isolation failed before application execution')
        control = json.loads(Path('/workspace/media_control.json').read_bytes())
        path = control['path']
        if path is not None:
            report['schema'] = 'python-web-media-preview.v1'
        hashes = control['hashes']
        if any(sha256((Path('/workspace') / name).read_bytes()).hexdigest() != digest for name, digest in hashes.items()):
            raise ValueError('Staged bytes changed')
        if path is None:
            with open('/tmp/tests.log', 'w+b') as log:
                tests = subprocess.run([sys.executable, '-I', '-S', '-B', '-c', TEST_LOADER],
                    cwd='/workspace', env=ENV, stdout=log, stderr=log, timeout=15, check=False)
                log.seek(0)
                report['tests_log'] = log.read(4096).decode('utf-8', errors='replace')
            if tests.returncode:
                raise ValueError('Unit tests failed or none found')
            report['tests_ok'] = True
        app = subprocess.Popen([sys.executable, '-I', '-S', '-B', '-c', APP_LOADER],
            cwd='/workspace', env=ENV, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        deadline = time.monotonic() + 8
        while time.monotonic() < deadline:
            if app.poll() is not None:
                raise ValueError('Application exited')
            try:
                status, raw, _ = fetch('/health', 12000)
                if status == 200 and json.loads(raw).get('status') == 'ok': break
            except (OSError, ValueError, http.client.HTTPException):
                pass
            time.sleep(.1)
        else:
            raise ValueError('Health timeout')
        if path is not None:
            status, raw, content_type = fetch(path, 18000 if path == '/' else 12000)
            report['response'] = dict(status=status, body=raw.decode(), content_type=content_type[:100])
        else:
            for route, (name, content_type) in control['public'].items():
                status, raw, actual_type = fetch(route)
                if status != 200 or sha256(raw).hexdigest() != hashes[name] or content_type not in actual_type:
                    raise ValueError('Missing/changed public file: ' + name)
            report['assets_ok'] = report['http_ok'] = True
            public_names = {v[0] for v in control['public'].values()}
            private = ['/' + name for name in hashes if name not in public_names]
            private += ['/runner_harness.py', '/runner_support.py', '/media_control.json', '/static/',
                '/../etc/passwd', '/%2e%2e/etc/passwd', '/static/../app.py', '/modules/', '/tests/']
            if any(fetch(route)[0] not in (400, 403, 404) for route in private):
                raise ValueError('Private sources exposed')
            report['source_not_exposed'] = True
    except Exception as exc:
        report['errors'].append(type(exc).__name__ + ': ' + str(exc)[:200])
    finally:
        if app is not None:
            app.terminate()
            try: app.wait(timeout=1)
            except subprocess.TimeoutExpired: app.kill(); app.wait(timeout=1)
    encoded = json.dumps(report, ensure_ascii=True)
    if len(encoded.encode()) > 30000:
        report.pop('response', None)
        report['errors'].append('Serialized response limit')
        encoded = json.dumps(report)
    print(encoded)
    return 1 if report['errors'] else 0


if __name__ == '__main__':
    sys.exit(main())
