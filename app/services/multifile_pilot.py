"""Trusted multi-module adapter, selected only by server-side profile routing.

Used by the explicit pilot and certified production router. Keeps the fixed image,
limits, lock, no-network policy, exact-identity cleanup and disposable workspace.
"""
from hashlib import sha256

from app.services.container_runner import ContainerRunner, ROOT, configuration
from app.services.multifile_profile import PROFILE, require_sources
from app.services.multifile_staging import stage_sources

HARNESS = ROOT / 'app/runner/multifile_harness.py'


def pilot_configuration():
    return configuration() | {'profile': PROFILE, 'harness_checksum': sha256(HARNESS.read_bytes()).hexdigest()}


class MultifilePilotRunner(ContainerRunner):
    def __init__(self):
        super().__init__(harness=HARNESS)

    def stage_sources(self, folder, files):
        stage_sources(folder, files)

    def run(self, files, config, name):
        require_sources(files)
        if config != pilot_configuration():
            raise ValueError('Pilot wymaga niezmienionego, przypiętego profilu.')
        return super().run(files, config, name)
