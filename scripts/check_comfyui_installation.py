"""Bounded local service smoke test, no model inference, cloud calls or application DB."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import tempfile
import time
from urllib.request import build_opener, ProxyHandler

from start_comfyui import ROOT, command


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', action='store_true')
    parser.add_argument('--shared-models', action='store_true', help='Require the existing FLUX Klein base 4B set in API lists')
    args = parser.parse_args()
    if not args.run:
        print('Use --run to start and stop an isolated service check on 127.0.0.1:8189.')
        return
    subprocess.run([str(ROOT / 'venv/bin/python'),
                    str(Path(__file__).with_name('start_comfyui.py')), '--check'], check=True)
    with socket.socket() as probe:
        probe.bind(('127.0.0.1', 8189))  # refuse occupied port; never stop its owner
    out = Path(tempfile.mkdtemp(prefix='install-check-', dir=ROOT))
    cmd = command()
    cmd[cmd.index('--port') + 1] = '8189'
    # Keep ComfyUI's own metadata DB/temp/input/output away from real projects.
    cmd += ['--base-directory', str(out / 'data')]
    environment = os.environ.copy()
    environment.update(HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1',
                       HF_HUB_DISABLE_TELEMETRY='1', DO_NOT_TRACK='1', OMP_NUM_THREADS='8')
    opener = build_opener(ProxyHandler({}))
    report = {'passed': False, 'generation_tested': False,
              'models_downloaded': False, 'application_integration_tested': False,
              'paid_api_enabled': False, 'custom_nodes_enabled': False}
    with (out / 'server.log').open('w') as log:
        process = subprocess.Popen(cmd, cwd=ROOT / 'ComfyUI', env=environment,
                                   stdout=log, stderr=subprocess.STDOUT)
        try:
            deadline = time.monotonic() + 60
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    raise RuntimeError('ComfyUI exited during startup; see server.log')
                try:
                    with opener.open('http://127.0.0.1:8189/system_stats', timeout=2) as r:
                        stats = json.load(r)
                    break
                except OSError:
                    time.sleep(.5)
            else:
                raise TimeoutError('ComfyUI did not start within 60 seconds')
            with opener.open('http://127.0.0.1:8189/', timeout=5) as r:
                assert r.status == 200
                assert b'<html' in r.read(2_000_000).lower()
            with opener.open('http://127.0.0.1:8189/object_info', timeout=5) as r:
                info = json.load(r)
            assert 'KSampler' in info and 'SaveImage' in info
            if args.shared_models:
                required = {
                    'UNETLoader': ('unet_name', 'flux-2-klein-base-4b-fp8.safetensors'),
                    'CLIPLoader': ('clip_name', 'qwen_3_4b.safetensors'),
                    'VAELoader': ('vae_name', 'flux2-vae.safetensors'),
                }
                for node, (field, filename) in required.items():
                    assert filename in info[node]['input']['required'][field][0], filename
                report['shared_model_set_visible'] = {
                    node: filename for node, (_, filename) in required.items()}
                report['shared_model_generation_tested'] = False
            api_nodes = [key for key, value in info.items()
                         if str(value.get('python_module', '')).startswith('comfy_api_nodes')]
            assert not api_nodes, api_nodes
            with opener.open('http://127.0.0.1:8189/queue', timeout=5) as r:
                queue = json.load(r)
            assert not queue['queue_running'] and not queue['queue_pending']
            report.update(passed=True, system_stats=stats, node_count=len(info),
                          cloud_node_count=len(api_nodes), queue=queue)
        except Exception as exc:
            report['error'] = f'{type(exc).__name__}: {exc}'
        finally:
            process.terminate()
            try:
                process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
            report['own_service_stopped'] = process.poll() is not None
    report['server_log_sha256'] = hashlib.sha256((out / 'server.log').read_bytes()).hexdigest()
    (out / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(json.dumps({'report': str(out / 'report.json'), **report}, ensure_ascii=False, indent=2))
    raise SystemExit(0 if report['passed'] else 1)


if __name__ == '__main__':
    main()
