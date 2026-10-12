from pathlib import Path
from unittest.mock import Mock

import pytest

from scripts import generation_limits as limits


def make_group(tmp_path, maximum='21474836480', swap='0', oom='1'):
    for name, value in [('memory.max', maximum), ('memory.swap.max', swap),
                        ('memory.oom.group', oom)]:
        (tmp_path / name).write_text(value)
    return tmp_path


@pytest.mark.parametrize('maximum,swap,oom', [
    ('max', '0', '1'), ('21474836481', '0', '1'), ('0', '0', '1'),
    ('21474836480', 'max', '1'), ('21474836480', '1', '1'),
    ('21474836480', '0', '0'),
])
def test_unbounded_or_incomplete_policy_refused(tmp_path, maximum, swap, oom):
    with pytest.raises(RuntimeError, match='not_enforced'):
        limits.verify_limits(make_group(tmp_path, maximum, swap, oom))


def test_missing_controller_refused(tmp_path):
    with pytest.raises(RuntimeError, match='not_enforced'):
        limits.verify_limits(tmp_path)


def test_reads_actual_kernel_files(tmp_path):
    assert limits.verify_limits(make_group(tmp_path))['memory_max'] == 20 * limits.GIB


def test_unified_cgroup_resolution_and_traversal_refusal(tmp_path):
    proc = tmp_path / 'cgroup'
    proc.write_text('0::/user.slice/test.service\n')
    assert limits.cgroup_path(proc, tmp_path) == tmp_path / 'user.slice/test.service'
    proc.write_text('0::/../../other\n')
    with pytest.raises(RuntimeError):
        limits.cgroup_path(proc, tmp_path)


def test_no_model_launch_on_failed_preflight(monkeypatch):
    monkeypatch.setattr(limits, 'cgroup_path', lambda: Path('/ordinary.scope'))
    monkeypatch.setattr(limits, 'host_preflight', Mock(side_effect=RuntimeError('busy')))
    execute = Mock()
    monkeypatch.setattr(limits.os, 'execvp', execute)
    with pytest.raises(RuntimeError, match='busy'):
        limits.ensure_bounded_launch(['/python', '/generator'])
    execute.assert_not_called()


def test_existing_service_still_requires_real_limits(monkeypatch, tmp_path):
    group = tmp_path / limits.UNIT
    group.mkdir()
    make_group(group, swap='max')
    monkeypatch.setattr(limits, 'cgroup_path', lambda: group)
    with pytest.raises(RuntimeError, match='not_enforced'):
        limits.ensure_bounded_launch(['/python', '/generator'])


def test_launcher_uses_shared_unit_and_bounded_runtime():
    first = limits.systemd_command(['/python', 'comfy'])
    second = limits.systemd_command(['/python', 'ace'])
    for cmd in (first, second):
        assert '--unit=' + limits.UNIT in cmd
        assert '--property=MemorySwapMax=0' in cmd
        assert '--property=KillMode=control-group' in cmd
        assert '--property=RuntimeMaxSec=7200' in cmd
    with pytest.raises(ValueError):
        limits.systemd_command(['python'], memory=21 * limits.GIB)


@pytest.mark.parametrize('containers,gpu,error', [
    ('rental-id\n', '600, 0\n', 'containers_active'),
    ('', '9000, 0\n', 'gpu_busy'),
    ('', '600, 80\n', 'gpu_busy'),
    ('', '', 'gpu_state_unknown'),
])
def test_host_preflight_refuses_competing_work(monkeypatch, containers, gpu, error):
    monkeypatch.setattr(Path, 'read_text', lambda self: 'MemAvailable: 30000000 kB\n')
    run = Mock(side_effect=[Mock(stdout=containers), Mock(stdout=gpu)])
    monkeypatch.setattr(limits.subprocess, 'run', run)
    with pytest.raises(RuntimeError, match=error):
        limits.host_preflight()


def test_host_reserve_checked_before_querying_or_starting_work(monkeypatch):
    monkeypatch.setattr(Path, 'read_text', lambda self: 'MemAvailable: 10000000 kB\n')
    run = Mock()
    monkeypatch.setattr(limits.subprocess, 'run', run)
    with pytest.raises(RuntimeError, match='reserve_insufficient'):
        limits.host_preflight()
    run.assert_not_called()


def test_unknown_host_state_is_not_permission(monkeypatch):
    monkeypatch.setattr(Path, 'read_text', lambda self: 'MemAvailable: 30000000 kB\n')
    monkeypatch.setattr(limits.subprocess, 'run', Mock(side_effect=OSError('unavailable')))
    with pytest.raises(OSError):
        limits.host_preflight()


def test_wait_allows_gpu_to_settle_but_rechecks_all_limits(monkeypatch):
    preflight = Mock(side_effect=[RuntimeError('generation_gpu_busy'), None])
    monkeypatch.setattr(limits, 'host_preflight', preflight)
    monkeypatch.setattr(limits.time, 'sleep', Mock())
    limits.wait_for_host()
    assert preflight.call_count == 2


def test_wait_is_bounded_and_never_bypasses_a_busy_gpu(monkeypatch):
    preflight = Mock(side_effect=RuntimeError('generation_gpu_busy'))
    monkeypatch.setattr(limits, 'host_preflight', preflight)
    monkeypatch.setattr(limits.time, 'sleep', Mock())
    with pytest.raises(RuntimeError, match='gpu_busy'): limits.wait_for_host()
    assert preflight.call_count == 16


def test_wait_stops_immediately_when_containers_appear(monkeypatch):
    preflight = Mock(side_effect=RuntimeError('generation_containers_active'))
    monkeypatch.setattr(limits, 'host_preflight', preflight)
    with pytest.raises(RuntimeError, match='containers_active'): limits.wait_for_host()
    assert preflight.call_count == 1
