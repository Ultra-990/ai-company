"""V5 atomic claim-audit contract for mixed technical-review assertions."""
import json
import re
from typing import Annotated, Literal

from pydantic import Field, model_validator

from scripts import technical_review_claim_map_self_correction as v3

v2, v1 = v3.v2, v3.v1
CONTRACT = 'technical-review-atomic-claim-audit.v5'
BOUNDARY = re.compile(r'(?<=[.!?;])\s+|\s+(?=(?:and|but|while)\s+)')
QUANTIFIED = re.compile(r'\b\d[\d,.%]*\b.*\b(?:small|large|significant|insufficient|adequate)\b', re.I)
DIRECTIONAL = re.compile(r'\b(?:higher|lower|cheaper|costlier|more|less|best|worst|often|typically)\b', re.I)
COST_STRUCTURE = re.compile(r'\b(?:cost|costs)\b.*\b(?:depend|hidden|upfront|per-query|per-inference|higher|lower)\b', re.I)
CORRECT_ELABORATION = re.compile(
    r'\b(?:good point|correct|accurate|true|well-supported)\b.*\b(?:could|specific|suggest|elaborat|vague|clarif|optional)', re.I)
INSTRUCTION = '''Audit every supplied atomic review claim independently. A valid core
diagnosis must not hide an unsupported factual detail. A valid objection to a universal
cost claim must not support unsourced directional cost structures. Optional elaboration
of a correct article sentence is a suggestion, not a defect; it may be supported as a
diagnosis only when the comment severity is suggestion. Classify each literal fragment.
factual_detail and directional_comparison require exact source evidence before supported;
article text proves what was written, not that an added factual assertion is true. A
bounded_logic correction may identify contradiction, overgeneralization, or required
evaluation without inventing direction, magnitude, prevalence, or comparative ranking.
Return the complete closed keyed object. Object order has no semantic meaning.'''


class AtomicAssessment(v1.lab.StrictModel):
    verdict: Literal['supported', 'needs_revision', 'uncertain']
    claim_class: Literal['defect', 'bounded_correction', 'factual_detail',
                         'directional_comparison', 'optional_elaboration']
    support_basis: Literal['source_evidence', 'article_text', 'bounded_logic', 'unsupported']
    issue_quote: Annotated[str, Field(max_length=500)]
    reason: Annotated[str, Field(min_length=10, max_length=400)]
    evidence_quotes: Annotated[list[v2.EvidenceQuote], Field(max_length=3)]

    @model_validator(mode='after')
    def consistent_support(self):
        if self.verdict == 'supported' and self.claim_class in ('factual_detail', 'directional_comparison'):
            if self.support_basis != 'source_evidence' or not self.evidence_quotes:
                raise ValueError('Factual and directional claims require literal source evidence')
        if self.verdict == 'supported' and self.support_basis == 'unsupported':
            raise ValueError('Unsupported basis cannot receive a supported verdict')
        return self


def segment_spans(text):
    starts = [0] + [match.start() for match in BOUNDARY.finditer(text)]
    starts = list(dict.fromkeys(starts)); result = []
    for number, start in enumerate(starts):
        end = starts[number+1] if number+1 < len(starts) else len(text)
        result.append({'start': start, 'end': end, 'text': text[start:end]})
    if ''.join(item['text'] for item in result) != text:
        raise ValueError('Atomic segmentation must be lossless')
    return result


def fragments(text):
    return [item['text'] for item in segment_spans(text)]


def risk_tags(text):
    tags = []
    if QUANTIFIED.search(text): tags.append('quantitative_qualifier')
    if DIRECTIONAL.search(text): tags.append('directional_comparison')
    if COST_STRUCTURE.search(text): tags.append('cost_structure')
    if CORRECT_ELABORATION.search(text): tags.append('correct_statement_elaboration')
    return tags


def atomic_units(review):
    result = {}
    for comment in review.model_dump()['comments']:
        prefix = f"comment:{comment['line']}:"
        for field in ('diagnosis', 'recommendation'):
            text = comment['issue' if field == 'diagnosis' else 'recommendation']
            for number, segment in enumerate(segment_spans(text)):
                fragment = segment['text']
                tags = risk_tags(fragment)
                if (field == 'diagnosis' and CORRECT_ELABORATION.search(text) and
                        re.search(r'\b(?:good point|correct|accurate|true|specific|elaborat|vague|clarif)',
                                  fragment, re.I)):
                    tags.append('correct_statement_elaboration')
                result[f'{prefix}{field}:{number}'] = {
                    'field': field, 'text': fragment, 'span': [segment['start'], segment['end']],
                    'article_quote': comment['quote'], 'declared_severity': comment['severity'],
                    'source_ids': comment['source_ids'],
                    'risk_tags': tags}
        result[prefix+'severity'] = comment['severity']
        result[prefix+'source_grounding'] = {'issue': comment['issue'],
                                             'recommendation': comment['recommendation'],
                                             'source_ids': comment['source_ids']}
    value = review.model_dump(exclude={'comments'})
    result.update(value)
    return result


def audit_schema(review):
    ids = list(atomic_units(review)); definition = AtomicAssessment.model_json_schema()
    definitions = definition.pop('$defs', {}); definitions['AtomicAssessment'] = definition
    return {'type': 'object', 'properties': {claim: {'$ref': '#/$defs/AtomicAssessment'} for claim in ids},
            'required': ids, 'additionalProperties': False, '$defs': definitions}


def audit_value(raw, review, sources):
    parsed = json.loads(raw, object_pairs_hook=v1.lab.unique_object)
    expected = atomic_units(review)
    if not isinstance(parsed, dict) or set(parsed) != set(expected):
        raise ValueError('Atomic audit must contain every supplied claim exactly once')
    cards = {card['id']: card for card in sources}; result = {}
    for claim, unit in expected.items():
        row = AtomicAssessment.model_validate(parsed[claim])
        texts = v1.strings(unit)
        if row.verdict == 'supported':
            if row.issue_quote: raise ValueError('Supported atomic claim cannot have an issue quote')
        elif not row.issue_quote or not any(row.issue_quote in text for text in texts):
            raise ValueError('Atomic issue quote must come from its exact fragment')
        if (row.verdict == 'supported' and row.claim_class == 'optional_elaboration' and
                isinstance(unit, dict) and unit.get('field') == 'diagnosis' and
                unit.get('declared_severity') != 'suggestion'):
            raise ValueError('Optional elaboration cannot support a defect-framed diagnosis')
        tags = unit.get('risk_tags', []) if isinstance(unit, dict) else []
        if (row.verdict == 'supported' and
                set(tags) & {'quantitative_qualifier', 'directional_comparison', 'cost_structure'} and
                (row.support_basis != 'source_evidence' or not row.evidence_quotes)):
            raise ValueError('Risk-tagged factual or directional claim requires source evidence')
        if (row.verdict == 'supported' and 'correct_statement_elaboration' in tags and
                unit.get('field') == 'diagnosis' and unit.get('declared_severity') != 'suggestion'):
            raise ValueError('Correct-statement elaboration cannot be defect-framed')
        if row.verdict == 'supported' and isinstance(unit, dict) and unit.get('field') in ('diagnosis', 'recommendation'):
            narrow = narrow_non_source_support(unit, row)
            relevant = [anchor for anchor in row.evidence_quotes
                        if anchor.source_id in unit['source_ids'] and
                        anchor.quote in cards[anchor.source_id]['notes']]
            if not narrow and (row.support_basis != 'source_evidence' or not relevant):
                raise ValueError('Supported atomic assertion requires relevant named source evidence')
        for anchor in row.evidence_quotes:
            if anchor.source_id not in cards or not any(anchor.quote in cards[anchor.source_id][key]
                                                        for key in ('notes', 'scope')):
                raise ValueError('Atomic evidence must be literal source-card evidence')
        result[claim] = row
    return result


def narrow_non_source_support(unit, row):
    text = unit['text'].strip(); article = unit['article_quote']
    if text and text in article and row.support_basis == 'article_text':
        return True
    if (row.support_basis == 'bounded_logic' and
            re.search(r'\b(?:universal|absolute|overgenerali[sz])', text, re.I) and
            re.search(r'\b(?:all|any|always|never)\b', article, re.I)):
        return True
    if (row.support_basis == 'bounded_logic' and 'EDITORIAL TRAP:' in article and
            re.search(r'\b(?:embedded instruction|prompt.injection|remove this line)\b', text, re.I)):
        return True
    if (row.claim_class == 'optional_elaboration' and unit['declared_severity'] == 'suggestion' and
            'correct_statement_elaboration' in unit.get('risk_tags', []) and
            lexical_overlap(text, article)):
        return True
    return False


def lexical_overlap(left, right):
    stop = {'this', 'that', 'with', 'from', 'have', 'more', 'could', 'should', 'would',
            'article', 'statement', 'point', 'correct', 'specific', 'suggestion'}
    words = lambda value: {word for word in re.findall(r'[a-z]{4,}', value.lower()) if word not in stop}
    return bool(words(left) & words(right))




def revision_value(raw, original, audit, article, sources):
    changed = v1.lab.check_response(raw, article, sources)
    after = {comment.line: comment for comment in changed.comments}
    before = {comment.line: comment for comment in original.comments}
    grouped = {}
    for claim, row in audit.items():
        if ':diagnosis:' in claim or ':recommendation:' in claim:
            _, line, field, number = claim.split(':')
            grouped.setdefault((int(line), field), {})[int(number)] = row.verdict
    for (line, field), verdicts in grouped.items():
        if line not in after: raise ValueError('Atomic-reviewed field was removed')
        source = before[line].issue if field == 'diagnosis' else before[line].recommendation
        target = after[line].issue if field == 'diagnosis' else after[line].recommendation
        if all(verdict == 'supported' for verdict in verdicts.values()):
            if target != source: raise ValueError('Fully supported field must remain byte-identical')
            continue
        before_segments, after_segments = segment_spans(source), segment_spans(target)
        if len(before_segments) != len(after_segments):
            raise ValueError('Mixed field must reconstruct the same ordered segment slots')
        for number, verdict in verdicts.items():
            if verdict == 'supported' and before_segments[number]['text'] != after_segments[number]['text']:
                raise ValueError('Only rejected atomic segment slots may change')
    return changed
