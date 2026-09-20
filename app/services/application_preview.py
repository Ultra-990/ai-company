"""Stateless, owner-authorized preview requests. No exposed ports or persistent app."""
import json
import re
from hashlib import sha256
from app.services.container_runner import ContainerRunner, ROOT, configuration

HARNESS = ROOT / 'app/runner/preview_harness.py'


def validate_path(path):
    if path != '/' and not re.fullmatch(r'/api/[A-Za-z0-9_-]+(?:\?[A-Za-z0-9_=&.%+,-]{0,800})?', path):
        raise ValueError('Podgląd dopuszcza tylko GET / lub /api/nazwa z ograniczonym zapytaniem.')
    return path


def preview_configuration():
    return configuration() | {'profile': 'python-web-preview-v1',
        'harness_checksum': sha256(HARNESS.read_bytes()).hexdigest(), 'stateless': True}


class PreviewRunner(ContainerRunner):
    def __init__(self, path):
        super().__init__(HARNESS)
        self.path = validate_path(path)

    def run(self, files, config, name):
        if config.get('profile') == 'python-web-media-preview-v1':
            from app.services.media_package_runner import MediaPackageRunner, media_configuration
            if config != media_configuration(True) | {'request_path': self.path}:
                raise ValueError('Nieaktualny profil podglądu PNG.')
            return MediaPackageRunner(self.path).run(files, config, name)
        if config.get('profile') == 'python-web-multifile-preview-v1':
            from app.services.multifile_preview import MultifilePreviewRunner, certified_configuration
            if config != certified_configuration() | {'request_path': self.path}:
                raise ValueError('Nieaktualny profil podglądu wielomodułowego.')
            return MultifilePreviewRunner(self.path).run(files, config, name)
        return super().run(files | {'preview_request.json': json.dumps({'path': self.path})}, config, name)


def response_of(run):
    if run['state'] != 'previewed':
        raise ValueError('Nie udało się uruchomić podglądu. Sprawdź historię wykonania.')
    return json.loads(run['result']['log'])['response']
