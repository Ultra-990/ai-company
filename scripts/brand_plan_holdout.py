"""New text claims against preserved model-authored SVGs; labels withheld."""
from copy import deepcopy
from scripts import brand_plan_review as REVIEWER

CONTRACT = 'brand-plan-review-holdout.v2'
SOURCES = {'coastal-claims': 'identity-4wzg1fnx', 'ember-claims': 'identity-ii5cd4fw',
           'morning-claims': 'identity-v0fs3gxq', 'supper-claims': 'identity-ykhokw_f'}
CASES = (
    ('coastal-claims', [
        'Use Arial for the logo wordmark and Georgia for supporting card text.',
        'Use the separately supplied text-only SVG in narrow spaces.',
        'Keep one capital-letter height of clear space around the complete logo.',
        'The complete logo is proven readable at a width of 7 mm.',
        'A wave and flame sit inside a circle above a straight Arial wordmark.',
        'The fish-and-leaf concept places its wordmark on a circular text path.'
    ], [False, True, False, True, False, True]),
    ('ember-claims', [
        'Use the dark monochrome mark against a light background.',
        'Use Georgia for the logo wordmark and Arial for the card contact text.',
        'The supplied small preview omits the restaurant name for symbol-only use.',
        'All supplied variants remain readable on dark and light paper without modification.',
        'The orange flame ring encloses the restaurant name within its circumference.',
        'A pale oval appears above the straight dark wordmark in the second concept.'
    ], [False, False, True, True, True, False]),
    ('morning-claims', [
        'Use the supplied 240-pixel preview for digital layouts at its native dimensions.',
        'The delivered wordmark is set in Arial Light at weight 300.',
        'Keep two capital-letter heights of clear space around the logo.',
        'The 16 mm minimum width has been confirmed by print legibility testing.',
        'A green branch-like arc and dots appear above a straight wordmark.',
        'The second concept curves the name inside the circular symbol.'
    ], [False, True, False, True, False, True]),
    ('supper-claims', [
        'Retain the complete logo drawing when resizing the preview for digital layouts.',
        'The delivered text uses Arial at weights 700 and 400.',
        'The delivery includes a separate bowl-only SVG for avatar use.',
        'The dark monochrome mark is guaranteed readable on a background of the identical ink color.',
        'The continuous wave mark is accompanied by a wordmark in Arial weight 500.',
        'A circular bowl and two steam lines sit above a straight Arial wordmark.'
    ], [False, False, True, True, True, False]),
)


def data(case):
    if case not in CASES: raise ValueError('Frozen expanded-review case required')
    identity, fields, _ = case
    legacy = REVIEWER.legacy
    package = legacy.brand.ROOT/SOURCES[identity]
    original, value = legacy.inputs(package)
    value = REVIEWER.expand(value, package)
    value['source_report_sha256'] = legacy.brand.school.checksum(package/'report.json')
    value['fixture_kind'] = 'New evaluator-authored text claims against preserved local-model SVGs; not a new design job.'
    value['plan']['guidelines'] = deepcopy(fields[:4])
    value['plan']['concept_a'], value['plan']['concept_b'] = fields[4:]
    return value
