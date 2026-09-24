"""Independent qualification contract for the five requested Upwork services.

This module only evaluates evidence supplied by bounded local-model pilots. It
does not create client work, infer quality from a passing unit test, or turn a
partial pilot into a parity claim. Every service needs its own held-out result
and a matched assistant/baseline comparison.
"""
from datetime import date
import argparse
import json
from pathlib import Path

SERVICES = {
    'technical_review': {
        'label': 'LLM fine-tuning technical review',
        'evidence': ('local_model_output', 'line_anchor_contract', 'semantic_acceptance',
                     'heldout_review_exam', 'matched_baseline'),
    },
    'interior_pinterest': {
        'label': 'AI interior/Pinterest imagery',
        'evidence': ('local_model_output', 'image_rights_record', 'visual_acceptance',
                     'content_package_checks', 'matched_baseline'),
    },
    'vector_flyer': {
        'label': 'print-ready flyer recreation',
        'evidence': ('local_model_output', 'svg_contract', 'pdf_preflight',
                     'independent_visual_acceptance', 'matched_baseline'),
    },
    'amazon_infographic': {
        'label': 'Amazon product infographics',
        'evidence': ('local_model_output', 'product_fidelity_checks', 'four_panel_package',
                     'independent_visual_acceptance', 'matched_baseline'),
    },
    'restaurant_branding': {
        'label': 'restaurant branding and logo',
        'evidence': ('local_model_output', 'editable_asset_contract', 'package_preflight',
                     'independent_visual_acceptance', 'matched_baseline'),
    },
}

SCHEMA = 'upwork-service-qualification.v1'


def empty_evidence():
    return {service: {key: False for key in spec['evidence']} for service, spec in SERVICES.items()}


def evaluate(evidence, *, checked_on=None):
    """Evaluate a complete evidence matrix without guessing missing values."""
    if not isinstance(evidence, dict) or set(evidence) != set(SERVICES):
        raise ValueError('Evidence must name exactly the five requested services')
    checked_on = checked_on or date.today().isoformat()
    date.fromisoformat(checked_on)
    results = {}
    for service, spec in SERVICES.items():
        record = evidence[service]
        if not isinstance(record, dict) or set(record) != set(spec['evidence']):
            raise ValueError(f'Incomplete evidence fields for {service}')
        if any(type(value) is not bool for value in record.values()):
            raise ValueError(f'Evidence values must be booleans for {service}')
        missing = [key for key, value in record.items() if value is not True]
        results[service] = {
            'label': spec['label'],
            'qualified': not missing,
            'missing': missing,
            'parity_proven': record['matched_baseline'] and not missing,
        }
    qualified = [key for key, value in results.items() if value['qualified']]
    return {
        'schema': SCHEMA,
        'checked_on': checked_on,
        'services': results,
        'qualified_services': qualified,
        'qualified_count': len(qualified),
        'all_five_qualified': len(qualified) == len(SERVICES),
        'parity_claim_allowed': len(qualified) == len(SERVICES),
        'production_ready': False,
        'automatic_promotion': False,
        'limitation': 'Evidence contract only; it does not replace independent review or prove commercial readiness.',
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence', type=Path)
    args = parser.parse_args()
    if args.evidence:
        evidence = json.loads(args.evidence.read_text())
    else:
        evidence = empty_evidence()
    print(json.dumps(evaluate(evidence), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
