"""Fail-closed cgroup v2 limits for the ComfyUI and ACE-Step launchers.

The shared transient service name serializes these two entry points. It does
not constrain independently launched tools, Ollama, training or other users.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import time

GIB = 1024 ** 3
UNIT = 'ai-company-heavy-generation.service'
MAX_MEMORY = 20 * GIB


def cgroup_path(proc: Path = Path('/proc/self/cgroup'),
                root: Path = Path('/sys/fs/cgroup')) -> Path:
    entries = [line[3:] for line in proc.read_text().splitlines() if line.startswith('0::')]
    if len(entries) != 1 or '..' in Path(entries[0]).parts:
        raise RuntimeError('generation_cgroup_unknown')
    return root / entries[0].lstrip('/')


def verify_limits(group: Path | None = None) -> dict:
    group = group if group is not None else cgroup_path()
    try:
        maximum = int((group / 'memory.max').read_text().strip())
        swap = int((group / 'memory.swap.max').read_text().strip())
        oom_group = (group / 'memory.oom.group').read_text().strip()
        if not 0 < maximum <= MAX_MEMORY or swap != 0 or oom_group != '1':
            raise ValueError('limits outside policy')
    except (OSError, ValueError) as exc:
        raise RuntimeError('generation_memory_limits_not_enforced') from exc
    return {'cgroup': str(group), 'memory_max': maximum, 'swap_max': swap,
            'oom_group': True}


def systemd_command(command: list[str], *, memory: int = MAX_MEMORY,
                    seconds: int = 7200) -> list[str]:
    if not command or not 0 < memory <= MAX_MEMORY or not 1 <= seconds <= 7200:
        raise ValueError('generation_limits_invalid')
    return ['systemd-run', '--user', '--wait', '--pipe', '--collect',
            '--unit=' + UNIT, '--service-type=exec',
            '--property=MemoryAccounting=yes', '--property=MemoryMax=' + str(memory),
            '--property=MemorySwapMax=0',
            '--property=OOMPolicy=kill', '--property=KillMode=control-group',
            '--property=TimeoutStopSec=10', '--property=RuntimeMaxSec=' + str(seconds),
            '--property=CPUQuota=600%', '--property=TasksMax=512',
            '--property=Nice=10', '--property=UMask=0077',
            '--setenv=HF_HUB_OFFLINE=1', '--setenv=TRANSFORMERS_OFFLINE=1',
            '--setenv=HF_HUB_DISABLE_TELEMETRY=1', '--setenv=DO_NOT_TRACK=1',
            '--setenv=OMP_NUM_THREADS=4', '--setenv=MKL_NUM_THREADS=4',
            '--', *command]


def host_preflight() -> None:
    info = dict(line.split(':', 1) for line in Path('/proc/meminfo').read_text().splitlines())
    available = int(info['MemAvailable'].split()[0]) * 1024
    if available < MAX_MEMORY + 4 * GIB:
        raise RuntimeError('generation_host_memory_reserve_insufficient')
    # An unknown resource state must not become permission to load weights.
    containers = subprocess.run(['docker', 'ps', '-q'], capture_output=True,
                                text=True, timeout=10, check=True)
    if containers.stdout.strip():
        raise RuntimeError('generation_containers_active')
    gpu = subprocess.run(['nvidia-smi', '--query-gpu=memory.used,utilization.gpu',
                          '--format=csv,noheader,nounits'], capture_output=True,
                         text=True, timeout=10, check=True)
    rows = [row for row in gpu.stdout.splitlines() if row.strip()]
    if len(rows) != 1:
        raise RuntimeError('generation_gpu_state_unknown')
    memory, utilization = (int(part.strip()) for part in rows[0].split(','))
    if memory > 2048 or utilization > 20:
        raise RuntimeError('generation_gpu_busy')


def wait_for_host() -> None:
    # NVML utilization covers a recent sampling interval even after our model
    # exits. Recheck for at most 15 seconds; never relax the admission limits.
    for attempt in range(16):
        try:
            host_preflight()
            return
        except RuntimeError as exc:
            if str(exc) != 'generation_gpu_busy' or attempt == 15:
                raise
            time.sleep(1)


def ensure_bounded_launch(command: list[str]) -> dict:
    group = cgroup_path()
    if group.name == UNIT:
        receipt = verify_limits(group)
        print(json.dumps({'generation_resource_limits': receipt}), flush=True)
        return receipt
    wait_for_host()
    args = systemd_command(command)
    # Re-enter the same launcher under the actual kernel-enforced limits.
    # No unbounded fallback, environment flag bypass, or unit replacement.
    os.execvp(args[0], args)
    raise AssertionError('exec returned')
