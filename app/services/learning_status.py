"""Public-to-owner summary of private learning intake, without prompts or file paths."""
from datetime import datetime, timezone
import json
from pathlib import Path

STATE = Path('/home/marcin/ai-company-workspaces/learning-autopilot/state.json')


def status():
    result = {'phase': 'not_started', 'checked_at': None, 'fresh': False,
              'counts': {'train': 0, 'validation': 0, 'test': 0},
              'training_started': False, 'automatic_weight_training_available': False,
              'model_promotion_enabled': False,
              'note': 'Automatyczne zbieranie ocenionych danych i kontrola wejść. Trening wag nie jest jeszcze zautomatyzowany.'}
    if not STATE.exists(): return result
    if (any(p.is_symlink() for p in (STATE, *STATE.parents)) or not STATE.is_file()
            or STATE.stat().st_size > 1024*1024):
        raise ValueError('Nieprawidłowy raport nauki.')
    try:
        data = json.loads(STATE.read_text())
        if data['schema'] != 'learning-autopilot.v1' or data['phase'] != 'collecting_reviewed_data':
            raise ValueError('Unknown learning phase')
        counts = data['counts']
        if (set(counts) != {'train', 'validation', 'test'}
                or any(type(n) is not int or not 0 <= n <= 1500 for n in counts.values())
                or data['training_started'] is not False
                or data['automatic_weight_training_available'] is not False):
            raise ValueError('Unsupported learning report')
        checked = datetime.fromisoformat(data['checked_at'])
        if checked.tzinfo is None: raise ValueError('Timestamp has no timezone')
        age = (datetime.now(timezone.utc)-checked).total_seconds()
        result.update(phase=data['phase'], checked_at=checked.isoformat(), fresh=0 <= age <= 900,
                      counts=counts, approved_bundles=len(data['entries']),
                      rejected_or_failed_sources=len(data['errors']), skipped_sources=len(data['skipped']))
        return result
    except (ValueError, KeyError, TypeError, OSError) as exc:
        raise ValueError('Nie można potwierdzić aktualnego raportu nauki.') from exc
