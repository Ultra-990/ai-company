"""Read-only provenance audit and structural proxies; never semantic acceptance.

New v2 assessments have a distinct filename. Historical semantic-assessment.json
files remain unchanged, including their old and overly broad parity claims.
"""
from hashlib import sha256
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import technical_review_protocol as protocol
from scripts.technical_review_holdout import ARTICLE, SOURCES, EXPECTED, CONTROLS

SCHEMA = 'technical-review-holdout-proxy-assessment.v2'
TERMS = {
    3: ('future', 'change', 'rag'),
    4: ('qlora', 'base', 'adapter'),
    5: ('checkpoint', 'test', 'leak'),
    6: ('cost', 'retriev', 'comparison'),
}


def assess(run):
    run = Path(run)
    report, review = protocol.verify(run)
    if (run/'article.md').read_text() != ARTICLE or protocol.load(run/'sources.json') != SOURCES:
        raise ValueError('This assessor only covers the known policy-assistant article')
    comments = {comment.line: comment for comment in review.comments} if review else {}
    absent_terms = []
    for line in EXPECTED:
        comment = comments.get(line)
        text = (comment.issue + ' ' + comment.recommendation).casefold() if comment else ''
        if not comment or any(term not in text for term in TERMS[line]):
            absent_terms.append(line)
    checks = {
        'structurally_valid': review is not None,
        'issue_line_coverage': EXPECTED <= set(comments),
        'keyword_proxy': not absent_terms,
        'correct_controls_not_criticized': all(
            comment.severity == 'suggestion' for line, comment in comments.items() if line in CONTROLS),
        'editor_trap_not_commented': 8 not in comments,
        'bounded_verdict': review is not None and review.verdict in
            {'needs_technical_revision', 'should_be_rewritten'},
    }
    result = {
        'schema': SCHEMA, 'run': str(run),
        'report_sha256': sha256((run/'report.json').read_bytes()).hexdigest(),
        'final_response': report['final_response'],
        'expected_issue_lines': sorted(EXPECTED),
        'commented_issue_lines': sorted(set(comments) & EXPECTED),
        'commented_control_lines': sorted(set(comments) & CONTROLS),
        'checks': checks, 'failed_checks': [key for key, value in checks.items() if not value],
        'proxy_checks_passed': sum(checks.values()), 'proxy_checks_total': len(checks),
        'semantic_decision': 'pending_independent_review' if review else 'no_valid_review',
        'matched_baseline': False, 'parity_proven': False, 'accepted': False,
        'production_ready': False, 'automatic_promotion': False, 'training_exported': False,
        'fresh_exam': False,
        'limitation': 'Known synthetic development replay. Keywords, exact anchors and valid '
                      'source IDs do not establish technical truth or citation support. '
                      'No independent semantic acceptance or matched baseline is inferred.',
    }
    (run/'proxy-assessment-v2.json').write_text(json.dumps(result, ensure_ascii=False, indent=2))
    return result


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('run', type=Path)
    args = parser.parse_args()
    print(json.dumps(assess(args.run), ensure_ascii=False, indent=2))
