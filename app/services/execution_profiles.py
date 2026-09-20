"""Trusted runner routing. Package owners cannot supply images or commands."""
from app.services.container_runner import ContainerRunner
from app.services.multifile_pilot import MultifilePilotRunner, pilot_configuration
from app.services.multifile_profile import PROFILE

CERTIFIED_HARNESS = 'b0bd8fdceaf91e74766c9f669cb99157fdf43df7b5aa235492230aee70b689a1'


def multifile_configuration():
    config = pilot_configuration()
    if config['harness_checksum'] != CERTIFIED_HARNESS:
        raise ValueError('Tester wielomodułowy zmienił się; wymagany nowy pilot izolacji.')
    return config


class RoutedContainerRunner(ContainerRunner):
    def run(self, files, config, name):
        from app.services.media_packages import PROFILE as MEDIA_PROFILE
        if config.get('profile') == MEDIA_PROFILE:
            from app.services.media_package_runner import MediaPackageRunner, media_configuration
            if config != media_configuration():
                raise ValueError('Nieaktualny profil paczki z PNG.')
            return MediaPackageRunner().run(files, config, name)
        if config.get('profile') == PROFILE:
            if config != multifile_configuration():
                raise ValueError('Nieaktualny profil wykonawcy wielomodułowego.')
            return MultifilePilotRunner().run(files, config, name)
        if config.get('profile') != 'python-web-v1':
            raise ValueError('Nieobsługiwany profil testów.')
        return super().run(files, config, name)


def capabilities(profile):
    """Feature support only, not authorization, availability or readiness."""
    if profile in (PROFILE, 'python-web-media-v1'):
        return {'test': True, 'candidate': True, 'preview': True,
                'automatic_repair': False, 'release': True, 'package_review': True}
    if profile == 'python-web-v1':
        return {'test': True, 'candidate': True, 'preview': True,
                'automatic_repair': True, 'release': True}
    return {'test': False, 'candidate': False, 'preview': False,
            'automatic_repair': False, 'release': False}
