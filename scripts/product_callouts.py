"""Measured functional annotations; never generate or repair artwork."""
import math
import re

LEGACY_CONTRACT = 'functional-callouts.v1'
LINE_CONTRACT = 'functional-callouts.v2'
RECTANGLE_CONTRACT = 'functional-callouts.v3'
CONTACT_CONTRACT = 'functional-callouts.v4'
CONTRACT = 'functional-callouts.v5'

RULES = '''Functional annotations are independently measured, not inferred from
their presence. Use actual line shapes for dimension markers and material
leaders. For dimensions: one vertical line must span the product's exact
top/bottom (tolerance 12 units), outside its left or right edge by 20..180;
one horizontal line must span its full width, above/below by 20..180.
Keep each corresponding fact box within 140 units of its dimension line.
For materials: connect each fact to its actual colored body/lid with a line
or connected chain of lines (endpoint joins within 6 units). One endpoint
must touch visible paint of that part, the other be within 80 units of its
fact box; don't cross text or other leaders. Use the measured source part boxes to plan.
Headlines may describe only supplied facts; no durability, thermal, leak,
certification, environmental or warranty claims. You choose every coordinate.'''


def stage_rules(panel):
    common = ('Headlines describe supplied facts only; no durability, thermal, leak, '
              'certification, environmental or warranty claims. You choose every coordinate.\n')
    if panel == 'dimensions':
        return common+'''ACTIVE PURPOSE: dimensions. Use visible lines or thin rectangle bars spanning the
actual top/bottom or full width within 12 units, outside the corresponding
edge by 20..180. Keep the matching fact box within 140 units of its line.
Use the measured product bbox and transform to calculate real edges.'''
    if panel == 'materials':
        return common+'''ACTIVE PURPOSE: materials. Connect each exact fact to visible
paint of its body/lid with visible lines or thin rectangle bars forming a
connected chain (joins within 6 units).
The opposite endpoint approaches the fact box within 80 units. Leaders
must not cross each other or text. Use the measured source part boxes.'''
    if panel in ('capacity', 'care'):
        return common+f'''ACTIVE PURPOSE: {panel} facts only. Keep the product and supplied
facts primary. Measurement brackets and material leaders belong to other
panels; do not introduce them here. Use restrained relevant decoration.'''
    raise ValueError('Known communication purpose required')


def validate_contract(value):
    if value not in (None, LEGACY_CONTRACT, LINE_CONTRACT, RECTANGLE_CONTRACT, CONTACT_CONTRACT, CONTRACT):
        raise ValueError('Unknown functional annotation contract')


def paint(color):
    return 'rgb('+', '.join(str(int(color[i:i+2], 16)) for i in (1, 3, 5))+')'


def point_box_distance(point, box):
    x, y, w, h = box
    return math.hypot(max(x-point[0], 0, point[0]-x-w),
                      max(y-point[1], 0, point[1]-y-h))


def line_box_distance(line, box):
    # Dimension markers are axis aligned. Box gap, not midpoint distance:
    # labels may be aligned to either end of a long marker.
    a, b = line['start'], line['end']
    x, y, w, h = box
    return math.hypot(max(min(a[0], b[0])-x-w, x-max(a[0], b[0]), 0),
                      max(min(a[1], b[1])-y-h, y-max(a[1], b[1]), 0))


def endpoint_matches(line, side, color, *, allow_contact=False):
    actual = line['product_endpoint_fills'][side]
    if actual == color: return True
    if actual is not None or not allow_contact or line.get('endpoint_contact_radius') != 1:
        return False
    contacts = line.get('product_endpoint_contact_fills', [])
    # Accept only unambiguous paint within one canvas unit (0.4 preview px).
    # A neighboring part never overrides an exact hit on the wrong part.
    return len(contacts) == 2 and contacts[side] == [color]


def connected_to_fact(lines, color, box, *, allow_contact=False):
    endpoints = [(i, side) for i, line in enumerate(lines) for side in (0, 1)
                 if endpoint_matches(line, side, color, allow_contact=allow_contact)]
    visited = set()
    while endpoints:
        i, side = endpoints.pop()
        if (i, side) in visited:
            continue
        visited.add((i, side))
        # Traverse at least one segment before testing proximity to the fact.
        end = lines[i]['end' if side == 0 else 'start']
        if point_box_distance(end, box) <= 80:
            return True
        for j, line in enumerate(lines):
            if j == i:
                continue
            for next_side, point in enumerate((line['start'], line['end'])):
                if math.dist(end, point) <= 6:
                    endpoints.append((j, next_side))
    return False


def crossing_point(first, second):
    a, b = first['start'], first['end']; c, d = second['start'], second['end']
    cross = lambda x, y: x[0]*y[1]-x[1]*y[0]
    u = [b[i]-a[i] for i in (0, 1)]; v = [d[i]-c[i] for i in (0, 1)]
    denominator = cross(u, v)
    if abs(denominator) < 1e-6: return None
    delta = [c[i]-a[i] for i in (0, 1)]
    t, s = cross(delta, v)/denominator, cross(delta, u)/denominator
    if not (0 < t < 1 and 0 < s < 1): return None
    point = [a[i]+t*u[i] for i in (0, 1)]
    return point if all(math.dist(point, end) > 6 for end in (a, b, c, d)) else None


def issues(measured, panel, style, *, contract=CONTRACT):
    validate_contract(contract)
    defects = []
    text = measured['layout'][1:]
    headline = text[0]['text']
    if re.search(r'\b(lasts?|durab\w*|leak\w*|thermal\w*|insulat\w*|certif\w*|'
                 r'warrant\w*|eco\w*|sustainab\w*|recycl\w*)\b', headline, re.I):
        defects.append({'kind': 'unsupported_headline_claim', 'headline': headline,
                        'required': 'describe only the frozen supplier facts'})
    if panel not in ('dimensions', 'materials'):
        return defects
    segments = measured.get('panel_line_segments', [])
    kinds = ('line', 'rectangle_bar') if contract in (RECTANGLE_CONTRACT, CONTACT_CONTRACT, CONTRACT) else ('line',)
    lines = [line for line in segments if line.get('kind') in kinds
             and math.dist(line['start'], line['end']) >= 12
             and line.get('stroke_width', 0) > 0 and line.get('visible_samples', 0) > 0]
    if len(measured.get('group_layout', [])) != 1 or len(text) != 3:
        return defects+[{'kind': 'missing_annotation_geometry'}]
    left, top, width, height = measured['group_layout'][0]['bbox']
    right, bottom = left+width, top+height
    facts = text[1:]
    if contract == CONTRACT:
        prefixes = ('Height:', 'Diameter:') if panel == 'dimensions' else ('Body:', 'Lid:')
        ordered = [[fact for fact in facts if fact['text'].startswith(prefix)] for prefix in prefixes]
        if any(len(matches) != 1 for matches in ordered):
            return defects+[{'kind': 'missing_unique_supplier_fact_roles'}]
        facts = [matches[0] for matches in ordered]
    if panel == 'dimensions':
        for axis, fact in ((1, facts[0]), (0, facts[1])):
            lo, hi = (top, bottom) if axis else (left, right)
            cross_lo, cross_hi = (left, right) if axis else (top, bottom)
            valid = False
            for line in lines:
                a, b = line['start'], line['end']
                cross = (a[1-axis]+b[1-axis])/2
                gap = max(cross_lo-cross, cross-cross_hi)
                if (abs(a[1-axis]-b[1-axis]) <= 2 and 20 <= gap <= 180
                        and abs(min(a[axis], b[axis])-lo) <= 12
                        and abs(max(a[axis], b[axis])-hi) <= 12
                        and line_box_distance(line, fact['bbox']) <= 140):
                    valid = True
                    break
            if not valid:
                defects.append({'kind': 'dimension_not_bound_to_product', 'fact': fact['text'],
                                'product_bbox': [left, top, width, height], 'fact_bbox': fact['bbox'],
                                'required': 'aligned spanning line, outside product by 20..180, within 140 of fact'})
    else:
        if not lines:
            return defects+[{'kind': 'missing_visible_material_leaders'}]
        if any(len(line.get('product_endpoint_fills', [])) != 2 for line in lines):
            return defects+[{'kind': 'missing_material_endpoint_measurement'}]
        if style['body_color'].lower() == style['cap_color'].lower():
            return defects+[{'kind': 'indistinguishable_material_parts'}]
        if contract in (LINE_CONTRACT, RECTANGLE_CONTRACT, CONTACT_CONTRACT, CONTRACT):
            for i, line in enumerate(lines):
                for j, other in enumerate(lines[i+1:], i+1):
                    point = crossing_point(line, other)
                    if point:
                        defects.append({'kind': 'crossed_material_leaders', 'line_indices': [i, j],
                                        'intersection': point, 'required': 'route leaders without interior crossings'})
        for part, fact in (('body', facts[0]), ('cap', facts[1])):
            if not connected_to_fact(lines, paint(style[part+'_color']), fact['bbox'], allow_contact=contract in (CONTACT_CONTRACT, CONTRACT)):
                defects.append({'kind': 'material_not_connected_to_part', 'fact': fact['text'],
                                'part': part, 'fact_bbox': fact['bbox'],
                                'required': 'connected leader from visible part paint to within 80 of fact; no text crossing'})
    return defects
