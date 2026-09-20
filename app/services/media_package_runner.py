"""Separate PNG runner profile; existing text limits and Docker isolation remain."""
from hashlib import sha256
import json
import os

from app.services.container_runner import ContainerRunner, ROOT, configuration
from app.services.media_packages import validate, bytes_of, PROFILE

PREVIEW = 'python-web-media-preview-v1'
HARNESS = ROOT / 'app/runner/media_package_harness.py'
SUPPORT = ROOT / 'app/runner/multifile_harness.py'
CERTIFIED_HARNESS = 'fb1eddbcc2bf93a186a7e33a9ceb428e1deb29b9aebf017b06123db278df229d'
CERTIFIED_SUPPORT = 'b0bd8fdceaf91e74766c9f669cb99157fdf43df7b5aa235492230aee70b689a1'


def pilot_configuration(preview=False):
    return configuration() | {'profile': PREVIEW if preview else PROFILE,
        'harness_checksum': sha256(HARNESS.read_bytes()).hexdigest(),
        'support_checksum': sha256(SUPPORT.read_bytes()).hexdigest(), 'stateless': True}


def media_configuration(preview=False):
    config = pilot_configuration(preview)
    if config['harness_checksum'] != CERTIFIED_HARNESS or config['support_checksum'] != CERTIFIED_SUPPORT:
        raise ValueError('Profil PNG wymaga zgodnego testera i pilota izolacji.')
    return config


def public_routes(files):
    types = {'.html': 'text/html', '.css': 'text/css', '.js': 'javascript',
             '.png': 'image/png', '.json': 'application/json', '.txt': 'text/plain'}
    from pathlib import PurePosixPath
    return {('/' if name == 'index.html' else '/' + name): (name, types[PurePosixPath(name).suffix])
        for name in sorted(files) if name in {'index.html', 'style.css', 'app.js'} or name.startswith('static/')}


class MediaPackageRunner(ContainerRunner):
    def __init__(self, path=None):
        super().__init__(HARNESS)
        from app.services.application_preview import validate_path
        self.path = validate_path(path) if path is not None else None

    def stage_sources(self, folder, files):
        entries = validate(files)
        if (any(p.is_symlink() for p in (folder, *folder.parents)) or any(folder.iterdir())
                or folder.stat().st_uid != os.geteuid() or folder.stat().st_mode & 0o077):
            raise ValueError('Wymagany pusty prywatny staging na Linuksie.')
        content = {e['path']: bytes_of(e) for e in entries}
        content.update({'runner_support.py': SUPPORT.read_bytes(),
            'media_control.json': json.dumps({'path': self.path, 'public': public_routes(files),
                'hashes': {e['path']: e['sha256'] for e in entries}}).encode()})
        for name, raw in sorted(content.items()):
            target = folder / name
            target.parent.mkdir(mode=0o755, exist_ok=True, parents=True)
            with target.open('xb') as stream:
                stream.write(raw)
            target.chmod(0o444)
        folder.chmod(0o755)

    def run(self, files, config, name):
        validate(files)
        expected = pilot_configuration(self.path is not None)
        if self.path is not None:
            expected['request_path'] = self.path
        if config != expected:
            raise ValueError('Zmieniono profil wykonania paczki z PNG.')
        return super().run(files, config, name)
