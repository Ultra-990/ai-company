"""Bounded cold/warm inference timing probe, not a service qualification."""
import json
from pathlib import Path
import tempfile
import time
import subprocess

from app.services.local_ollama import configuration, OllamaProvider, ensure_idle
from scripts.compare_local_models import check_idle, local_json, PreflightFailure
from scripts import vector_school as school

TASKS = (('17 + 28', 45), ('63 - 19', 44), ('6 * 7', 42))
ROOT = Path('/home/marcin/ai-company-workspaces/model-comparisons')
SCHEMA = {'type': 'object', 'additionalProperties': False, 'required': ['result'],
          'properties': {'result': {'type': 'integer'}}}


def run():
    resources = check_idle()
    root = ROOT
    if any(p.is_symlink() for p in (root, *root.parents)):
        raise ValueError('Private Linux workspace required')
    root.mkdir(exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix='batch-speed-', dir=root))
    config = configuration() | {'num_ctx': 8192, 'num_predict': 128, 'num_thread': 4,
                               'timeout_seconds': 60, 'format': SCHEMA}
    report = {'schema': 'local-batch-speed-probe.v1', 'resources_before': resources,
              'config': config, 'runs': [], 'status': 'running', 'production_changed': False,
              'training_exported': False, 'autonomy_qualified': False,
              'limitations': 'Three short arithmetic requests per arm, cold first. Not a full-job speedup or quality benchmark.'}
    print(json.dumps({'output': str(out)}), flush=True)
    try:
        for arm in ('cold', 'warm'):
            check_idle()
            started = time.monotonic()
            entry = {'arm': arm, 'requests': []}; report['runs'].append(entry)
            for index, (task, expected) in enumerate(TASKS):
                if arm == 'cold':
                    check_idle()
                else:
                    # The initial load passed full preflight. Before further work
                    # refuse a changed resident model or newly arrived container.
                    models = local_json(11434, '/api/ps').get('models')
                    if not isinstance(models, list) or any(
                        (m.get('name'), m.get('digest')) != (config['model'], config['digest']) for m in models
                    ): raise PreflightFailure('unexpected_resident_model')
                    if subprocess.check_output(['docker', 'ps', '--format', '{{.ID}}'], text=True, timeout=5).strip():
                        raise PreflightFailure('active_containers')
                    if not models: check_idle()
                # Natural short expiry on the last request; no stop/unload API.
                retention = (1 if index == len(TASKS)-1 else 15) if arm == 'warm' else 0
                request = {'config': config | {'keep_alive_seconds': retention}, 'messages': [
                    {'role': 'system', 'content': 'Return only the requested JSON arithmetic result.'},
                    {'role': 'user', 'content': 'Calculate '+task}]}
                stem = arm+'-'+str(index)
                school.save(out/(stem+'-request.json'), request)
                response = OllamaProvider(request['config']).complete(request['messages'])
                school.save(out/(stem+'-response.json'), response)
                correct = json.loads(response['content']) == {'result': expected}
                entry['requests'].append({'stem': stem, 'correct': correct,
                    'elapsed_seconds': response['elapsed_seconds'], 'timings_ns': response.get('timings_ns', {})})
                if not correct: raise ValueError('Timing request gave an incorrect result')
            entry['request_seconds'] = round(sum(r['elapsed_seconds'] for r in entry['requests']), 3)
            # Read-only wait for natural expiry, included in wall time.
            for _ in range(20):
                try: ensure_idle(); break
                except ValueError: time.sleep(1)
            else: raise ValueError('Natural model expiry not confirmed')
            entry['wall_seconds_including_expiry'] = round(time.monotonic()-started, 3)
        report['status'] = 'completed'
    except Exception as exc:
        report.update(status='failed', error_type=type(exc).__name__, error=str(exc)[:200])
    finally:
        report['artifacts'] = {p.name: school.checksum(p) for p in out.iterdir() if p.is_file()}
        school.save(out/'report.json', report)
    print(json.dumps({'report': str(out/'report.json'), **report}), flush=True)
    return out, report
