"""Container-only, one bounded GET against an ephemeral application. No host import."""
import http.client
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time


def fetch(path):
    connection = http.client.HTTPConnection('127.0.0.1', 8080, timeout=2)
    try:
        connection.request('GET', path)
        response = connection.getresponse()
        body = response.read(12001)
        if len(body) > 12000:
            raise ValueError('Preview response too large')
        return {'status': response.status, 'body': body.decode('utf-8'),
                'content_type': response.getheader('Content-Type', '')[:100]}
    finally:
        connection.close()


def main():
    signal.alarm(15)
    request = json.loads(Path('/workspace/preview_request.json').read_text())
    # Fixed network namespace and runner options are enforced outside the guest.
    if os.geteuid() == 0 or set(os.listdir('/sys/class/net')) != {'lo'}:
        return 2
    app = subprocess.Popen([sys.executable, '-I', '-S', '-B', '/workspace/app.py'],
        cwd='/workspace', env={'PATH': '/usr/local/bin:/usr/bin:/bin',
        'HOST': '127.0.0.1', 'PORT': '8080'}, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        deadline = time.monotonic() + 7
        while time.monotonic() < deadline:
            if app.poll() is not None:
                raise ValueError('Application exited')
            try:
                response = fetch('/health')
                if response['status'] == 200 and json.loads(response['body']).get('status') == 'ok':
                    break
            except (OSError, ValueError, http.client.HTTPException):
                pass
            time.sleep(.1)
        else:
            raise ValueError('Health check timeout')
        response = fetch(request['path'])
        print(json.dumps({'schema': 'python-web-preview.v1', 'response': response}, ensure_ascii=True))
        return 0
    finally:
        app.terminate()
        try:
            app.wait(timeout=1)
        except subprocess.TimeoutExpired:
            app.kill()
            app.wait(timeout=1)


if __name__ == '__main__':
    sys.exit(main())
