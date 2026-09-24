"""Generate a separate local-model restaurant-brand holdout package."""
from copy import deepcopy
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts import brand_school


def run(variant='cedar'):
    original_brief = brand_school.BRIEF
    original_root = brand_school.ROOT
    briefs = {
      'cedar': {
        'restaurant_name': 'Cedar & Salt',
        'family': 'cedar-salt-brand-holdout-001',
        'split': 'validation',
        'concept': 'Fictional coastal neighborhood restaurant serving seasonal shared plates. Calm, tactile and welcoming; avoid luxury crests and generic fork/knife clip art.',
        'audience': 'Friends meeting for relaxed dinners near the coast.',
        'contacts': ['Reservations by email', 'hello@cedarandsalt.example', 'cedarandsalt.example'],
        'synthetic': True, 'printer_specifications_supplied': False,
      },
      'maple': {
        'restaurant_name': 'Maple & Ember', 'family': 'maple-ember-brand-holdout-001', 'split': 'validation',
        'concept': 'Fictional neighborhood restaurant serving wood-fired seasonal plates. Warm, grounded and welcoming; avoid luxury crests and generic fork/knife clip art.',
        'audience': 'Neighbors meeting for relaxed dinners around a shared table.',
        'contacts': ['Reservations by email', 'hello@mapleember.example', 'mapleember.example'],
        'synthetic': True, 'printer_specifications_supplied': False,
      },
    }
    if variant not in briefs: raise ValueError('Known holdout variant required')
    brand_school.BRIEF = briefs[variant]
    brand_school.ROOT = Path('/home/marcin/ai-company-workspaces/brand-school-holdout-'+variant)
    try:
        return brand_school.run()
    finally:
        brand_school.BRIEF = original_brief
        brand_school.ROOT = original_root


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(); parser.add_argument('--run', action='store_true'); parser.add_argument('--variant', choices=('cedar','maple'), default='cedar'); args=parser.parse_args()
    out, report = run(args.variant)
    print({'report': str(out/'report.json'), 'status': report['status']})
