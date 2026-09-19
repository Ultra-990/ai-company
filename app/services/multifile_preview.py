"""Same fixed container limits; sources and owner-controlled request stay separate."""
import json
from hashlib import sha256

from app.services.container_runner import ContainerRunner, ROOT, configuration
from app.services.application_preview import validate_path
from app.services.multifile_profile import require_sources
from app.services.multifile_staging import stage_sources

PROFILE = 'python-web-multifile-preview-v1'
HARNESS = ROOT / 'app/runner/multifile_preview_harness.py'
CERTIFIED_HARNESS = '6f655533645b196378e325f14f16e7b11d59eaa357d57c6dcd0ac39e8706abcd'


def preview_configuration():
    return configuration() | {'profile': PROFILE, 'harness_checksum': sha256(HARNESS.read_bytes()).hexdigest(), 'stateless': True}


def certified_configuration():
    config = preview_configuration()
    if config['harness_checksum'] != CERTIFIED_HARNESS:
        raise ValueError('Podgląd wielomodułowy wymaga nowego pilota po zmianie testera.')
    return config


class MultifilePreviewRunner(ContainerRunner):
    def __init__(self, path):
        super().__init__(HARNESS)
        self.path = validate_path(path)

    def stage_sources(self, folder, files):
        stage_sources(folder, files)
        target = folder / 'preview_request.json'
        with target.open('x', encoding='utf-8') as stream:
            json.dump({'path': self.path}, stream)
        target.chmod(0o444)

    def run(self, files, config, name):
        require_sources(files)
        if config != preview_configuration() | {'request_path': self.path}:
            raise ValueError('Niezgodna konfiguracja podglądu wielomodułowego.')
        return super().run(files, config, name)
