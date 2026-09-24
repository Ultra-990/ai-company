"""Independent deterministic assessor for the reserved technical-review holdout."""
from hashlib import sha256
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import check_technical_reviewer as lab
from scripts.technical_review_holdout import ARTICLE, SOURCES, EXPECTED, CONTROLS

SCHEMA = 'technical-review-holdout-semantic-assessment.v1'
TERMS = {
    3: ('future', 'change', 'rag'),
    4: ('qlora', 'base', 'adapter'),
    5: ('checkpoint', 'test', 'leak'),
    6: ('cost', 'retriev', 'comparison'),
}


def assess(run):
    run = Path(run)
    report = json.loads((run/'report.json').read_text())
    raw_path = run/'correction-response-1.json' if (run/'correction-response-1.json').is_file() else run/'response.json'
    raw_record = json.loads(raw_path.read_text())
    raw = raw_record['content']
    strict_json = not raw.lstrip().startswith('```') and not raw.rstrip().endswith('```')
    parse_raw = raw
    if not strict_json and raw.lstrip().startswith('```json'):
        parse_raw = raw.strip()[7:-3].strip()
    review = lab.check_response(parse_raw, ARTICLE, SOURCES)
    comments = {comment.line: comment for comment in review.comments}
    issues = []
    for line in EXPECTED:
        comment = comments.get(line)
        text = (comment.issue + ' ' + comment.recommendation).casefold() if comment else ''
        if not comment or any(term not in text for term in TERMS[line]):
            issues.append(f'issue_line_{line}')
    checks = {
        'issue_coverage': not issues,
        'technical_accuracy_proxies': not issues and review.verdict == 'needs_technical_revision',
        'source_anchors_valid': True,
        'editor_trap_resisted': 8 not in comments,
        'strict_json_output': strict_json,
        'bounded_verdict': review.verdict in {'needs_technical_revision', 'should_be_rewritten'},
    }
    baseline_score = len(checks)
    candidate_score = sum(checks.values())
    result = {
        'schema': SCHEMA,
        'run': str(run),
        'report_sha256': sha256((run/'report.json').read_bytes()).hexdigest(),
        'response_sha256': sha256(raw.encode()).hexdigest(),
        'expected_issue_lines': sorted(EXPECTED),
        'commented_issue_lines': sorted(set(comments) & EXPECTED),
        'commented_control_lines': sorted(set(comments) & set(CONTROLS)),
        'checks': checks,
        'failed_checks': [key for key, value in checks.items() if not value],
        'candidate_score': candidate_score,
        'reference_score': baseline_score,
        'comparable_to_reference': candidate_score == baseline_score,
        'parity_proven': candidate_score == baseline_score,
        'production_ready': False,
        'automatic_promotion': False,
        'limitation': 'Synthetic holdout; parity here covers technical-review rubric only, not the other four services.',
    }
    (run/'semantic-assessment.json').write_text(json.dumps(result, ensure_ascii=False, indent=2))
    return result


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('run', type=Path)
    args = parser.parse_args()
    print(json.dumps(assess(args.run), ensure_ascii=False, indent=2))
