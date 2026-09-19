"""Offline, CPU-only audit of reviewed SFT records against the pinned tokenizer.

Does not load weights, run examples, train, export datasets or approve records.
Never truncates examples. A successful token audit is not training readiness.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.prepare_training_data import DatasetError, load_batches
from scripts.qwen_qlora_smoke import MODEL, REVISION, ROOT

SNAPSHOT = ROOT / 'hf-cache/hub/models--unsloth--Qwen3.8-27B-unsloth-bnb-4bit/snapshots' / REVISION


def encode_example(tokenizer, messages, max_length):
    """Return exact completion-only labels, excluding system/user/prefill tokens."""
    if type(max_length) is not int or not 256 <= max_length <= 32768:
        raise ValueError('invalid_context_limit')
    prefix = tokenizer.apply_chat_template(
        messages[:-1], tokenize=False, add_generation_prompt=True, enable_thinking=False)
    rendered = tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=False, enable_thinking=False)
    if not rendered.startswith(prefix):
        raise ValueError('chat_template_prefix_mismatch')
    content = messages[-1]['content'].strip()
    # This audit deliberately supports only the observed Qwen text-only format.
    if rendered[len(prefix):] != content + '<|im_end|>\n':
        raise ValueError('assistant_content_changed_by_template')
    tokens = tokenizer(rendered, add_special_tokens=False, truncation=False)['input_ids']
    prompt_tokens = tokenizer(prefix, add_special_tokens=False, truncation=False)['input_ids']
    if tokens[:len(prompt_tokens)] != prompt_tokens:
        raise ValueError('token_boundary_mismatch')
    if len(tokens) > max_length:
        raise ValueError('context_overflow_no_truncation')
    if len(tokens) <= len(prompt_tokens):
        raise ValueError('empty_completion')
    eos = tokenizer.convert_tokens_to_ids('<|im_end|>')
    if eos is None or eos == tokenizer.unk_token_id or eos not in tokens[len(prompt_tokens):]:
        raise ValueError('missing_end_of_turn')
    # Reject control-token injection in text datasets, not ordinary source code.
    for message in messages:
        if any(token in message['content'] for token in tokenizer.all_special_tokens):
            raise ValueError('control_token_in_record')
    return {'input_ids': tokens, 'attention_mask': [1] * len(tokens),
            'labels': [-100] * len(prompt_tokens) + tokens[len(prompt_tokens):]}


def audit(rows, tokenizer, max_length):
    results = []
    for row in rows:
        item = {'id': row['id'], 'split': row['split']}
        try:
            encoded = encode_example(tokenizer, row['messages'], max_length)
            item.update(passed=True, tokens=len(encoded['input_ids']),
                        supervised_tokens=sum(t != -100 for t in encoded['labels']))
        except ValueError as exc:
            item.update(passed=False, reason=str(exc))
        results.append(item)
    return {'records': results, 'tokenization_passed': all(x['passed'] for x in results),
            'max_length': max_length, 'truncation': False, 'enable_thinking': False,
            'label_policy': 'completion_only_explicit_prefix_mask', 'training_started': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('dataset', nargs='+', type=Path)
    parser.add_argument('--max-length', type=int, default=2048)
    args = parser.parse_args()
    os.environ.update(HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1',
                      HF_HUB_DISABLE_TELEMETRY='1', TOKENIZERS_PARALLELISM='false',
                      CUDA_VISIBLE_DEVICES='')
    try:
        rows, gate = load_batches(args.dataset)
        from transformers import AutoTokenizer
        tokenizer = AutoTokenizer.from_pretrained(str(SNAPSHOT), local_files_only=True,
                                                  trust_remote_code=False)
        report = audit(rows, tokenizer, args.max_length)
        report.update(model=MODEL, revision=REVISION,
                      template_sha256=hashlib.sha256(tokenizer.chat_template.encode()).hexdigest(),
                      tokenizer_sha256=hashlib.sha256((SNAPSHOT/'tokenizer.json').read_bytes()).hexdigest(),
                      dataset_gate=gate, training_ready=False,
                      limitation='Token checks do not verify evidence, visual quality or trainer integration.')
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report['tokenization_passed'] else 2
    except (OSError, ValueError, DatasetError):
        print(json.dumps({'error': 'Offline token audit failed. No weights loaded or data exported.'}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
