"""Desktop entry: reuse local ComfyUI or start one background instance."""
import fcntl
import json
from pathlib import Path
import socket
import subprocess
import time
from urllib.request import build_opener, ProxyHandler

try:
    from scripts.start_comfyui import check_shared_mount
except ModuleNotFoundError:
    from start_comfyui import check_shared_mount

ROOT = Path('/home/marcin/ai-company-workspaces/comfyui')
URL = 'http://127.0.0.1:8188'
START = Path(__file__).with_name('start_comfyui.py')


def ready():
    try:
        with build_opener(ProxyHandler({})).open(URL + '/system_stats', timeout=2) as response:
            value = json.loads(response.read(262144))
        return isinstance(value, dict) and bool(value.get('system', {}).get('comfyui_version'))
    except (OSError, ValueError, AttributeError):
        return False


def open_browser():
    subprocess.run(['xdg-open', URL], check=True, timeout=15)


def main():
    if not check_shared_mount():
        subprocess.run(['notify-send', '--urgency=normal', 'ComfyUI — modele Windows niedostępne',
                        'Dysk modeli nie jest zamontowany. Nie pobieraj wag ponownie. '
                        'Przywróć dostęp tylko do odczytu do /media/marcin/Windows. '
                        'Lokalne modele nadal mogą działać.'], check=False, timeout=10)
    if ready():
        open_browser()
        return
    # The server inherits the lock descriptor, keeping it for its lifetime.
    with (ROOT / 'desktop.lock').open('a') as lock:
        owns_lock = True
        try:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            owns_lock = False
        process = None
        if owns_lock and not ready():
            try:
                with socket.socket() as port:
                    port.bind(('127.0.0.1', 8188))
            except OSError as exc:
                raise RuntimeError('Port 8188 jest zajęty. Nie zatrzymano żadnego procesu.') from exc
            with (ROOT / 'desktop.log').open('ab') as log:
                process = subprocess.Popen(
                    [str(ROOT / 'venv/bin/python'), str(START)],
                    cwd=START.parent.parent, stdout=log, stderr=subprocess.STDOUT,
                    stdin=subprocess.DEVNULL, start_new_session=True,
                    pass_fds=(lock.fileno(),))
        deadline = time.monotonic() + 90
        while time.monotonic() < deadline:
            if ready():
                open_browser()
                return
            if process is not None and process.poll() is not None:
                break
            time.sleep(.5)
        raise RuntimeError('ComfyUI nie jest gotowe. Szczegóły: ' + str(ROOT / 'desktop.log'))


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        subprocess.run(['notify-send', '--urgency=critical', 'ComfyUI', str(exc)],
                       check=False, timeout=10)
        raise SystemExit(1)
