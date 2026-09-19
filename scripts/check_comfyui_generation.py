"""One fixed local Z-Image smoke generation on an owned temporary ComfyUI process."""
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
import uuid
from urllib.request import build_opener, ProxyHandler, Request

try:
    from scripts.start_comfyui import ROOT, SHARED_MODELS, command, check_shared_mount
except ModuleNotFoundError:
    from start_comfyui import ROOT, SHARED_MODELS, command, check_shared_mount

MODELS = ('diffusion_models/z_image_turbo_bf16.safetensors',
          'text_encoders/qwen_3_4b.safetensors', 'vae/ae.safetensors')
PROMPT = ('Product photograph of a single cobalt blue glass sphere on a clean ivory '
          'pedestal, soft studio lighting, elegant minimal composition, no text, no people.')


def workflow():
    # Derived from installed official image_z_image_turbo.json; native nodes only.
    return {
        '1': {'class_type': 'UNETLoader', 'inputs': {'unet_name': Path(MODELS[0]).name, 'weight_dtype': 'default'}},
        '2': {'class_type': 'CLIPLoader', 'inputs': {'clip_name': Path(MODELS[1]).name, 'type': 'lumina2', 'device': 'default'}},
        '3': {'class_type': 'VAELoader', 'inputs': {'vae_name': Path(MODELS[2]).name}},
        '4': {'class_type': 'CLIPTextEncode', 'inputs': {'text': PROMPT, 'clip': ['2', 0]}},
        '5': {'class_type': 'ConditioningZeroOut', 'inputs': {'conditioning': ['4', 0]}},
        '6': {'class_type': 'EmptySD3LatentImage', 'inputs': {'width': 768, 'height': 512, 'batch_size': 1}},
        '7': {'class_type': 'ModelSamplingAuraFlow', 'inputs': {'model': ['1', 0], 'shift': 3.0}},
        '8': {'class_type': 'KSampler', 'inputs': {'model': ['7', 0], 'positive': ['4', 0],
              'negative': ['5', 0], 'latent_image': ['6', 0], 'seed': 20260913,
              'steps': 8, 'cfg': 1.0, 'sampler_name': 'res_multistep', 'scheduler': 'simple', 'denoise': 1.0}},
        '9': {'class_type': 'VAEDecode', 'inputs': {'samples': ['8', 0], 'vae': ['3', 0]}},
        '10': {'class_type': 'SaveImage', 'inputs': {'images': ['9', 0], 'filename_prefix': 'local-smoke'}},
    }


def output_path(root, entry):
    if entry.get('type') != 'output':
        raise ValueError('Expected output image')
    name, sub = entry['filename'], entry.get('subfolder', '')
    if not isinstance(name, str) or not isinstance(sub, str):
        raise ValueError('Invalid image path')
    if Path(name).name != name or not name.endswith('.png') or '\\' in name + sub:
        raise ValueError('Invalid filename')
    path = root / sub / name
    if not path.resolve().is_relative_to(root.resolve()) or path.is_symlink():
        raise ValueError('Image escapes output directory')
    if not path.is_file() or not 0 < path.stat().st_size <= 16_000_000:
        raise ValueError('Missing or oversized image')
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', action='store_true')
    args = parser.parse_args()
    if not args.run:
        print('No generation. Use --run for one 768x512 image, 8 steps, existing weights only.')
        return
    if not check_shared_mount():
        raise SystemExit('Shared weights unavailable; will not mount or download.')
    opener = build_opener(ProxyHandler({}))

    def request(base, path, payload=None):
        data = None if payload is None else json.dumps(payload).encode()
        req = Request(base + path, data=data, headers={'Content-Type': 'application/json'})
        with opener.open(req, timeout=5) as response:
            raw = response.read(4_000_001)
        if len(raw) > 4_000_000:
            raise ValueError('Oversized API response')
        return json.loads(raw)

    def ensure_idle():
        queue = request('http://127.0.0.1:8188', '/queue')
        if queue['queue_running'] or queue['queue_pending']:
            raise RuntimeError('User ComfyUI busy; not interrupting it')
        if request('http://127.0.0.1:11434', '/api/ps')['models']:
            raise RuntimeError('Ollama busy; not unloading any model')

    ensure_idle()
    with socket.socket() as probe:
        probe.bind(('127.0.0.1', 8189))
    out = Path(tempfile.mkdtemp(prefix='generation-check-', dir=ROOT))
    report = {'passed': False, 'model_inference_succeeded': False, 'visual_reviewed': False,
              'application_integration_tested': False, 'published': False, 'models_downloaded': False,
              'custom_nodes_installed': False, 'workflow': workflow(), 'model_files': []}
    # Header validation only, not an authenticity claim or full tensor hash.
    from safetensors import safe_open
    for relative in MODELS:
        path = SHARED_MODELS / relative
        if not path.resolve().is_relative_to(SHARED_MODELS.resolve()):
            raise ValueError('Model escapes shared directory')
        with safe_open(path, framework='numpy') as header:
            report['model_files'].append({'relative': relative, 'bytes': path.stat().st_size,
                                          'tensor_count': len(header.keys()), 'full_hash_checked': False})
    (out / 'workflow-api.json').write_text(json.dumps(workflow(), indent=2))
    cmd = command()
    cmd[cmd.index('--port') + 1] = '8189'
    cmd += ['--base-directory', str(out / 'data'), '--output-directory', str(out / 'output')]
    env = os.environ.copy()
    env.update(HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', HF_HUB_DISABLE_TELEMETRY='1',
               DO_NOT_TRACK='1', OMP_NUM_THREADS='8')
    started = time.monotonic()
    with (out / 'server.log').open('w') as log:
        proc = subprocess.Popen(cmd, cwd=ROOT / 'ComfyUI', env=env, stdout=log, stderr=subprocess.STDOUT)
        try:
            deadline = time.monotonic() + 60
            while True:
                if proc.poll() is not None or time.monotonic() > deadline:
                    raise RuntimeError('ComfyUI startup failed')
                try:
                    report['system_stats'] = request('http://127.0.0.1:8189', '/system_stats')
                    break
                except OSError:
                    time.sleep(.5)
            ensure_idle()
            queued = request('http://127.0.0.1:8189', '/prompt',
                             {'prompt': workflow(), 'client_id': str(uuid.uuid4())})
            if queued.get('node_errors'):
                raise ValueError(str(queued['node_errors']))
            job = queued['prompt_id']
            report['prompt_id'] = job
            submitted = time.monotonic()
            deadline = submitted + 300
            while time.monotonic() < deadline:
                ensure_idle()  # if user starts work, stop only our own test server
                history = request('http://127.0.0.1:8189', '/history/' + job)
                if job in history:
                    report['history'] = history[job]
                    break
                if proc.poll() is not None:
                    raise RuntimeError('ComfyUI exited during generation')
                time.sleep(1)
            else:
                raise TimeoutError('Generation exceeded 300 seconds')
            report['generation_seconds'] = round(time.monotonic() - submitted, 3)
            status = report['history']['status']
            if status.get('status_str') != 'success' or not status.get('completed'):
                raise RuntimeError('Model execution failed; see history/server.log')
            entries = report['history']['outputs']['10']['images']
            if len(entries) != 1:
                raise ValueError('Expected exactly one image')
            path = output_path(out / 'output', entries[0])
            from PIL import Image, ImageStat
            with Image.open(path) as img:
                img.load()
                if img.size != (768, 512) or img.format != 'PNG':
                    raise ValueError('Unexpected image format or dimensions')
                std = ImageStat.Stat(img.convert('RGB')).stddev
                if max(std) < 1:
                    raise ValueError('Nearly uniform output')
            report.update(passed=True, model_inference_succeeded=True, image=str(path),
                          image_sha256=hashlib.sha256(path.read_bytes()).hexdigest(), pixel_stddev=std)
        except Exception as exc:
            report['error'] = f'{type(exc).__name__}: {exc}'
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=15)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=5)
            report['own_service_stopped'] = proc.poll() is not None
    report['elapsed_seconds'] = round(time.monotonic() - started, 3)
    (out / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(json.dumps({'report': str(out / 'report.json'), 'passed': report['passed'],
                      'image': report.get('image'), 'error': report.get('error')}, ensure_ascii=False))
    raise SystemExit(0 if report['passed'] else 1)


if __name__ == '__main__':
    main()
