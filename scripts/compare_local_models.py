"""Sequential public synthetic benchmark; no training, production routing or customer data."""
import argparse
import http.client
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.services.local_ollama import OllamaProvider, ensure_idle, generation_options
from app.services.container_runner import ContainerRunner, configuration as runner_configuration
from scripts import evaluate_qwen_repairs as repairs, evaluate_qwen_roles as roles
from scripts.qwen_evaluation_catalog import load_suite, load_role_suite, CHECKSUM, ROLE_CHECKSUM

MODELS = ('qwen3.8:27b', 'gemma4:31b')


def local_json(port, path):
    conn = http.client.HTTPConnection('127.0.0.1', port, timeout=5)
    try:
        conn.request('GET', path); response = conn.getresponse(); raw = response.read(1024*1024+1)
        if response.status != 200 or len(raw) > 1024*1024: raise ValueError('local status unavailable')
        return json.loads(raw)
    finally: conn.close()


def check_idle():
    ensure_idle()
    queue = local_json(8188, '/queue')
    if queue.get('queue_running') != [] or queue.get('queue_pending') != []:
        raise ValueError('ComfyUI is busy')
    gpu = subprocess.check_output(['nvidia-smi', '--query-gpu=memory.free', '--format=csv,noheader,nounits'], text=True, timeout=5)
    if len(gpu.splitlines()) != 1 or int(gpu.strip()) < 24576:
        raise ValueError('At least 24 GiB free GPU memory required. No model unloaded automatically.')


def model_config(model, inventory):
    if model not in MODELS: raise ValueError('Model outside approved local comparison')
    item = next(m for m in inventory['models'] if m['name'] == model)
    digest = item['digest']
    if len(digest) != 64 or any(c not in '0123456789abcdef' for c in digest): raise ValueError('Invalid digest')
    return {'model':model, 'digest':digest, 'num_ctx':8192, 'num_predict':1200,
            'num_thread':6, 'timeout_seconds':120,
            'sampling_profile':'gemma4-default.v1' if model.startswith('gemma4:') else 'bounded-default.v1'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', action='store_true')
    parser.add_argument('--model', choices=MODELS, required=True)
    args = parser.parse_args()
    repair_suite, role_suite = load_suite(), load_role_suite()
    if not args.run:
        print(json.dumps({'model':args.model, 'repair_cases':len(repair_suite['cases']),
                          'role_cases':len(role_suite['cases']), 'inference':False})); return 0
    check_idle()
    config = model_config(args.model, local_json(11434, '/api/tags'))
    runner_config = runner_configuration()
    parent = Path('/home/marcin/ai-company-workspaces/model-comparisons')
    if any(p.is_symlink() for p in [parent, *parent.parents]): raise ValueError('Symlink workspace')
    parent.mkdir(exist_ok=True)
    if parent.stat().st_dev != Path('/home/marcin').stat().st_dev: raise ValueError('Linux /home required')
    out = Path(tempfile.mkdtemp(prefix=args.model.split(':')[0]+'-', dir=parent))
    report = {'schema':'local-model-comparison.v1', 'model':config['model'], 'digest':config['digest'],
        'sampling':generation_options(config), 'num_ctx':8192, 'think':False, 'keep_alive':0,
        'repair_suite_checksum':CHECKSUM, 'role_suite_checksum':ROLE_CHECKSUM,
        'repairs':[], 'roles':[], 'attempts_per_case':1, 'training_started':False,
        'production_routing_changed':False, 'limits':'Public synthetic suites; not full application delivery or adversarial audit.'}
    started = time.monotonic()
    def save():
        report['repair_summary'] = repairs.summary(report['repairs'], len(repair_suite['cases']))
        report['role_summary'] = roles.summarize(role_suite, report['roles'])
        report['elapsed_seconds'] = round(time.monotonic()-started, 3)
        (out/'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))
    save(); print(json.dumps({'report':str(out/'report.json')}), flush=True)
    try:
        for case in repair_suite['cases']:
            check_idle()
            entry = repairs.evaluate_case(case, OllamaProvider(config | {'format':repairs.SCHEMA}), ContainerRunner(), runner_config)
            report['repairs'].append(entry); save()
            print(json.dumps({'suite':'repairs', 'case':case['id'], 'status':entry['status']}), flush=True)
            if entry['status'] == 'infrastructure_error': return 2
        for case in role_suite['cases']:
            check_idle()
            entry = roles.evaluate_case(role_suite, case, OllamaProvider(config | {'format':roles.SCHEMA, 'num_predict':600}))
            report['roles'].append(entry); save()
            print(json.dumps({'suite':'roles', 'case':case['id'], 'status':entry['status']}), flush=True)
            if entry['status'] == 'infrastructure_error': return 2
        return 0
    except Exception as exc:
        report['error_type'] = type(exc).__name__; report['error'] = 'Preflight/resources/adapter failed; no automatic retry.'
        return 2
    finally:
        save(); print(json.dumps({'repairs':report['repair_summary'], 'roles':report['role_summary']}), flush=True)


if __name__ == '__main__': raise SystemExit(main())
