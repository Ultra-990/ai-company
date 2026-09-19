"""Opt-in isolated installation/download/hardware smoke test; never deploys a model.

Run ONLY with qwen-training/venv. The synthetic smoke data is NOT a company
training dataset or held-out evaluation. Production dataset gate remains intact.
"""
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import shutil
import signal
import sys
import tempfile
import time

ROOT = Path('/home/marcin/ai-company-workspaces/qwen-training')
MODEL = 'unsloth/Qwen3.8-27B-unsloth-bnb-4bit'
REVISION = '8aa5f05d26b7205477066e1449e0af13f762a299'
FILES = ['config.json', 'generation_config.json', 'tokenizer.json',
         'tokenizer_config.json', 'chat_template.jinja', 'processor_config.json',
         'model.safetensors', 'README.md']


def configure():
    if Path(sys.prefix).resolve() != (ROOT / 'venv').resolve():
        raise RuntimeError('Use the isolated qwen-training/venv, not the application venv.')
    ROOT.mkdir(parents=True, exist_ok=True)
    for key, value in {
        'HF_HOME': str(ROOT / 'hf-cache'), 'HF_HUB_DISABLE_TELEMETRY': '1',
        'HF_HUB_DISABLE_IMPLICIT_TOKEN': '1', 'DO_NOT_TRACK': '1',
        'TOKENIZERS_PARALLELISM': 'false', 'OMP_NUM_THREADS': '4',
        'TORCHINDUCTOR_CACHE_DIR': str(ROOT / 'torch-cache'),
        'TRITON_CACHE_DIR': str(ROOT / 'triton-cache'),
        'UNSLOTH_DISABLE_STATISTICS': '1',
    }.items():
        os.environ[key] = value


def synthetic_messages():
    # Deliberately trivial software/hardware fixture; no client data or Qwen drafts.
    return [[{'role': 'system', 'content': 'Return only the integer result.'},
             {'role': 'user', 'content': f'Calculate {a} + {b}.'},
             {'role': 'assistant', 'content': str(a + b)}]
            for a, b in [(2, 3), (4, 7), (9, 6), (13, 5)]]


def versions():
    result = {}
    for name in ('torch', 'transformers', 'peft', 'trl', 'unsloth', 'unsloth_zoo', 'bitsandbytes'):
        try:
            result[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            result[name] = None
    return result


def download():
    from huggingface_hub import snapshot_download
    if shutil.disk_usage(ROOT).free < 70 * 1024**3:
        raise RuntimeError('At least 70 GiB free workspace required before download.')
    return snapshot_download(MODEL, revision=REVISION, allow_patterns=FILES,
                             cache_dir=ROOT / 'hf-cache/hub', max_workers=2, token=False)


def preflight():
    import torch
    import psutil
    if not torch.cuda.is_available():
        raise RuntimeError('CUDA unavailable in isolated training environment.')
    free, total = torch.cuda.mem_get_info()
    return {'gpu': torch.cuda.get_device_name(), 'compute_capability': torch.cuda.get_device_capability(),
            'torch_cuda': torch.version.cuda, 'vram_free_bytes': free, 'vram_total_bytes': total,
            'ram_available_bytes': psutil.virtual_memory().available,
            'disk_free_bytes': shutil.disk_usage(ROOT).free}


def render_fixture(tokenizer):
    messages = synthetic_messages()
    rendered = [tokenizer.apply_chat_template(m, tokenize=False, add_generation_prompt=False,
                                              enable_thinking=False) for m in messages]
    lengths = [len(tokenizer(t, add_special_tokens=False)['input_ids']) for t in rendered]
    if not lengths or max(lengths) > 256:
        raise RuntimeError('Smoke example exceeds context.')
    return rendered, lengths


def tokenize_fixture():
    os.environ['HF_HUB_OFFLINE'] = '1'
    from transformers import AutoTokenizer
    location = ROOT / 'hf-cache/hub/models--unsloth--Qwen3.8-27B-unsloth-bnb-4bit/snapshots' / REVISION
    tokenizer = AutoTokenizer.from_pretrained(str(location), trust_remote_code=False, local_files_only=True)
    _, lengths = render_fixture(tokenizer)
    return {'lengths': lengths, 'max_length': 256, 'chat_template_present': bool(tokenizer.chat_template)}


def run_smoke(output, report):
    # Local files only during the training phase; no repository Python code loaded.
    os.environ['HF_HUB_OFFLINE'] = '1'
    os.environ['TRANSFORMERS_OFFLINE'] = '1'
    os.environ['UNSLOTH_COMPILE_LOCATION'] = str(output / 'compiled')
    from unsloth import FastModel
    import torch
    from datasets import Dataset
    from trl import SFTConfig, SFTTrainer
    from huggingface_hub import snapshot_download

    resources = preflight()
    report['resources_before'] = resources
    if resources['vram_free_bytes'] < 26 * 1024**3 or resources['ram_available_bytes'] < 10 * 1024**3:
        raise RuntimeError('Insufficient free memory; do not unload or kill other workloads.')
    location = snapshot_download(MODEL, revision=REVISION, cache_dir=ROOT / 'hf-cache/hub',
                                 local_files_only=True, allow_patterns=FILES, token=False)
    torch.set_num_threads(4)
    torch.cuda.reset_peak_memory_stats()
    print('Loading pinned local checkpoint; no production model changes.', flush=True)
    model, tokenizer = FastModel.from_pretrained(
        model_name=location, max_seq_length=256, load_in_4bit=True,
        full_finetuning=False, trust_remote_code=False, local_files_only=True,
        text_only=True, offload_embedding=False, dtype=torch.bfloat16,
    )
    model = FastModel.get_peft_model(
        model, finetune_vision_layers=False, finetune_language_layers=True,
        finetune_attention_modules=True, finetune_mlp_modules=True,
        r=4, lora_alpha=4, lora_dropout=0, bias='none',
        use_gradient_checkpointing='unsloth', random_state=3407,
    )
    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    if trainable == 0:
        raise RuntimeError('No trainable adapter parameters.')
    report['trainable_parameters'] = trainable
    probe_name, probe = next((name, p) for name, p in model.named_parameters()
                            if p.requires_grad and 'lora_B' in name)
    before = probe.detach().cpu().clone()
    print(json.dumps({'trainable_parameters': trainable}), flush=True)
    messages = synthetic_messages()
    rendered, lengths = render_fixture(tokenizer)
    report['token_lengths'] = lengths
    report['fixture_sha256'] = hashlib.sha256(json.dumps(messages).encode()).hexdigest()
    trainer = SFTTrainer(model=model, processing_class=tokenizer,
                        train_dataset=Dataset.from_dict({'text': rendered}),
                        args=SFTConfig(output_dir=str(output / 'checkpoints'),
                                       dataset_text_field='text', max_length=256,
                                       per_device_train_batch_size=1, gradient_accumulation_steps=1,
                                       max_steps=3, learning_rate=1e-5, warmup_steps=0,
                                       optim='adamw_8bit', logging_steps=1, save_strategy='no',
                                       report_to='none', seed=3407, dataset_num_proc=1,
                                       bf16=True, dataloader_num_workers=0))
    result = trainer.train()
    report['metrics'] = result.metrics
    report['steps'] = trainer.state.global_step
    report['peak_vram_bytes'] = torch.cuda.max_memory_allocated()
    report['finite_loss'] = bool(torch.isfinite(torch.tensor(result.training_loss)).item())
    report['adapter_parameter_changed'] = not torch.equal(before, probe.detach().cpu())
    report['parameter_probe'] = probe_name
    if not report['finite_loss'] or report['steps'] != 3:
        raise RuntimeError('Smoke training did not complete three finite-loss steps.')
    if not report['adapter_parameter_changed']:
        raise RuntimeError('Adapter parameter did not change during training.')
    model.save_pretrained(output / 'adapter-NOT-FOR-PRODUCTION', safe_serialization=True)
    tokenizer.save_pretrained(output / 'adapter-NOT-FOR-PRODUCTION')
    report['adapter_saved'] = (output / 'adapter-NOT-FOR-PRODUCTION/adapter_config.json').is_file()
    if not report['adapter_saved']:
        raise RuntimeError('Adapter export missing.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['download', 'preflight', 'tokenize', 'smoke'])
    args = parser.parse_args()
    configure()
    output = Path(tempfile.mkdtemp(prefix=f'{args.action}-', dir=ROOT))
    report = {'action': args.action, 'model': MODEL, 'revision': REVISION,
              'versions': versions(), 'status': 'started', 'production_ready': False,
              'quality_improvement_measured': False, 'adapter_saved': False}
    started = time.monotonic()
    print(json.dumps({'report_directory': str(output)}), flush=True)
    def expired(*_):
        raise TimeoutError('Bounded training/download deadline reached.')
    signal.signal(signal.SIGALRM, expired)
    signal.alarm(1200 if args.action != 'preflight' else 90)
    try:
        if args.action == 'download':
            report['snapshot'] = download()
        elif args.action == 'preflight':
            report['resources'] = preflight()
        elif args.action == 'tokenize':
            report['tokenization'] = tokenize_fixture()
        else:
            run_smoke(output, report)
        report['status'] = 'passed'
    except Exception as exc:
        report['status'] = 'failed'
        report['error_type'] = type(exc).__name__
        report['error'] = str(exc)[:1500]
        print(f'{type(exc).__name__}: {str(exc)[:1500]}', flush=True)
    finally:
        signal.alarm(0)
        report['elapsed_seconds'] = round(time.monotonic() - started, 3)
        (output / 'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({'status': report['status'], 'report': str(output / 'report.json')}), flush=True)
    return 0 if report['status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
