"""Independent structural assessor for a local-model restaurant brand package.

The assessor never edits artwork and never treats structural validity as visual
or commercial approval. A separate reviewer must record the visual decision.
"""
import argparse
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


REQUIRED = ('logo-a', 'logo-b', 'logo-selected', 'logo-monochrome', 'logo-small', 'business-card')


def assess(root):
    root = Path(root)
    report = json.loads((root / 'report.json').read_text())
    delivery = root / 'delivery'
    checks = []
    checks.append(('run_completed', report.get('status') == 'pending_independent_visual_review'))
    checks.append(('synthetic_only', report.get('brief', {}).get('synthetic') is True))
    checks.append(('manifest_present', (delivery / 'manifest.json').is_file()))
    checks.append(('style_plan_present', (delivery / 'style-plan.json').is_file()))
    checks.append(('brand_guide_present', (delivery / 'brand-guide.md').is_file()))
    for name in REQUIRED:
        svg = delivery / (name + '.svg')
        png = delivery / (name + '.png')
        pdf = delivery / (name + '.pdf')
        checks.extend([(name + '_svg', svg.is_file()), (name + '_png', png.is_file()),
                       (name + '_pdf', pdf.is_file())])
        if svg.is_file():
            try:
                tree = ET.parse(svg)
                checks.append((name + '_svg_parse', tree.getroot().tag.endswith('svg')))
                checks.append((name + '_no_raster_or_script', not any(
                    node.tag.endswith(('image', 'script')) for node in tree.getroot().iter())))
            except (OSError, ET.ParseError):
                checks.extend([(name + '_svg_parse', False), (name + '_no_raster_or_script', False)])
    manifest = json.loads((delivery / 'manifest.json').read_text()) if (delivery / 'manifest.json').is_file() else {}
    checks.append(('manifest_noncommercial', manifest.get('print_ready') is False and
                   manifest.get('commercial_delivery_approved') is False))
    review_path = root / 'independent-review.json'
    review = json.loads(review_path.read_text()) if review_path.is_file() else None
    visual = review.get('visual_acceptance') if isinstance(review, dict) else None
    return {
        'schema': 'restaurant-brand-package-assessment.v1',
        'package': str(root),
        'structural_checks': {name: bool(value) for name, value in checks},
        'structurally_valid': all(value for _, value in checks),
        'independent_visual_review_present': isinstance(visual, dict),
        'independent_visual_acceptance': visual.get('accepted') is True if isinstance(visual, dict) else False,
        'matched_baseline_present': bool(review and review.get('matched_baseline') is True),
        'training_exported': False,
        'commercial_delivery_approved': False,
        'limitation': 'Structural validity does not prove visual quality, baseline parity, or commercial readiness.',
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('package', type=Path)
    args = parser.parse_args()
    print(json.dumps(assess(args.package), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
