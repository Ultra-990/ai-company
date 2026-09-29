"""Short, opt-in reuse of a model loaded by this bounded sequential batch.

Never sends stop/unload requests. On early exit the three-second lease expires
naturally. This is a cooperative local batch, not an exclusive GPU reservation.
"""
import subprocess
import time

from app.services.local_ollama import OllamaProvider
from scripts.compare_local_models import check_idle, local_json, PreflightFailure

CONTRACT = 'local-retained-batch.v1'
RETENTION_SECONDS = 3


def resident_models():
    response = local_json(11434, '/api/ps')
    models = response.get('models') if isinstance(response, dict) else None
    if not isinstance(models, list) or any(not isinstance(m, dict) for m in models):
        raise PreflightFailure('resident_state_unknown')
    return models


def check_resources(config, started_here):
    models = resident_models()
    if models:
        if (not started_here or len(models) != 1 or
                (models[0].get('name'), models[0].get('digest')) != (config['model'], config['digest'])):
            raise PreflightFailure('unexpected_resident_model')
    else:
        check_idle()
    # Recheck independent users on every request, including both local Comfy ports.
    for port in (8188, 8189):
        try:
            queue = local_json(port, '/queue')
        except ConnectionRefusedError:
            continue
        if not isinstance(queue, dict) or queue.get('queue_running') != [] or queue.get('queue_pending') != []:
            raise PreflightFailure('comfyui_busy_or_unknown')
    if subprocess.check_output(['docker', 'ps', '--format', '{{.ID}}'], text=True, timeout=5).strip():
        raise PreflightFailure('active_containers')
    free = subprocess.check_output(['nvidia-smi', '--query-gpu=memory.free', '--format=csv,noheader,nounits'], text=True, timeout=5)
    if len(free.splitlines()) != 1:
        raise PreflightFailure('gpu_memory_unavailable')
    own_bytes = models[0].get('size_vram') if models else 0
    if type(own_bytes) is not int or not 0 <= own_bytes <= 32*1024**3:
        raise PreflightFailure('resident_memory_unknown')
    if int(free.strip()) + own_bytes//1024**2 < 24576:
        raise PreflightFailure('gpu_memory_unavailable')
    return {'resident_reused': bool(models), 'gpu_free_mib': int(free.strip()),
            'resident_vram_bytes': own_bytes, 'docker': 'empty', 'comfyui': 'idle_or_not_listening'}


class RetainedBatch:
    def __init__(self, config, max_calls):
        if type(max_calls) is not int or not 1 <= max_calls <= 5:
            raise ValueError('Bounded batch requires one to five calls')
        self.config = dict(config)
        self.max_calls = max_calls
        self.calls = []
        self.started_here = False
        self.started = time.monotonic()
        self.closed = False

    def call(self, out, name, system, user, schema, *, final=False):
        from scripts import vector_school as school
        if self.closed or len(self.calls) >= self.max_calls or time.monotonic()-self.started > 600:
            raise ValueError('Retained batch limit reached')
        resources = check_resources(self.config, self.started_here)
        retention = 0 if final else RETENTION_SECONDS
        entry = {'stage': name, 'keep_alive_seconds': retention, 'resources_before': resources}
        self.calls.append(entry)  # A failed transport also consumes its call budget.
        school.save(out/(name+'-request.json'), {'system': system, 'user': user, 'format': schema})
        result = OllamaProvider(self.config | {'format': schema, 'keep_alive_seconds': retention}).complete([
            {'role': 'system', 'content': system}, {'role': 'user', 'content': user}])
        school.save(out/(name+'-response.json'), result)
        if (result.get('model'), result.get('digest')) != (self.config['model'], self.config['digest']):
            raise ValueError('Pinned batch author changed')
        self.started_here = True
        entry.update(elapsed_seconds=result['elapsed_seconds'], timings_ns=result.get('timings_ns', {}))
        return result['content']

    def close(self):
        self.closed = True
        # Read-only wait; never evict a newly arrived model, even on failure.
        deadline = time.monotonic()+RETENTION_SECONDS+2
        while True:
            models = resident_models()
            if not models:
                return {'schema': CONTRACT, 'calls': self.calls, 'idle_after': True}
            if any((m.get('name'), m.get('digest')) != (self.config['model'], self.config['digest']) for m in models):
                raise PreflightFailure('unexpected_resident_model_after_batch')
            if time.monotonic() >= deadline:
                raise PreflightFailure('natural_expiry_not_confirmed')
            time.sleep(.2)
