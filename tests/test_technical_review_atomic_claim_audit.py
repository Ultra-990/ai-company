import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from app.services.local_ollama import output_format
from scripts import technical_review_atomic_claim_audit as atomic
from scripts import technical_review_holdout as holdout


RUN = Path('/home/marcin/ai-company-workspaces/technical-review-holdout/final-correction-vi85m_7h')


def review():
    if RUN.exists(): return atomic.v1.lab.Review.model_validate(atomic.v1.base.load(RUN/'review.json'))
    raise RuntimeError('Preserved v4 review fixture is required')


def assessment_map(value):
    quotes = {'pilot': 'No confidence intervals, task slices, checkpoint-selection protocol, latency or error-cost measurements supplied.',
              'qlora': 'QLoRA backpropagates through a frozen quantized base into LoRA adapters',
              'rag': 'Retrieved non-parametric memory and parametric model memory can be combined and have different update/access properties.'}
    result = {}
    for claim, unit in atomic.atomic_units(value).items():
        risky = isinstance(unit, dict) and bool(unit.get('risk_tags'))
        atomic_text = isinstance(unit, dict) and unit.get('field') in ('diagnosis', 'recommendation')
        source_ids = unit.get('source_ids', []) if atomic_text else []
        rejected = risky or atomic_text and not source_ids
        result[claim] = {'verdict': 'needs_revision' if rejected else 'supported',
                         'claim_class': 'bounded_correction',
                         'support_basis': 'unsupported' if rejected else ('source_evidence' if atomic_text else 'bounded_logic'),
                         'issue_quote': unit['text'] if rejected else '',
                         'reason': 'Synthetic bounded atomic assessment for contract testing.',
                         'evidence_quotes': ([] if rejected or not atomic_text else [
                             {'source_id': source_ids[0], 'quote': quotes[source_ids[0]]}])}
    return result


def find_claim(value, text):
    return next(claim for claim, unit in atomic.atomic_units(value).items()
                if isinstance(unit, dict) and text in unit.get('text', ''))


def test_atomic_units_expose_hidden_sample_size_and_cost_directions():
    value = review(); units = atomic.atomic_units(value)
    assert any('1,000-example dataset is small' in unit.get('text', '')
               for unit in units.values() if isinstance(unit, dict))
    assert any('lower per-inference cost' in unit.get('text', '')
               for unit in units.values() if isinstance(unit, dict))
    assert any(unit.get('field') == 'diagnosis' and unit.get('declared_severity') == 'minor' and
               'good point' in unit.get('text', '') for unit in units.values() if isinstance(unit, dict))
    assert 'quantitative_qualifier' in units[find_claim(value, '1,000-example dataset is small')]['risk_tags']
    assert 'directional_comparison' in units[find_claim(value, 'lower per-inference cost')]['risk_tags']
    assert 'correct_statement_elaboration' in units[find_claim(value, 'good point')]['risk_tags']
    for comment in value.comments:
        for field in (comment.issue, comment.recommendation):
            spans = atomic.segment_spans(field)
            assert ''.join(item['text'] for item in spans) == field
            assert all(field[item['start']:item['end']] == item['text'] for item in spans)


@pytest.mark.parametrize('text,kind', [
    ('1,000-example dataset is small', 'factual_detail'),
    ('lower per-inference cost', 'directional_comparison')])
def test_unsourced_factual_or_directional_fragment_cannot_be_supported(text, kind):
    value = review(); raw = assessment_map(value); claim = find_claim(value, text)
    raw[claim].update(verdict='supported', issue_quote='', claim_class=kind, support_basis='bounded_logic')
    with pytest.raises(ValueError, match='source evidence'):
        atomic.audit_value(json.dumps(raw), value, holdout.SOURCES)
    raw[claim].update(verdict='needs_revision', support_basis='unsupported', issue_quote=text)
    parsed = atomic.audit_value(json.dumps(raw), value, holdout.SOURCES)
    assert parsed[claim].verdict == 'needs_revision'


def test_optional_elaboration_cannot_be_supported_as_minor_defect():
    value = review(); raw = assessment_map(value); claim = find_claim(value, 'good point')
    raw[claim].update(verdict='supported', issue_quote='', claim_class='optional_elaboration', support_basis='article_text')
    with pytest.raises(ValueError, match='defect-framed'):
        atomic.audit_value(json.dumps(raw), value, holdout.SOURCES)
    raw[claim].update(verdict='needs_revision', issue_quote='good point')
    assert atomic.audit_value(json.dumps(raw), value, holdout.SOURCES)[claim].verdict == 'needs_revision'


def test_writer_can_remove_rejected_detail_but_must_keep_supported_core():
    value = review(); raw = assessment_map(value)
    rejected = find_claim(value, '1,000-example dataset is small')
    raw[rejected].update(verdict='needs_revision', claim_class='factual_detail',
                         support_basis='unsupported', issue_quote='1,000-example dataset is small')
    parsed = atomic.audit_value(json.dumps(raw), value, holdout.SOURCES)
    changed = value.model_copy(deep=True)
    rejected_text = atomic.atomic_units(value)[rejected]['text']
    changed.comments[0].issue = value.comments[0].issue.replace(
        rejected_text, ' A sample-count adequacy claim needs a task-specific basis,', 1)
    result = atomic.revision_value(json.dumps(changed.model_dump()), value, parsed,
                                   holdout.ARTICLE, holdout.SOURCES)
    assert '1,000-example dataset is small' not in result.comments[0].issue
    changed.comments[0].issue = 'Only a generic replacement.'
    with pytest.raises(ValueError, match='segment slots|rejected atomic'):
        atomic.revision_value(json.dumps(changed.model_dump()), value, parsed,
                              holdout.ARTICLE, holdout.SOURCES)


@pytest.mark.parametrize('assertion', [
    'An 8% improvement may be misleading.',
    'Fine-tuning is a static process.',
    'Only the adapters are trained.'
])
def test_untagged_factual_assertion_cannot_bypass_source_requirement(assertion):
    value = review(); value.comments[0].issue = assertion
    raw = assessment_map(value); claim = next(key for key in raw if key.startswith('comment:2:diagnosis:'))
    raw[claim].update(verdict='supported', claim_class='bounded_correction',
                      support_basis='bounded_logic', issue_quote='', evidence_quotes=[])
    with pytest.raises(ValueError, match='requires relevant named source evidence'):
        atomic.audit_value(json.dumps(raw), value, holdout.SOURCES)


@pytest.mark.parametrize('mutation', ['reorder', 'connector', 'negation', 'collapse'])
def test_supported_segments_preserve_order_connectors_negation_and_duplicates(mutation):
    value = review(); value.comments[0].issue = (
        'Core defect. and keep connector. Never remove this. Repeat. Repeat.')
    raw = assessment_map(value); parsed = atomic.audit_value(json.dumps(raw), value, holdout.SOURCES)
    changed = value.model_copy(deep=True)
    replacements = {
        'reorder': 'Core defect. Never remove this. and keep connector. Repeat. Repeat.',
        'connector': 'Core defect. but keep connector. Never remove this. Repeat. Repeat.',
        'negation': 'Core defect. and keep connector. Always remove this. Repeat. Repeat.',
        'collapse': 'Core defect. and keep connector. Never remove this. Repeat.'}
    changed.comments[0].issue = replacements[mutation]
    with pytest.raises(ValueError, match='byte-identical'):
        atomic.revision_value(json.dumps(changed.model_dump()), value, parsed,
                              holdout.ARTICLE, holdout.SOURCES)


@pytest.mark.parametrize('fault', ['irrelevant_source', 'wrong_basis'])
def test_evidence_must_be_named_and_source_basis_explicit(fault):
    value = review(); raw = assessment_map(value)
    claim = find_claim(value, 'Fine-tuning is a static process')
    raw[claim].update(verdict='supported', issue_quote='', support_basis='source_evidence',
                      evidence_quotes=[{'source_id': 'rag', 'quote': 'Original RAG research, not a current platform comparison.'}])
    if fault == 'wrong_basis':
        raw[claim].update(support_basis='bounded_logic',
                          evidence_quotes=[{'source_id': 'rag', 'quote': 'different update/access properties'}])
    with pytest.raises(ValueError, match='relevant named source evidence'):
        atomic.audit_value(json.dumps(raw), value, holdout.SOURCES)


def test_supported_atomic_claim_accepts_matching_named_note_and_rejects_mismatched_id():
    value = review(); units = atomic.atomic_units(value)
    claim = find_claim(value, 'base model weights are frozen')
    assert units[claim]['source_ids'] == ['qlora']
    raw = assessment_map(value)
    raw[claim].update(verdict='supported', issue_quote='', support_basis='source_evidence',
                      evidence_quotes=[{'source_id': 'qlora',
                                        'quote': 'QLoRA backpropagates through a frozen quantized base into LoRA adapters'}])
    parsed = atomic.audit_value(json.dumps(raw), value, holdout.SOURCES)
    assert parsed[claim].verdict == 'supported'
    raw[claim]['evidence_quotes'] = [
        {'source_id': 'rag', 'quote': 'different update/access properties'}]
    with pytest.raises(ValueError, match='relevant named source evidence'):
        atomic.audit_value(json.dumps(raw), value, holdout.SOURCES)


def test_optional_label_cannot_exempt_arbitrary_factual_suggestion():
    value = review(); value.comments[0].severity = 'suggestion'
    value.comments[0].issue = 'A 1,000-example dataset is definitely inadequate.'
    raw = assessment_map(value); claim = next(key for key in raw if key.startswith('comment:2:diagnosis:'))
    raw[claim].update(verdict='supported', issue_quote='', claim_class='optional_elaboration',
                      support_basis='bounded_logic', evidence_quotes=[])
    with pytest.raises(ValueError, match='requires relevant named source evidence'):
        atomic.audit_value(json.dumps(raw), value, holdout.SOURCES)


def test_mixed_field_rejects_arbitrary_inserted_segment():
    value = review(); raw = assessment_map(value)
    rejected = find_claim(value, '1,000-example dataset is small')
    raw[rejected].update(verdict='needs_revision', support_basis='unsupported',
                         issue_quote='1,000-example dataset is small')
    parsed = atomic.audit_value(json.dumps(raw), value, holdout.SOURCES)
    changed = value.model_copy(deep=True)
    changed.comments[0].issue += ' An unrelated inserted assertion.'
    with pytest.raises(ValueError, match='same ordered segment slots'):
        atomic.revision_value(json.dumps(changed.model_dump()), value, parsed,
                              holdout.ARTICLE, holdout.SOURCES)


def test_closed_atomic_schema_fits_adapter_for_preserved_review():
    value = review(); schema = atomic.audit_schema(value)
    Draft202012Validator.check_schema(schema)
    assert schema['additionalProperties'] is False
    assert set(schema['required']) == set(schema['properties'])
    assert len(json.dumps(schema)) <= 16000
    assert output_format({'format': schema}) == schema


def test_preserved_v4_artifacts_are_read_only():
    if not RUN.exists(): pytest.skip('preserved v4 run unavailable')
    before = {path.name: path.read_bytes() for path in RUN.iterdir() if path.is_file()}
    assert atomic.v1.base.digest(RUN/'report.json') == '2f811271fac543760daaccbf383a3c0d41dd8b90143777c8894faf870f2f9292'
    assert atomic.v1.base.digest(RUN/'manifest.json') == '48d5a7181dd00c9cd69cb4780e3647657373422274802c0f5566eac7b08eed0f'
    implementation = RUN/'implementation/technical_review_final_correction.py'
    assert atomic.v1.base.digest(implementation) == '7a20b611eca21e54ebf66f8cd68d0a7c87804dcbc4085ac9d945890bb20b5c4f'
    assert implementation.read_bytes() == Path(atomic.v3.__file__).with_name('technical_review_final_correction.py').read_bytes()
    assert {path.name: path.read_bytes() for path in RUN.iterdir() if path.is_file()} == before
