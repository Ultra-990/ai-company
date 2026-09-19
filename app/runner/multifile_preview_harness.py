"""Container only: one bounded GET, never import this module on the host."""
import http.client
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import time

APP_LOADER = """import sys,runpy
sys.path.insert(0,'/workspace')
runpy.run_path('/workspace/app.py',run_name='__main__')
"""


def isolation_checks():
    fields = dict(line.split(':', 1) for line in Path('/proc/self/status').read_text().splitlines() if ':' in line)
    checks = {'non_root': os.geteuid() != 0,
              'capabilities_dropped': int(fields['CapEff'].strip(), 16) == 0,
              'no_new_privileges': fields['NoNewPrivs'].strip() == '1',
              'seccomp': fields['Seccomp'].strip() == '2',
              'no_docker_socket': not Path('/var/run/docker.sock').exists(),
              'no_host_home': not Path('/home/marcin').exists(),
              'no_gpu_device': not Path('/dev/nvidia0').exists(),
              'network_only_loopback': set(os.listdir('/sys/class/net')) == {'lo'}}
    for name, path in [('readonly_root', '/root-write-probe'), ('readonly_source', '/workspace/write-probe')]:
        try:
            with open(path, 'x') as stream:
                stream.write('probe')
            checks[name] = False
        except OSError as exc:
            checks[name] = exc.errno in (13, 30)
    return checks


def fetch(path):
    connection = http.client.HTTPConnection('127.0.0.1', 8080, timeout=2)
    try:
        connection.request('GET', path)
        response = connection.getresponse()
        body = response.read(12001)
        if len(body) > 12000:
            raise ValueError('Preview response too large')
        return dict(status=response.status, body=body.decode('utf-8'),
                    content_type=response.getheader('Content-Type', '')[:100])
    finally:
        connection.close()


def main():
    signal.alarm(15)
    report = dict(schema='python-web-multifile-preview.v1', isolation=isolation_checks(), errors=[])
    app = None
    try:
        if not all(report['isolation'].values()):
            raise ValueError('Isolation preflight failed; application NOT executed')
        request = json.loads(Path('/workspace/preview_request.json').read_text())
        path = request['path']
        if path != '/' and not re.fullmatch(r'/api/[A-Za-z0-9_-]+(?:\?[A-Za-z0-9_=&.%+,-]{0,800})?', path):
            raise ValueError('Unsupported preview path')
        app = subprocess.Popen([sys.executable, '-I', '-S', '-B', '-c', APP_LOADER],
            cwd='/workspace', env={'PATH': '/usr/local/bin:/usr/bin:/bin', 'HOST': '127.0.0.1', 'PORT': '8080'},
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        deadline = time.monotonic() + 7
        while time.monotonic() < deadline:
            if app.poll() is not None:
                raise ValueError('Application exited')
            try:
                health = fetch('/health')
                if health['status'] == 200 and json.loads(health['body']).get('status') == 'ok':
                    break
            except (OSError, ValueError, AttributeError, http.client.HTTPException):
                pass
            time.sleep(.1)
        else:
            raise ValueError('Health check timeout')
        report['response'] = fetch(path)
    except (OSError, ValueError, KeyError, TypeError, http.client.HTTPException) as exc:
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
    return 0 if not report['errors'] else 1


if __name__ == '__main__':
    sys.exit(main())
