from scripts.start_comfyui import command
from unittest.mock import MagicMock
import pytest
from scripts import open_comfyui as desktop
from scripts import start_comfyui as launcher
import json
import yaml


@pytest.fixture(autouse=True)
def no_real_mount_checks_or_notifications(monkeypatch):
    monkeypatch.setattr(desktop, 'check_shared_mount', lambda: True)


def test_comfyui_is_loopback_and_has_no_paid_or_custom_nodes():
    cmd = command()
    assert cmd[cmd.index('--listen') + 1] == '127.0.0.1'
    assert cmd[cmd.index('--port') + 1] == '8188'
    assert '--disable-api-nodes' in cmd
    assert '--disable-all-custom-nodes' in cmd
    assert '--enable-manager' not in cmd
    assert '--reserve-vram' in cmd
    assert '--cpu' not in cmd


def test_cpu_diagnostic_does_not_request_gpu_reservation():
    cmd = command(cpu=True)
    assert '--cpu' in cmd
    assert '--reserve-vram' not in cmd


def test_desktop_starts_once_then_reuses_service(monkeypatch, tmp_path):
    monkeypatch.setattr(desktop, 'ROOT', tmp_path)
    answers = iter([False, False, True, True])
    monkeypatch.setattr(desktop, 'ready', lambda: next(answers))
    monkeypatch.setattr(desktop.socket, 'socket', MagicMock())
    browser = MagicMock()
    start = MagicMock()
    monkeypatch.setattr(desktop, 'open_browser', browser)
    monkeypatch.setattr(desktop.subprocess, 'Popen', start)
    desktop.main()
    desktop.main()
    assert start.call_count == 1
    assert start.call_args.kwargs['pass_fds']
    assert start.call_args.kwargs['start_new_session']
    assert browser.call_count == 2


def test_desktop_waits_when_another_click_holds_lock(monkeypatch, tmp_path):
    monkeypatch.setattr(desktop, 'ROOT', tmp_path)
    answers = iter([False, True])
    monkeypatch.setattr(desktop, 'ready', lambda: next(answers))
    monkeypatch.setattr(desktop.fcntl, 'flock', MagicMock(side_effect=BlockingIOError))
    start = MagicMock()
    monkeypatch.setattr(desktop.subprocess, 'Popen', start)
    monkeypatch.setattr(desktop, 'open_browser', MagicMock())
    desktop.main()
    start.assert_not_called()


def test_desktop_does_not_replace_unknown_service(monkeypatch, tmp_path):
    monkeypatch.setattr(desktop, 'ROOT', tmp_path)
    monkeypatch.setattr(desktop, 'ready', lambda: False)
    socket = MagicMock()
    socket.return_value.__enter__.return_value.bind.side_effect = OSError('occupied')
    monkeypatch.setattr(desktop.socket, 'socket', socket)
    start = MagicMock()
    monkeypatch.setattr(desktop.subprocess, 'Popen', start)
    with pytest.raises(RuntimeError, match='zajęty'):
        desktop.main()
    start.assert_not_called()


def test_shared_config_is_not_a_download_or_plugin_directory():
    config = yaml.safe_load(launcher.MODEL_CONFIG.read_text())['windows_weights']
    assert config['base_path'] == str(launcher.SHARED_MODELS)
    assert config['is_default'] is False
    assert 'custom_nodes' not in config
    assert set(config) == {'base_path', 'is_default', 'checkpoints', 'diffusion_models',
                           'text_encoders', 'vae', 'loras', 'controlnet', 'clip_vision',
                           'upscale_models', 'latent_upscale_models', 'model_patches', 'audio_encoders'}
    assert '--extra-model-paths-config' in command()


@pytest.mark.parametrize('options,source,accepted', [
    ('ro,nosuid,nodev', '/dev/nvme0n1p4', True),
    ('rw,nosuid,nodev', '/dev/nvme0n1p4', False),
    ('ro,nosuid,nodev', '/dev/other', False),
])
def test_shared_mount_must_be_expected_and_readonly(monkeypatch, options, source, accepted):
    path = MagicMock()
    path.is_dir.return_value = True
    path.resolve.return_value = path
    monkeypatch.setattr(launcher, 'SHARED_MODELS', path)
    result = MagicMock(stdout=json.dumps({'filesystems': [
        {'source': source, 'target': '/media/marcin/Windows', 'options': options}]}))
    monkeypatch.setattr(launcher.subprocess, 'run', MagicMock(return_value=result))
    if accepted:
        assert launcher.check_shared_mount()
    else:
        with pytest.raises(RuntimeError, match='read-only'):
            launcher.check_shared_mount()


def test_missing_windows_does_not_mount_it(monkeypatch, tmp_path):
    monkeypatch.setattr(launcher, 'SHARED_MODELS', tmp_path / 'not-mounted')
    run = MagicMock()
    monkeypatch.setattr(launcher.subprocess, 'run', run)
    assert launcher.check_shared_mount() is False
    run.assert_not_called()


def test_launcher_warns_about_missing_shared_weights_without_downloading(monkeypatch):
    monkeypatch.setattr(desktop,'check_shared_mount',lambda:False)
    monkeypatch.setattr(desktop,'ready',lambda:True)
    notify=MagicMock();browser=MagicMock()
    monkeypatch.setattr(desktop.subprocess,'run',notify)
    monkeypatch.setattr(desktop,'open_browser',browser)
    desktop.main()
    assert notify.call_args.args[0][0]=='notify-send'
    assert 'Nie pobieraj wag ponownie' in notify.call_args.args[0][-1]
    browser.assert_called_once()
