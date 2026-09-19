"""Start the separate local multimedia service; never enable cloud/custom nodes."""
from __future__ import annotations

import argparse
import os
import json
from pathlib import Path
import subprocess

ROOT = Path('/home/marcin/ai-company-workspaces/comfyui')
REVISION = '19e1058f4c445ef74047e77a23f9ca7684c1e4b6'
MODEL_CONFIG = Path(__file__).resolve().parents[1] / 'config/comfyui-model-paths.yaml'
SHARED_MODELS = Path('/media/marcin/Windows/Users/kusmi/Desktop/Comfy UI/models')


def check_shared_mount() -> bool:
    """Never mount or remount Windows; refuse using an existing writable mount."""
    if not SHARED_MODELS.is_dir():
        return False
    result = subprocess.run(['findmnt', '--json', '--target', str(SHARED_MODELS),
                             '--output', 'SOURCE,TARGET,OPTIONS'],
                            capture_output=True, text=True, check=True)
    filesystems = json.loads(result.stdout)['filesystems']
    if len(filesystems) != 1:
        raise RuntimeError('Cannot identify the shared model filesystem.')
    fs = filesystems[0]
    if (fs['source'] != '/dev/nvme0n1p4' or fs['target'] != '/media/marcin/Windows'
            or 'ro' not in fs['options'].split(',')
            or SHARED_MODELS.resolve() != SHARED_MODELS):
        raise RuntimeError('Shared Windows weights must be on the expected read-only mount.')
    return True


def command(root: Path = ROOT, *, cpu: bool = False) -> list[str]:
    return [str(root / 'venv/bin/python'), str(root / 'ComfyUI/main.py'),
            '--listen', '127.0.0.1', '--port', '8188',
            '--disable-api-nodes', '--disable-all-custom-nodes',
            '--disable-auto-launch', '--cache-none',
            '--extra-model-paths-config', str(MODEL_CONFIG),
            '--preview-method', 'none',
            *(['--cpu'] if cpu else ['--reserve-vram', '3'])]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cpu', action='store_true', help='CPU diagnostic, not fast generation')
    parser.add_argument('--check', action='store_true', help='Check files/revision only; do not start')
    args = parser.parse_args()
    shared_available = check_shared_mount()
    if not MODEL_CONFIG.is_file():
        raise SystemExit('Missing shared model path configuration.')
    if ROOT.resolve() != ROOT or ROOT.stat().st_dev != Path('/home/marcin').stat().st_dev:
        raise SystemExit('Expected a non-symlink directory on the Linux /home filesystem.')
    for path in (ROOT / 'ComfyUI/main.py', ROOT / 'venv/bin/python'):
        if not path.is_file():
            raise SystemExit(f'Missing installation file: {path}')
    revision = subprocess.check_output(['git', '-C', str(ROOT / 'ComfyUI'),
                                        'rev-parse', 'HEAD'], text=True).strip()
    if revision != REVISION:
        raise SystemExit('ComfyUI revision changed; review and retest before updating the pin.')
    cmd = command(cpu=args.cpu)
    print('Local ComfyUI: http://127.0.0.1:8188 · paid API and custom nodes disabled', flush=True)
    print('Shared Windows weights: ' + ('read-only' if shared_available else
          'unavailable — no automatic mount; local models remain usable'), flush=True)
    if args.check:
        print('Files and revision OK; service NOT started; models NOT verified.')
        return
    # Disable automatic HF downloads/telemetry. This is NOT a network sandbox.
    environment = os.environ.copy()
    environment.update(HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1',
                       HF_HUB_DISABLE_TELEMETRY='1', DO_NOT_TRACK='1',
                       OMP_NUM_THREADS='8')
    os.chdir(ROOT / 'ComfyUI')
    os.execve(cmd[0], cmd, environment)


if __name__ == '__main__':
    main()
