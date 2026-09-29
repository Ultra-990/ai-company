"""Pixel observations for the frozen flat cylindrical-bottle exercise.

Only inspect model output; never draw, normalize or repair its silhouette.
These checks do not replace independent visual acceptance or apply to arbitrary
commercial products with handles, feet, embossed rings or decorative profiles.
"""
from PIL import Image

LEGACY_CONTRACT = 'synthetic-bottle-contour.v1'
CONTRACT = 'synthetic-bottle-contour.v2'


def body_rows(image, body_color):
    if image.size != (600, 800):
        raise ValueError('Original 600x800 source preview required')
    target = tuple(int(body_color[i:i+2], 16) for i in (1, 3, 5))
    pixels = image.convert('RGBA').load()
    rows = []
    for y in range(image.height):
        xs = [x for x in range(image.width) if pixels[x, y][3] >= 240
              and max(abs(pixels[x, y][i]-target[i]) for i in range(3)) <= 12]
        if xs:
            rows.append({'y': y, 'left': xs[0], 'right': xs[-1], 'width': xs[-1]-xs[0]+1})
    return rows


def contour_issues(rows):
    if len(rows) < 20:
        return [{'kind': 'body_contour_not_measurable'}]
    widest = max(row['width'] for row in rows)
    top, bottom = rows[0]['y'], rows[-1]['y']
    height = bottom-top+1
    issues = []
    # Missing body-color rows may be painted surface bands, not physical gaps.
    # Only compare adjacent observed rows when measuring shoulder steps.
    shoulder_end = next(i for i, row in enumerate(rows) if row['width'] >= widest*.95)
    shoulder_rows = rows[:shoulder_end+1]
    if shoulder_end < 3 or shoulder_rows[0]['width'] >= widest*.9:
        issues.append({'kind': 'body_shoulders_not_visible',
                       'required': 'Show the brief-required curved shoulder transition into the wider body.'})
    else:
        jumps = [{'y': b['y'], 'left_step': a['left']-b['left'],
                  'right_step': b['right']-a['right']} for a, b in zip(shoulder_rows, shoulder_rows[1:])
                 if b['y'] == a['y']+1
                 and max(a['left']-b['left'], b['right']-a['right']) > max(4, widest*.08)]
        if jumps:
            issues.append({'kind': 'abrupt_square_shoulders', 'body_width': widest, 'steps': jumps[:10],
                           'required': 'The requested shoulders must curve into the body without abrupt square ledges.'})
    base = [row for row in rows if row['y'] >= top+height*.8]
    narrowest = base[0]['width']
    for row in base[1:]:
        if row['width']-narrowest > max(3, widest*.035):
            issues.append({'kind': 'base_contour_notch', 'y': row['y'],
                           'narrower_width': narrowest, 'later_width': row['width'],
                           'required': 'The rounded base must meet the body smoothly, without pinching inward and expanding again.'})
            break
        narrowest = min(narrowest, row['width'])
    return issues


def full_contour_issues(rows):
    issues = contour_issues(rows)
    if len(rows) < 20: return issues
    widths = [row['width'] for row in rows]
    left_max = []; maximum = 0
    for width in widths:
        maximum = max(maximum, width); left_max.append(maximum)
    right_max = []; maximum = 0
    for width in reversed(widths):
        maximum = max(maximum, width); right_max.append(maximum)
    right_max.reverse()
    tolerance = max(3, max(widths)*.035)
    notches = [{'y': row['y'], 'width': row['width'], 'neighboring_envelope_width': min(a, b)}
               for row, a, b in zip(rows, left_max, right_max, strict=True)
               if min(a, b)-row['width'] > tolerance]
    if notches and not any(issue['kind'] == 'base_contour_notch' for issue in issues):
        worst = max(notches, key=lambda entry: entry['neighboring_envelope_width']-entry['width'])
        issues.append({'kind': 'body_contour_notch', **worst,
                       'required': 'The cylindrical outline must join smoothly from shoulders through body to base, without narrowing between wider neighboring sections.'})
    return issues


def inspect(path, style, *, contract=CONTRACT):
    if contract not in (LEGACY_CONTRACT, CONTRACT): raise ValueError('Known source contour contract required')
    with Image.open(path) as image:
        rows = body_rows(image, style['body_color'])
    return {'contract': contract, 'observed_body_rows': len(rows),
            'issues': contour_issues(rows) if contract == LEGACY_CONTRACT else full_contour_issues(rows),
            'visual_acceptance': False}
