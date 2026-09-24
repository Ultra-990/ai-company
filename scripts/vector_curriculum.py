"""Frozen families and split assignments, declared before generating variants."""
from hashlib import sha256
import json

from scripts.vector_school_contract import SOURCE_BRIEF

LEGACY = 'print-fair-development-v1'
COMMON = '''Create an original fictional event leaflet for a synthetic teaching exercise.
Invent exactly eight short, distinct English ASCII text lines: event name, tagline,
date, time, venue, two activity/entry details, closing invitation. No real contact
details, brands or addresses. Title at most 20 characters, other lines at most
42 characters. Keep every line readable, separate and inside the 12-unit margin.
Use exactly eight editable text elements, at least three simple decorative shapes
and only the static SVG subset in the system instruction. You author the complete
wording and artwork. Do not reuse the former Ink and Paper Fair design. '''
CURRICULA = {
    LEGACY: {'family': 'community-print-fair-001', 'data_split': 'development', 'brief': SOURCE_BRIEF},
    'garden-workshop-train-v1': {'family': 'garden-workshop-001', 'data_split': 'train',
        'brief': COMMON + '''Topic: a neighborhood seed and planting workshop.
Use an asymmetric layout with left-aligned text, a narrow vertical accent band,
one simple abstract sprout illustration on the right, and generous empty space.
Choose a warm cream, deep olive and muted clay palette. Keep shapes away from
text; no centered target/ring illustration or top/bottom stripe template.'''},
    'restaurant-tasting-train-v1': {'family': 'restaurant-tasting-001', 'data_split': 'train',
        'brief': COMMON + '''Topic: a fictional small restaurant's seasonal tasting evening.
Use a dark full-page background, a light inset rectangular information panel,
serif headline above it, short left-aligned details within it and a small simple
plate-like geometric symbol. Choose navy, warm ivory and muted copper.
Create a balanced hospitality design, not a business card or real restaurant logo.'''},
    'vinyl-market-train-v1': {'family': 'vinyl-market-001', 'data_split': 'train',
        'brief': COMMON + '''Topic: a fictional independent vinyl record market.
Use a bold top headline, an off-center record illustration, a wide horizontal
accent block through the middle, and a compact bottom information area. Select
cream, dark ink and brick red; choose a clear sans-serif hierarchy. Keep all
eight text lines separate from the illustration and from one another.'''},
    'bookbinding-fair-train-v1': {'family': 'bookbinding-fair-001', 'data_split': 'train',
        'brief': COMMON + '''Topic: a fictional bookbinding and paper craft fair.
Use a tall centered title block, a low horizontal information band, and one
simple geometric stitched-book symbol in the upper right. Select parchment,
charcoal and deep teal with one rust accent. Keep the title separate from the
symbol and all event details inside the lower band; use a calm editorial grid.''',},
    'science-evening-validation-v1': {'family': 'science-evening-001', 'data_split': 'validation',
        'brief': COMMON + '''Topic: a fictional community astronomy demonstration evening.
Use a two-column information area below a large open header, blue-gray and white
with a yellow accent, and a small cluster of geometric star/planet shapes.
Keep each short text line in its column and make the reading order unambiguous.'''},
    'travel-club-test-v1': {'family': 'travel-club-001', 'data_split': 'test',
        'brief': COMMON + '''Topic: a fictional rail travel club's illustrated talk.
Use a narrow sidebar with two short information lines, a large main column for
the remaining six lines, and a small geometric route diagram made from straight
lines and circles. Use pale blue, deep charcoal and one orange accent. Avoid
other curriculum layouts; make a coherent editorial composition.'''},
    'travel-club-test-v2': {'family': 'travel-club-v2-001', 'data_split': 'test',
        'brief': COMMON + '''Topic: a fictional rail travel club's illustrated talk.
Use a dark sidebar exactly 172 units wide on the left and a pale main column on
the right. Put exactly two short information lines, each no more than 24
characters, inside the sidebar at x=20 with baselines near y=700 and y=735;
use a high-contrast light or orange fill. Put the other six text lines in the
main column at x>=200. Include a small geometric route diagram in the sidebar
above those lines, made from straight lines and circles. Use pale blue, deep
charcoal and one orange accent. Do not let any text cross the sidebar boundary
or overlap another line.'''},
    'night-market-test-v1': {'family': 'night-market-001', 'data_split': 'test',
        'brief': COMMON + '''Topic: a fictional evening makers market.
Use a deep indigo full-page background with a warm cream inset panel, a bold
cream headline at the top, six short event lines in a clear left-aligned stack,
and one small geometric lantern symbol in the upper right. Use cream, indigo,
muted coral and one warm gold accent. Keep all eight text lines readable,
separate, inside the inset panel, and away from the symbol; use a calm modern
market-poster composition.'''},
}


def metadata(report):
    name = report.get('curriculum', LEGACY)
    if name not in CURRICULA: raise ValueError('Unknown frozen vector curriculum')
    curriculum = CURRICULA[name]
    expected = {'curriculum': name, 'family': curriculum['family'], 'data_split': curriculum['data_split']}
    if name != LEGACY:
        expected['curriculum_sha256'] = sha256(json.dumps(curriculum, sort_keys=True).encode()).hexdigest()
        if 'schema' in report and not set(expected) <= set(report):
            raise ValueError('Incomplete frozen curriculum metadata')
    for key, value in expected.items():
        if key in report and report[key] != value: raise ValueError('Curriculum or split was changed')
    return expected


def require_learning(report):
    result = metadata(report)
    if result['data_split'] not in {'development', 'train'}:
        raise ValueError('Reserved validation/test family cannot enter school repairs or training')
    return result
