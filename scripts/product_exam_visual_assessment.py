"""Read-only aggregation of independent, artifact-bound full-package reviews.

This consumes reviews written by the independent reviewer, never model ratings.
Even three accepted packages do not satisfy the separate correction exam.
"""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts import product_exam_assessment as technical

PARTS = ('source', 'capacity', 'dimensions', 'materials', 'care')
APPROVED = 'approved_synthetic_exam_package'
REJECTED = 'needs_visual_revision'


def review_package(folder):
    folder = Path(folder)
    path = folder/'independent-review.json'
    if not path.exists():
        return {'status': 'pending', 'accepted': False}
    review = technical.revision.read(path)
    checksum = technical.product.school.checksum
    if (review.get('schema') != 'product-infographic-independent-review.v1'
            or review.get('reviewer') != 'assistant_direct_visual_review'
            or review.get('decision') not in (APPROVED, REJECTED)
            or review.get('report_sha256') != checksum(folder/'report.json')
            or review.get('verification_sha256') != checksum(technical.revision.bounded(folder/'verification.json'))
            or review.get('training_exported') is not False
            or review.get('commercial_approved') is not False
            or review.get('autonomy_qualified') is not False
            or review.get('exam_feedback_used') is not False):
        raise ValueError('Independent exam review must bind the original unassisted package')
    images = ['source/preview.png']+[f'delivery/{part}-small.png' for part in PARTS[1:]]
    if review.get('inspected_images') != {
            name: checksum(technical.revision.bounded(folder/name)) for name in images}:
        raise ValueError('Review must cover the unchanged source and all four delivered previews')
    comments = review.get('comments')
    if (not isinstance(comments, dict) or set(comments) != set(PARTS)
            or any(not isinstance(notes, list) or not 1 <= len(notes) <= 10
                   or any(not isinstance(note, str) or not 1 <= len(note.strip()) <= 2000 for note in notes)
                   for notes in comments.values())):
        raise ValueError('Explicit independent observations for all five parts required')
    return {'status': 'accepted' if review['decision'] == APPROVED else 'rejected',
            'accepted': review['decision'] == APPROVED,
            'review_sha256': checksum(path), 'comments': comments}


def assess(path):
    evidence = technical.assess(path)
    scores = {arm: 0 for arm in technical.exam.ARMS}
    outcomes = []
    for case in evidence['cases']:
        review = review_package(case['package']) if case['measured_pass'] else {
            'status': 'technical_failure', 'accepted': False}
        scores[case['arm']] += int(review['accepted'])
        outcomes.append(case | {'visual_review': review})
    return {'schema': 'product-full-package-visual-assessment.v1',
            'exam_report_sha256': evidence['exam_report_sha256'],
            'integrity_verified': True, 'technical_scores': evidence['scores'],
            'visually_accepted_scores': scores, 'cases': outcomes,
            'reviews_complete': all(case['visual_review']['status'] != 'pending' for case in outcomes),
            'all_three_packages_accepted': {arm: score == 3 for arm, score in scores.items()},
            'autonomous_correction_evidence_required': True,
            'autonomy_qualified': False, 'commercial_approved': False,
            'training_exported': False, 'production_changed': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('exam', type=Path)
    args = parser.parse_args()
    print(json.dumps(assess(args.exam), ensure_ascii=False, indent=2))
