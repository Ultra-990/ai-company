"""Install the pinned official Surge bundle privately, without root or GUI."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import urllib.request
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.instruments import runtime

URL = 'https://github.com/surge-synthesizer/releases-xt/releases/download/1.3.4/surge-xt-linux-x64-1.3.4.deb'
PACKAGES = ['pedalboard==0.9.26', 'numpy==2.2.6', 'mido==1.3.3', 'packaging==25.0']


def install():
    root = runtime.ROOT
    if root.is_symlink(): raise ValueError('instrument_workspace_unsafe')
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    archive = root/'surge-xt-1.3.4.deb'
    if not archive.exists():
        temporary = root/'download.part'
        with urllib.request.urlopen(URL, timeout=60) as response, temporary.open('xb') as target:
            size = 0
            while block := response.read(1024**2):
                size += len(block)
                if size > 250*1024**2: raise ValueError('instrument_download_too_large')
                target.write(block)
        if runtime.sha256(temporary) != runtime.DEB_SHA256: raise ValueError('instrument_download_changed')
        temporary.replace(archive)
    if runtime.sha256(archive) != runtime.DEB_SHA256: raise ValueError('instrument_download_changed')
    # Extraction only: do not execute package maintainer scripts or install system files.
    if not (root/'surge').exists():
        subprocess.run(['dpkg-deb', '-x', str(archive), str(root/'surge')], check=True, timeout=180)
    if not runtime.PYTHON.exists():
        subprocess.run(['/usr/bin/python3', '-m', 'venv', str(root/'venv')], check=True, timeout=120)
    subprocess.run([str(runtime.PYTHON), '-m', 'pip', 'install', '--only-binary=:all:', *PACKAGES], check=True, timeout=300)
    receipt = runtime.preflight() | {'archive_sha256':runtime.DEB_SHA256, 'packages':PACKAGES,
                                     'source_url':URL, 'license_file':'surge/usr/share/surge-xt/doc/copyright'}
    (root/'installation.json').write_text(json.dumps(receipt, indent=2))
    return receipt


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--install', action='store_true'); args = parser.parse_args()
    print(json.dumps(install() if args.install else runtime.preflight(), indent=2))
