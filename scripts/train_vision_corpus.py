"""Bounded corpus adapter training and matched validation; never promote weights."""
import argparse
from contextlib import nullcontext
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import random
import signal
import subprocess
import sys
import tempfile
import time
import traceback

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.qwen_qlora_smoke import ROOT, MODEL, REVISION, configure, preflight, versions
from scripts.check_vision_training_inputs import REPO, SNAPSHOT, VisionResponseCollator, feature
from scripts.train_vision_input_pilot import full_vision_names

PLAN = REPO/'config/vision-corpus-research-001.json'
SETTINGS = {'max_length': 4096, 'epochs': 1, 'minimum_records': 2, 'maximum_records': 128,
            'gradient_accumulation': 4, 'rank': 4, 'alpha': 8, 'learning_rate': 1e-5,
            'seed': 3407, 'batch_size': 1, 'vision_layers_frozen': True, 'optimizer': 'torch_adamw'}


def digest(path): return sha256(path.read_bytes()).hexdigest()


def load_protocol():
    plan = json.loads(PLAN.read_text())
    if (plan['schema'] != 'vision-corpus-research.v1' or plan['model'] != MODEL or plan['revision'] != REVISION
            or plan['training'] != SETTINGS or plan['deadline_seconds'] != 2400
            or any(plan[k] is not False for k in ('automatic_promotion', 'production_ready', 'production_data_gate_changed'))):
        raise ValueError('A new bounded research protocol is required')
    return plan


def schedule(count):
    if type(count) is not int or not SETTINGS['minimum_records'] <= count <= SETTINGS['maximum_records']:
        raise ValueError('Bounded multi-record training corpus required')
    indices = list(range(count)); random.Random(SETTINGS['seed']).shuffle(indices)
    return [indices[i:i+SETTINGS['gradient_accumulation']] for i in range(0, count, SETTINGS['gradient_accumulation'])]


def prepare(state_path, exam_path):
    from scripts import learning_autopilot as intake
    from scripts.check_vision_training_inputs import verify_bundle
    from scripts.vector_exam import load_exam
    from scripts import vector_school as school
    from scripts.prepare_training_data import unique_object
    state_bytes = state_path.read_bytes()
    state = json.loads(state_bytes, object_pairs_hook=unique_object)
    if state.get('schema') != 'learning-autopilot.v1': raise ValueError('Recognized intake snapshot required')
    entries, ids, seen_rows, families, images = [], set(), {}, set(), set()
    for key, cached in sorted(state['entries'].items()):
        bundle = Path(cached['bundle']); rows = verify_bundle(bundle)
        if not intake.cached_valid(cached, rows): raise ValueError('Current independent review and CPU audit required')
        local_ids = set()
        for row in rows:
            if row['split'] != 'train': raise ValueError('Distinct train-only records required')
            if row['id'] in local_ids:
                raise ValueError('Duplicate record within one training bundle')
            local_ids.add(row['id'])
            if row['id'] in ids:
                previous = seen_rows[row['id']]
                if not intake.equivalent_experience(previous, row):
                    raise ValueError('Duplicate record changed across training bundles')
                continue
            ids.add(row['id']); families.add(row['family']); images.update(i['sha256'] for i in row['images'])
            seen_rows[row['id']] = row
            entries.append({'bundle': str(bundle), 'row': row, 'records_sha256': digest(bundle/'records.jsonl'),
                            'manifest_sha256': digest(bundle/'manifest.json'), 'audit': cached['audit']})
    steps = schedule(len(entries)); exam, _, _ = load_exam(exam_path)
    if exam['data_split'] != 'validation': raise ValueError('Research comparison uses validation, not final test data')
    requests = []
    for case in exam['cases']:
        request_path = exam_path.parent/f"case-{case['id']:02d}"/'request.json'
        request = json.loads(request_path.read_text(), object_pairs_hook=unique_object)
        if exam['family'] in families or request['image']['sha256'] in images:
            raise ValueError('Training family or image leaked into validation')
        requests.append({'id': case['id'], 'kind': case['kind'], 'request': request,
                         'request_sha256': school.checksum(request_path)})
    return {'protocol': load_protocol(), 'state_sha256': sha256(state_bytes).hexdigest(), 'entries': entries, 'schedule': steps,
            'families': sorted(families), 'exam': str(exam_path), 'exam_sha256': digest(exam_path),
            'validation': requests, 'training_started': False}


def train(out, data, report, persist):
    configure(); os.environ.update(HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', UNSLOTH_COMPILE_LOCATION=str(out/'compiled'))
    from unsloth import FastModel
    import torch
    import transformers
    from transformers import conversion_mapping
    from bitsandbytes.nn import Linear4bit
    torch.set_num_threads(4); report['resources_before'] = preflight(); persist()
    if report['resources_before']['vram_free_bytes'] < 26*1024**3 or report['resources_before']['ram_available_bytes'] < 10*1024**3:
        raise RuntimeError('Insufficient free memory; other processes remain unchanged')
    if transformers.__version__ != '5.5.0': raise RuntimeError('Unverified loader version')
    torch.cuda.reset_peak_memory_stats()
    report['stage'] = 'loading'; persist()
    with full_vision_names(conversion_mapping):
        model, processor = FastModel.from_pretrained(model_name=str(SNAPSHOT), max_seq_length=4096,
            load_in_4bit=True, full_finetuning=False, trust_remote_code=False, local_files_only=True,
            text_only=False, offload_embedding=False, dtype=torch.bfloat16)
    quant = [m for m in model.modules() if isinstance(m, Linear4bit)]
    if len(quant) != 352 or any(getattr(m.weight, 'quant_state', None) is None for m in quant):
        raise RuntimeError('Incomplete quantization state')
    model = FastModel.get_peft_model(model, finetune_vision_layers=False, finetune_language_layers=True,
        finetune_attention_modules=True, finetune_mlp_modules=True, r=4, lora_alpha=8, lora_dropout=0, bias='none',
        use_gradient_checkpointing='unsloth', random_state=3407)
    parameters = [(n, p) for n, p in model.named_parameters() if p.requires_grad]
    if not parameters or any('lora_' not in n or 'visual' in n or 'vision_tower' in n for n, p in parameters):
        raise RuntimeError('Only language adapter parameters may train')
    probe_name, probe = next((n, p) for n, p in parameters if 'lora_B' in n)
    before = probe.detach().cpu().clone()
    report.update(trainable_parameters=sum(p.numel() for n, p in parameters), parameter_probe=probe_name,
                  quantized_layers_verified=len(quant), training_inputs=[], losses=[], steps=0)
    FastModel.for_training(model); processor.tokenizer.padding_side = 'right'
    collator = VisionResponseCollator(processor, 4096)
    visual = next((m for name, m in model.named_modules() if name.endswith('.visual')), None)
    if visual is None: raise RuntimeError('Visual module missing')
    visual_calls = []; hook = visual.register_forward_pre_hook(lambda module, args: visual_calls.append(True))
    optimizer = torch.optim.AdamW([p for n, p in parameters], lr=1e-5)
    report['stage'] = 'training'; persist()
    try:
        for group in data['schedule']:
            optimizer.zero_grad(set_to_none=True)
            for index in group:
                entry = data['entries'][index]; row = entry['row']; bundle = Path(entry['bundle'])
                if digest(bundle/'records.jsonl') != entry['records_sha256'] or digest(bundle/'manifest.json') != entry['manifest_sha256']:
                    raise ValueError('Captured training bundle changed')
                batch = collator([feature(row, bundle)])
                report['training_inputs'].append({'id': row['id'], 'tokens': batch['input_ids'].shape[1],
                    'supervised_tokens': int((batch['labels'] != -100).sum()),
                    'image_grid_thw': batch['image_grid_thw'].tolist(),
                    'input_ids_sha256': sha256(batch['input_ids'].numpy().tobytes()).hexdigest(),
                    'labels_sha256': sha256(batch['labels'].numpy().tobytes()).hexdigest()})
                with torch.autocast(device_type='cuda', dtype=torch.bfloat16):
                    output = model(**{k: v.to('cuda') for k, v in batch.items()}); loss = output.loss
                value = float(loss.detach())
                if not math.isfinite(value): raise RuntimeError('Non-finite loss')
                (loss/len(group)).backward(); report['losses'].append(value)
                del batch, output, loss
            norm = float(torch.nn.utils.clip_grad_norm_([p for _, p in parameters], 1.0))
            if not math.isfinite(norm): raise RuntimeError('Non-finite gradient')
            optimizer.step(); report['steps'] += 1; report['weights_trained'] = True
            report['visual_forward_calls'] = len(visual_calls); persist()
            print(json.dumps({'step': report['steps'], 'examples_seen': len(report['losses'])}), flush=True)
    finally: hook.remove()
    if torch.equal(before, probe.detach().cpu()) or len(visual_calls) < len(data['entries']):
        raise RuntimeError('No adapter change or missing image forwards')
    if sorted(x['id'] for x in report['training_inputs']) != sorted(e['row']['id'] for e in data['entries']):
        raise RuntimeError('Incomplete one-pass training coverage')
    adapter = out/'adapter-RESEARCH-NOT-FOR-PRODUCTION'
    model.save_pretrained(adapter, safe_serialization=True); processor.save_pretrained(adapter)
    report.update(weights_trained=True, adapter=str(adapter), adapter_sha256=digest(adapter/'adapter_model.safetensors'),
                  adapter_parameter_changed=True, peak_vram_bytes=torch.cuda.max_memory_allocated(), stage='validation', results=[])
    optimizer.zero_grad(set_to_none=True); del optimizer, before
    persist(); FastModel.for_inference(model)
    evaluate(model, processor, data, report, persist)
    report.update(status='completed_pending_independent_scoring', stage='complete')


def evaluate(model, processor, data, report, persist):
    import torch
    from PIL import Image
    for phase in ('base', 'adapter'):
        for case in data['validation']:
            request = case['request']; path = Path(request['image']['path'])
            if digest(path) != request['image']['sha256']: raise ValueError('Validation image changed')
            with Image.open(path) as image: pixels = image.convert('RGB')
            messages = [{'role': 'system', 'content': request['system']}, {'role': 'user', 'content': [
                {'type': 'text', 'text': request['user']}, {'type': 'image'}]}]
            prompt = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True, enable_thinking=False)
            inputs = processor(text=prompt, images=[pixels], return_tensors='pt', add_special_tokens=False, truncation=False)
            n = inputs['input_ids'].shape[1]; limit = 400 if case['kind'] == 'attribute_restoration' else 2400
            if n+limit > 4096: raise ValueError('Validation context overflow')
            start = time.monotonic()
            with (model.disable_adapter() if phase == 'base' else nullcontext()), torch.inference_mode():
                output = model.generate(**{k: v.to('cuda') for k, v in inputs.items()}, max_new_tokens=limit,
                    max_time=90, do_sample=False, use_cache=True, pad_token_id=processor.tokenizer.pad_token_id)
            tokens = output[0, n:].tolist(); raw = processor.tokenizer.decode(tokens, skip_special_tokens=True)
            report['results'].append({'phase': phase, 'id': case['id'], 'content': raw,
                'response_sha256': sha256(raw.encode()).hexdigest(),
                'input_ids_sha256': sha256(inputs['input_ids'].numpy().tobytes()).hexdigest(),
                'pixel_values_sha256': sha256(inputs['pixel_values'].contiguous().view(torch.uint8).numpy().tobytes()).hexdigest(),
                'prompt_sha256': sha256(prompt.encode()).hexdigest(),
                'stop_token_seen': processor.tokenizer.convert_tokens_to_ids('<|im_end|>') in tokens,
                'seconds': round(time.monotonic()-start, 3), 'generated_tokens': len(tokens)})
            persist(); print(json.dumps({'validated': len(report['results'])}), flush=True)
            del output, inputs


def worker(out, input_sha):
    configure(); raw = (out/'input.json').read_bytes()
    if sha256(raw).hexdigest() != input_sha: raise ValueError('Captured input changed')
    data = json.loads(raw)
    if data['protocol'] != load_protocol() or data['schedule'] != schedule(len(data['entries'])):
        raise ValueError('Research protocol or schedule changed')
    for name, expected in data['implementation_sha256'].items():
        if digest(REPO/'scripts'/name) != expected: raise ValueError('Training implementation changed before worker start')
    report = {'schema': 'vision-corpus-training.v1', 'status': 'running', 'stage': 'preflight',
        'input_sha256': input_sha, 'protocol': data['protocol'], 'versions': versions(),
        'weights_trained': False, 'production_ready': False, 'automatic_promotion': False}
    started = time.monotonic()
    def persist():
        report['elapsed_seconds'] = round(time.monotonic()-started, 3)
        temporary = out/'report.tmp'; temporary.write_text(json.dumps(report, indent=2)); temporary.replace(out/'report.json')
    def expired(*_): raise TimeoutError('Bounded corpus research deadline')
    signal.signal(signal.SIGALRM, expired); signal.alarm(data['protocol']['deadline_seconds']); persist()
    try: train(out, data, report, persist)
    except Exception as exc:
        report.update(status='failed', error_type=type(exc).__name__)
        (out/'traceback.txt').write_text(traceback.format_exc())
    finally: signal.alarm(0); persist()
    return int(report['status'] == 'failed')


def assess(out):
    from scripts import vector_exam as exam
    report = json.loads((out/'report.json').read_text()); data = json.loads((out/'input.json').read_text())
    if report['status'] != 'completed_pending_independent_scoring' or digest(out/'input.json') != report['input_sha256']:
        raise ValueError('Complete matched inference required')
    if digest(Path(report['adapter'])/'adapter_model.safetensors') != report['adapter_sha256']:
        raise ValueError('Adapter changed')
    path = Path(data['exam'])
    if digest(path) != data['exam_sha256']: raise ValueError('Frozen exam changed')
    definition, source, measured = exam.load_exam(path)
    expected = {(phase, i) for phase in ('base', 'adapter') for i in range(25)}
    responses = {(r['phase'], r['id']): r for r in report['results']}
    if len(report['results']) != 50 or set(responses) != expected: raise ValueError('Complete matched response set required')
    for i in range(25):
        for key in ('input_ids_sha256', 'pixel_values_sha256', 'prompt_sha256'):
            if responses['base', i][key] != responses['adapter', i][key]: raise ValueError('Unmatched candidate inputs')
    scores = []
    for phase in ('base', 'adapter'):
        for entry in definition['cases']:
            folder = path.parent/f"case-{entry['id']:02d}"; response = responses[phase, entry['id']]
            if sha256(response['content'].encode()).hexdigest() != response['response_sha256']: raise ValueError('Response changed')
            output = out/f"score-{phase}-{entry['id']:02d}"; output.mkdir()
            result = {'phase': phase, 'id': entry['id'], 'kind': entry['kind'], 'response_sha256': response['response_sha256']}
            try:
                if not response['stop_token_seen']: raise ValueError('Incomplete candidate response')
                result.update(exam.score(response['content'], entry, folder, source, measured,
                    Path(data['validation'][entry['id']]['request']['image']['path']), output))
            except ValueError as exc: result.update(passed=False, error=str(exc)[:240])
            result['artifacts'] = {p.name: digest(p) for p in output.iterdir() if p.is_file()}
            scores.append(result)
    result = {'schema': 'vision-corpus-comparison.v1', 'training_report_sha256': digest(out/'report.json'),
        'exam_sha256': data['exam_sha256'], 'scores': scores, 'totals': {
            phase: {kind: sum(r['passed'] for r in scores if r['phase'] == phase and r['kind'] == kind)
                    for kind in ('attribute_restoration', 'whole_recreation')} for phase in ('base', 'adapter')},
        'training_exported': False, 'automatic_promotion': False, 'production_ready': False,
        'limitation': 'One validation family; no final test or five-service qualification. HF base and adapter share inputs and decoding; not directly comparable to grammar-constrained Ollama.'}
    (out/'comparison.json').write_text(json.dumps(result, indent=2)); return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state', type=Path); parser.add_argument('--exam', type=Path)
    parser.add_argument('--run', action='store_true'); parser.add_argument('--assess', type=Path)
    parser.add_argument('--worker', type=Path, help=argparse.SUPPRESS); parser.add_argument('--input-sha', help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker: return worker(args.worker, args.input_sha)
    if args.assess: print(json.dumps(assess(args.assess)['totals'])); return 0
    if not args.state or not args.exam: parser.error('--state and --exam required')
    data = prepare(args.state, args.exam)
    if not args.run: print(json.dumps({'records': len(data['entries']), 'updates': len(data['schedule']), 'training_started': False})); return 0
    from scripts.compare_local_models import check_idle
    data['resources_before'] = check_idle()
    data['implementation_sha256'] = {name: digest(REPO/'scripts'/name) for name in
        ('train_vision_corpus.py', 'train_vision_input_pilot.py', 'check_vision_training_inputs.py', 'qwen_qlora_smoke.py')}
    out = Path(tempfile.mkdtemp(prefix='vision-corpus-sft-', dir=ROOT))
    (out/'implementation').mkdir()
    for name, expected in data['implementation_sha256'].items():
        captured = (REPO/'scripts'/name).read_bytes()
        if sha256(captured).hexdigest() != expected: raise ValueError('Implementation changed during capture')
        (out/'implementation'/name).write_bytes(captured)
    payload = json.dumps(data); (out/'input.json').write_text(payload)
    env = os.environ.copy()
    for key in ('DISPLAY', 'WAYLAND_DISPLAY', 'XAUTHORITY', 'DBUS_SESSION_BUS_ADDRESS'): env.pop(key, None)
    command = [str(ROOT/'venv/bin/python'), str(Path(__file__).resolve()), '--worker', str(out), '--input-sha', sha256(payload.encode()).hexdigest()]
    print(json.dumps({'output': str(out)}), flush=True)
    with (out/'worker.log').open('w') as log:
        process = subprocess.run(command, cwd=REPO, env=env, stdout=log, stderr=subprocess.STDOUT, timeout=2430)
    print(json.dumps({'report': str(out/'report.json'), 'exit_code': process.returncode}))
    if process.returncode == 0:
        print(json.dumps({'comparison': str(out/'comparison.json'), 'totals': assess(out)['totals']}))
    return process.returncode


if __name__ == '__main__': raise SystemExit(main())
