import json
from pathlib import Path
import subprocess
from types import SimpleNamespace

import pytest

from app.services import container_runner as container
from app.services import multifile_pilot as pilot
from scripts.check_multifile_isolation import main, sources
from app.services.multifile_profile import inspect_sources


@pytest.mark.parametrize('scenario', ['success', 'no-tests', 'failed-test', 'timeout', 'source-leak'])
def test_pilot_fixtures_are_inert_valid_source_data(scenario):
    assert inspect_sources(sources(scenario))['compatible']


def test_default_command_only_inspects(monkeypatch, capsys):
    def forbidden(*args, **kwargs):
        pytest.fail('Inspection attempted a resource operation')
    monkeypatch.setattr(pilot, 'pilot_configuration', forbidden)
    monkeypatch.setattr(pilot.MultifilePilotRunner, 'run', forbidden)
    assert main([]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report['mode'] == 'inspection_only' and not report['executed']
    with pytest.raises(SystemExit) as exc:
        main(['--run'])
    assert exc.value.code == 2


def test_adapter_requires_fixed_current_config_before_container_calls(monkeypatch):
    base = {'profile': 'python-web-v1', 'image': container.IMAGE, 'harness_checksum': 'old', 'cpus': 1}
    monkeypatch.setattr(pilot, 'configuration', lambda: dict(base))
    config = pilot.pilot_configuration()
    calls = []
    monkeypatch.setattr(container.ContainerRunner, 'run', lambda self, files, cfg, name: calls.append((files, cfg, name)))
    runner = pilot.MultifilePilotRunner()
    assert runner.harness == pilot.HARNESS
    with pytest.raises(ValueError):
        runner.run(sources('success'), config | {'cpus': 8}, 'aic-package-' + 'a' * 32)
    with pytest.raises(ValueError):
        runner.run(sources('success') | {'evil.py': 'pass'}, config, 'aic-package-' + 'a' * 32)
    assert calls == []
    runner.run(sources('success'), config, 'aic-package-' + 'a' * 32)
    assert len(calls) == 1 and calls[0][1]['profile'] == 'python-web-multifile-v1'


def test_shared_container_boundary_stages_nested_files_and_uses_own_cleanup_only(monkeypatch, tmp_path):
    work = tmp_path / 'runner'
    work.mkdir(mode=0o700)
    monkeypatch.setattr(container, 'WORK', work)
    monkeypatch.setattr(pilot, 'configuration', lambda: {'image': container.IMAGE})
    config = pilot.pilot_configuration()
    name = 'aic-package-' + 'a' * 32
    calls = []

    def docker(*args, **kwargs):
        calls.append(args)
        if args[0] == 'info':
            output = '["name=seccomp,profile=builtin", "name=apparmor"]'
        elif args[0] == 'image':
            output = container.IMAGE + ' null'
        elif args[0] == 'create':
            mount = args[args.index('--mount') + 1]
            directory = Path(mount.split('source=', 1)[1].split(',', 1)[0])
            assert (directory / 'modules/logic.py').read_text() == sources('success')['modules/logic.py']
            assert (directory / 'tests/nested/test_logic.py').is_file()
            assert (directory / 'runner_harness.py').read_bytes() == pilot.HARNESS.read_bytes()
            for key in ('--network=none', '--read-only', '--cpus=1', '--pids-limit=64', '--memory=512m'):
                assert key in args
            assert '--gpus' not in args and '--privileged' not in args
            output = 'created'
        elif args[0] == 'inspect':
            assert args[-1] == name
            output = json.dumps({'Status': 'exited', 'ExitCode': 0})
        else:
            pytest.fail('Unexpected Docker operation: ' + str(args))
        return SimpleNamespace(returncode=0, stdout=output, stderr='')

    monkeypatch.setattr(container, 'docker', docker)
    monkeypatch.setattr(container, 'bounded_start', lambda target: {'cli_exit_code': 0, 'reason': None, 'log': '{}'})
    cleaned = []
    runner = pilot.MultifilePilotRunner()
    monkeypatch.setattr(runner, 'cleanup', lambda target: cleaned.append(target) or True)
    result = runner._run(sources('success'), config, name)
    assert result['cleanup_confirmed'] and cleaned == [name]
    assert list(work.iterdir()) == []
    assert [args[0] for args in calls] == ['info', 'image', 'create', 'inspect']


def test_existing_production_staging_still_rejects_nested_sources(tmp_path):
    folder = tmp_path / 'source'
    folder.mkdir(mode=0o700)
    with pytest.raises(ValueError):
        container.ContainerRunner().stage_sources(folder, {'modules/logic.py': 'pass'})
    assert list(folder.iterdir()) == []


@pytest.mark.parametrize('stage,reason',[('security','preflight_security_unavailable'),
                                          ('image','preflight_image_unavailable')])
def test_preflight_failures_are_typed_before_create(monkeypatch,tmp_path,stage,reason):
    work=tmp_path/'runner';work.mkdir(mode=0o700)
    monkeypatch.setattr(container,'WORK',work)
    calls=[]
    def docker(*args,**kwargs):
        calls.append(args[0])
        if args[0]=='info':
            if stage=='security':raise subprocess.TimeoutExpired('docker',10)
            return SimpleNamespace(returncode=0,stdout='["name=seccomp,profile=builtin","name=apparmor"]',stderr='')
        if args[0]=='image':return SimpleNamespace(returncode=1,stdout='',stderr='missing')
        pytest.fail('docker create must not run after preflight failure')
    monkeypatch.setattr(container,'docker',docker)
    runner=container.ContainerRunner()
    config={'image':container.IMAGE,'harness_checksum':'unused'}
    with pytest.raises(container.PreflightFailure) as exc:
        runner._run({'app.py':'pass'},config,'aic-package-'+'a'*32)
    assert exc.value.reason==reason and exc.value.container_started is False
    assert 'create' not in calls


def test_bounded_timeout_preserves_confirmed_cleanup_and_precise_phase(monkeypatch,tmp_path):
    work=tmp_path/'runner';work.mkdir(mode=0o700)
    monkeypatch.setattr(container,'WORK',work)
    runner=container.ContainerRunner()
    config={'image':container.IMAGE,'harness_checksum':container.sha256(runner.harness.read_bytes()).hexdigest()}
    def docker(*args,**kwargs):
        if args[0]=='info':return SimpleNamespace(returncode=0,stdout='["name=seccomp,profile=builtin","name=apparmor"]',stderr='')
        if args[0]=='image':return SimpleNamespace(returncode=0,stdout=container.IMAGE+' null',stderr='')
        if args[0]=='create':return SimpleNamespace(returncode=0,stdout='created',stderr='')
        if args[0]=='inspect':return SimpleNamespace(returncode=0,stdout=json.dumps({'Status':'running'}),stderr='')
        pytest.fail('unexpected docker call')
    monkeypatch.setattr(container,'docker',docker)
    monkeypatch.setattr(container,'bounded_start',lambda name:{'reason':'timeout','cli_exit_code':None,'log':''})
    monkeypatch.setattr(runner,'cleanup',lambda name:True)
    result=runner._run({'app.py':'pass'},config,'aic-package-'+'a'*32)
    assert result['container_created'] is True and result['start_attempted'] is True
    assert result['container_started'] is True
    assert result['reason']=='timeout' and result['cleanup_confirmed'] is True


def test_timeout_during_create_remains_ambiguous(monkeypatch,tmp_path):
    work=tmp_path/'runner';work.mkdir(mode=0o700)
    monkeypatch.setattr(container,'WORK',work)
    runner=container.ContainerRunner()
    config={'image':container.IMAGE,'harness_checksum':container.sha256(runner.harness.read_bytes()).hexdigest()}
    def docker(*args,**kwargs):
        if args[0]=='info':return SimpleNamespace(returncode=0,stdout='["name=seccomp,profile=builtin","name=apparmor"]',stderr='')
        if args[0]=='image':return SimpleNamespace(returncode=0,stdout=container.IMAGE+' null',stderr='')
        if args[0]=='create':raise subprocess.TimeoutExpired('docker create',10)
        pytest.fail('unexpected docker call')
    monkeypatch.setattr(container,'docker',docker)
    monkeypatch.setattr(runner,'cleanup',lambda name:True)
    result=runner._run({'app.py':'pass'},config,'aic-package-'+'a'*32)
    assert result['reason']=='runner_TimeoutExpired'
    assert result['container_created'] is False and result['start_attempted'] is False
    assert result['container_started'] is False and result['cleanup_confirmed'] is False


@pytest.mark.parametrize('stderr,absent',[
    ('Error response from daemon: No such object: aic-package-'+('a'*32),True),
    ('Error: No such container: aic-package-'+('a'*32),True),
    ('docker: No such file or directory',False),
    ('Error response from daemon: No such object: aic-package-'+('b'*32),False),
])
def test_confirm_absent_requires_exact_daemon_object_name(monkeypatch,stderr,absent):
    name='aic-package-'+'a'*32
    monkeypatch.setattr(container,'docker',lambda *a,**k:SimpleNamespace(returncode=1,stdout='',stderr=stderr))
    assert container.ContainerRunner().confirm_absent(name) is absent
