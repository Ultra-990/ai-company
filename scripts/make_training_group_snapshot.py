"""Create a deterministic private intake snapshot for one training family group."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.prepare_training_data import unique_object


def digest(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def make(source, output, prefix):
    source = Path(source); output = Path(output)
    state = json.loads(source.read_text(), object_pairs_hook=unique_object)
    if state.get('schema') != 'learning-autopilot.v1':
        raise ValueError('Recognized autopilot snapshot required')
    if not prefix or '/' in prefix:
        raise ValueError('Simple family prefix required')
    selected = {key: value for key, value in state.get('entries', {}).items()
                if any(row.get('family', '').startswith(prefix)
                       for row in _rows(value))}
    if not selected:
        raise ValueError('No training entries match the requested family prefix')
    families = sorted({row['family'] for value in selected.values() for row in _rows(value)})
    result = {
        'schema': 'learning-autopilot-group.v1',
        'source_state_sha256': digest(source),
        'group': prefix,
        'entries': selected,
        'families': families,
        'counts': {'train': sum(len(_rows(v)) for v in selected.values()),
                   'validation': state['counts']['validation'], 'test': state['counts']['test']},
        'reserved_exams': state.get('reserved_exams', []),
        'baseline_evaluation': state.get('baseline_evaluation', {}),
        'rollback_plan': state.get('rollback_plan', {}),
        'training_started': False,
        'automatic_promotion': False,
        'production_changed': False,
        'limitation': 'Group snapshot for isolated research; it is not a qualification or deployment decision.'
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    return result


def _rows(entry):
    bundle = Path(entry['bundle'])
    rows = []
    for line in (bundle/'records.jsonl').read_text().splitlines():
        rows.append(json.loads(line, object_pairs_hook=unique_object))
    return rows


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('state', type=Path); parser.add_argument('output', type=Path)
    parser.add_argument('--family-prefix', required=True)
    args = parser.parse_args()
    print(json.dumps(make(args.state, args.output, args.family_prefix), ensure_ascii=False))
