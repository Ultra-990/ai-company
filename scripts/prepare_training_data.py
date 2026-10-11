"""Offline dataset gate. Never calls a model, executes examples or reads the app DB."""
import argparse
from collections import Counter
from datetime import date
import hashlib
import json
from pathlib import Path
import re
import sys
import tempfile
import unicodedata

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

VERSION = 'company-sft.v1'
MAX_BYTES = 16 * 1024 * 1024
MINIMUMS = {'train': 200, 'validation': 25, 'test': 50}
WORKSPACES = Path('/home/marcin/ai-company-workspaces')
FIELDS = {'version', 'id', 'family', 'split', 'skill', 'source', 'messages', 'review'}
SKILLS = {'scope', 'planning', 'coding', 'repair', 'evidence'}


class DatasetError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise DatasetError(message)


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, 'duplicate JSON key')
        result[key] = value
    return result


def text(value, limit=200):
    return isinstance(value, str) and 0 < len(value.strip()) <= limit and '\x00' not in value


def normalized(value):
    return ' '.join(unicodedata.normalize('NFKC', value).casefold().split())


def fingerprint(value):
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


def task_views(content):
    """Recognize lossless JSON reserialization without executing task content.

    Text leaves also expose a reserved article carried as numbered lines inside
    a new JSON wrapper. This is exact-content screening, not paraphrase detection.
    """
    views = {normalized(content)}
    stripped = content.strip()
    if stripped.startswith('```json\n') and stripped.endswith('\n```'):
        stripped = stripped[8:-4]
    try:
        value = json.loads(stripped, object_pairs_hook=unique_object)
    except DatasetError:
        raise
    except (ValueError, TypeError):
        return views
    except RecursionError:
        raise DatasetError('task JSON nesting too deep') from None
    leaves = []
    def walk(item, depth=0):
        require(depth <= 32, 'task JSON nesting too deep')
        if isinstance(item, str):
            leaves.append(item)
        elif isinstance(item, dict):
            for child in item.values(): walk(child, depth+1)
        elif isinstance(item, list):
            for child in item: walk(child, depth+1)
    walk(value)
    views.add(normalized(json.dumps(value, ensure_ascii=False, sort_keys=True)))
    if leaves: views.add(normalized(' '.join(leaves)))
    return views


def task_identity(content):
    """Fingerprint lossless task representations, preserving keys and numbers.

    A single object/list wrapper carries no additional task content. Unlike
    reserved-article screening, identity must not discard numeric facts or
    compare only text leaves: distinct exercises can share those leaves.
    """
    stripped = content.strip()
    if stripped.startswith('```json\n') and stripped.endswith('\n```'):
        stripped = stripped[8:-4]
    try:
        value = json.loads(stripped, object_pairs_hook=unique_object)
    except DatasetError:
        raise
    except (ValueError, TypeError):
        return fingerprint(normalized(content))
    except RecursionError:
        raise DatasetError('task JSON nesting too deep') from None
    # Apply the same structural depth limit to all splits, including test.
    task_views(content)
    while isinstance(value, (dict, list)) and len(value) == 1:
        child = next(iter(value.values())) if isinstance(value, dict) else value[0]
        if not isinstance(child, (dict, list)):
            break
        value = child
    return fingerprint(normalized(json.dumps(value, ensure_ascii=False, sort_keys=True)))


def validate_record(row):
    require(isinstance(row, dict) and set(row) == FIELDS, 'incorrect record fields')
    require(row['version'] == VERSION, 'unsupported version')
    for field in ('id', 'family'):
        require(isinstance(row[field], str) and re.fullmatch(r'[a-z0-9][a-z0-9._-]{0,99}', row[field]), 'invalid identifier')
    require(row['split'] in ('train', 'validation', 'test'), 'invalid split')
    require(row['skill'] in SKILLS, 'invalid skill')
    source = row['source']
    require(isinstance(source, dict) and set(source) == {'kind', 'reference', 'rights', 'privacy_checked'}, 'incorrect source fields')
    require(source['kind'] in ('synthetic', 'licensed', 'owned'), 'invalid source kind')
    require(text(source['reference'], 500) and text(source['rights'], 500), 'missing provenance/rights')
    require(type(source['privacy_checked']) is bool, 'privacy flag must be boolean')
    messages = row['messages']
    require(isinstance(messages, list) and len(messages) == 3, 'expected system/user/assistant conversation')
    for message, role in zip(messages, ('system', 'user', 'assistant')):
        require(isinstance(message, dict) and set(message) == {'role', 'content'}, 'incorrect message fields')
        require(message['role'] == role and text(message['content'], 32000), 'invalid message role/content')
    review = row['review']
    require(isinstance(review, dict) and set(review) == {'status', 'reviewer', 'reviewed_on', 'evidence', 'note'}, 'incorrect review fields')
    require(review['status'] in ('pending', 'approved', 'rejected'), 'invalid review status')
    require(isinstance(review['evidence'], list) and len(review['evidence']) <= 20, 'invalid evidence list')
    for proof in review['evidence']:
        require(isinstance(proof, dict) and set(proof) == {'kind', 'reference', 'sha256'}, 'incorrect evidence fields')
        require(proof['kind'] in ('independent_test', 'content_review'), 'invalid evidence kind')
        require(text(proof['reference'], 500) and isinstance(proof['sha256'], str) and re.fullmatch('[a-f0-9]{64}', proof['sha256']), 'invalid evidence reference/hash')
    require(isinstance(review['note'], str) and len(review['note']) <= 1000, 'invalid review note')
    require(isinstance(review['reviewer'], str), 'invalid reviewer')
    if review['status'] == 'approved':
        require(source['privacy_checked'] and text(review['reviewer']) and text(review['note'], 1000) and review['evidence'], 'approval requires privacy review and evidence')
        try:
            reviewed = date.fromisoformat(review['reviewed_on'])
        except (ValueError, TypeError):
            raise DatasetError('invalid review date') from None
        require(reviewed <= date.today(), 'review date is in the future')
        if row['skill'] in ('coding', 'repair'):
            require(any(p['kind'] == 'independent_test' for p in review['evidence']), 'code/repair needs independent test evidence')
    else:
        require(review['reviewed_on'] is None or isinstance(review['reviewed_on'], str), 'invalid review date')


def validate_dataset(raw):
    # Reserved evaluation families cannot quietly become training/validation
    # examples through a separate input file. Never import/execute their code.
    from scripts.qwen_evaluation_catalog import reserved_cases
    from scripts.training_family_registry import load_training_only_families
    try:
        reserved = reserved_cases()
        training_only = load_training_only_families()
    except (OSError, ValueError, KeyError) as exc:
        raise DatasetError('evaluation catalog missing or changed') from exc
    reserved_families = {case['family'] for case in reserved}
    reserved_views = set()
    for case in reserved:
        reserved_views.update(task_views(case['brief']))
        if case.get('article'): reserved_views.add(normalized(case['article']))
    require(len(raw) <= MAX_BYTES, 'dataset too large')
    try:
        content = raw.decode('utf-8')
    except UnicodeError:
        raise DatasetError('dataset must be UTF-8') from None
    rows, ids, families, prompts, conversations = [], set(), {}, {}, set()
    for number, line in enumerate(content.splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line, object_pairs_hook=unique_object,
                             parse_constant=lambda _: (_ for _ in ()).throw(DatasetError('non-finite JSON')))
            validate_record(row)
            if row['split'] != 'train':
                require(row['family'] not in training_only,
                        'training-only family cannot enter validation/test')
            if row['split'] != 'test':
                require(row['family'] not in reserved_families,
                        'reserved evaluation family cannot enter training/validation')
                candidate_views = task_views(row['messages'][1]['content'])
                require(not any(brief in candidate for brief in reserved_views for candidate in candidate_views),
                        'evaluation brief reused outside test split')
            require(row['id'] not in ids, 'duplicate record ID')
            ids.add(row['id'])
            family, split = row['family'], row['split']
            require(family not in families or families[family] == split, 'family crosses dataset splits')
            families[family] = split
            # Ignore system text: changing the wrapper must not conceal a reused task.
            prompt = task_identity(row['messages'][1]['content'])
            require(prompt not in prompts or prompts[prompt] == split, 'same prompt crosses dataset splits')
            prompts[prompt] = split
            conversation = fingerprint(prompt + '\n' + normalized(row['messages'][2]['content']))
            require(conversation not in conversations, 'duplicate example')
            conversations.add(conversation)
            rows.append(row)
        except (ValueError, TypeError, KeyError) as exc:
            # Do not print potentially private source content or Pydantic/JSON excerpts.
            detail = str(exc) if isinstance(exc, DatasetError) else 'malformed JSON or record'
            raise DatasetError(f'line {number}: {detail}') from None
    require(rows, 'empty dataset')
    counts = Counter(row['split'] for row in rows)
    reasons = []
    if any(row['review']['status'] != 'approved' for row in rows):
        reasons.append('records_without_approval')
    for split, minimum in MINIMUMS.items():
        if counts[split] < minimum:
            reasons.append(f'insufficient_{split}')
    report = {'version': VERSION, 'sha256': hashlib.sha256(raw).hexdigest(),
              'records': len(rows), 'counts': {s: counts[s] for s in MINIMUMS},
              'reviews': dict(Counter(row['review']['status'] for row in rows)),
              'export_ready': not reasons, 'blocking_reasons': reasons,
              'limits': 'Metadata validation is not semantic review, secret detection or proof authentication.'}
    return rows, report


def export_dataset(rows, report, root):
    require(report['export_ready'], 'dataset not ready for export')
    # Recheck actual rows; a stale or edited report cannot authorize different records.
    raw = ''.join(json.dumps(row, ensure_ascii=False) + '\n' for row in rows).encode()
    _, checked = validate_dataset(raw)
    require(checked['export_ready'], 'dataset not ready for export')
    base = WORKSPACES.resolve()
    root = Path(root).resolve()
    require(root == base or base in root.parents, 'export must remain in Linux workspaces')
    root.mkdir(parents=True, exist_ok=True)
    output = Path(tempfile.mkdtemp(prefix='sft-dataset-', dir=root))
    hashes = {}
    for split in MINIMUMS:
        # Holdout and validation are distinct files; no concatenated training output.
        payload = ''.join(json.dumps({'messages': row['messages']}, ensure_ascii=False) + '\n'
                          for row in rows if row['split'] == split)
        (output / f'{split}.jsonl').write_text(payload, encoding='utf-8')
        hashes[split] = fingerprint(payload)
    (output / 'reviewed-records.jsonl').write_bytes(raw)
    manifest = checked | {'input_sha256': report['sha256'], 'files_sha256': hashes,
                          'training_started': False}
    if 'batches' in report:
        manifest['batches'] = report['batches']
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    return output


def load_batches(paths):
    """Validate all batches together; separate-file approval cannot hide split leakage."""
    require(1 <= len(paths) <= 32, 'expected 1 to 32 explicit batch paths')
    chunks, batches, seen = [], [], set()
    size = 0
    for index, path in enumerate(paths):
        path = Path(path)
        resolved = path.resolve()
        require(resolved not in seen, 'duplicate batch path')
        seen.add(resolved)
        with path.open('rb') as stream:
            raw = stream.read(MAX_BYTES + 1)
        size += len(raw) + (1 if chunks else 0)
        require(size <= MAX_BYTES, 'combined dataset too large')
        # A malformed partial line must not become valid by concatenation.
        records, _ = validate_dataset(raw)
        batches.append({'index':index, 'sha256':hashlib.sha256(raw).hexdigest(), 'records':len(records)})
        chunks.append(raw)
    rows, report = validate_dataset(b'\n'.join(chunks))
    approved_counts = Counter(row['split'] for row in rows if row['review']['status'] == 'approved')
    report.update(batches=batches,
        approved_counts={split:approved_counts[split] for split in MINIMUMS},
        missing_approved={split:max(0,minimum-approved_counts[split]) for split,minimum in MINIMUMS.items()},
        skill_counts=dict(Counter(row['skill'] for row in rows)))
    return rows, report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('dataset', type=Path, nargs='+')
    parser.add_argument('--require-ready', action='store_true')
    parser.add_argument('--export-root', type=Path)
    args = parser.parse_args()
    try:
        rows, report = load_batches(args.dataset)
        if args.export_root:
            report['export_directory'] = str(export_dataset(rows, report, args.export_root))
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report['export_ready'] or not args.require_ready else 2
    except (OSError, DatasetError):
        # A malformed dataset may contain secrets even in keys or filenames.
        print(json.dumps({'error': 'Dataset validation/export failed; inspect locally without publishing private data.'}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
