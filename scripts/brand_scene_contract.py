"""Stage-specific brand scene requirements and measured margins; no asset edits."""
import json
import re
import xml.etree.ElementTree as ET
from scripts import brand_school as b
from scripts.brand_spatial_review import box

CONTRACT = 'brand-scoped-scene.v1'
COMMON = '''Return only the complete JSON scene for the requested stage. All
geometry, placement, fonts, weights and colors are your responsibility. Use
the approved palette and text exactly; never substitute a tagline for a name.
All numeric attributes are strings. Choose text-anchor start/middle/end.
The y coordinate is a text baseline; use measured text extents for spacing.
Shapes: rect:x,y,width,height,fill; circle:cx,cy,r,fill;
ellipse:cx,cy,rx,ry,fill; line:x1,y1,x2,y2,stroke,stroke-width;
path:d,fill,stroke,stroke-width. Optional stroke/stroke-width allowed.
Use 1..12 simple shapes, explicit text attributes and weights 400 or 700.
No scripts, groups, images, CSS, gradients, rotation or external resources.
Keep decorative shape bounds separate from text bounds. Do not repeat a
rejected placement. Preserve all already correct brief requirements.'''
LOGO = '''This stage creates ONE LOGO on a 600x360 canvas, not a business card.
Include exactly one text: the required restaurant name. No tagline or contacts.
Use the heading font, text size 20..120, and no full-canvas background.
All visible geometry and text must stay within an 18px margin on every edge.
Choose symbol placement consistent with the concept; no fixed baseline is
prescribed. Keep the wordmark and symbol separate with clear spacing.
The monochrome tool replaces every non-none fill/stroke with monochrome_ink;
choose geometry whose details remain visible under that conversion.'''
CARD = '''This stage creates ONE BUSINESS CARD on an 850x550 canvas.
Include exactly four texts: the approved tagline and three approved contacts.
The tool inserts the provided logo unchanged at your logo_placement x/y/scale;
do not repeat its name as a separate text. Use the body font, text size >=28.
Keep visible content within a 35px margin, except the full paper background.
Choose line baselines from measured text and placed logo bounds. Background
decorations must remain outside every text bounding box, including the logo.'''


def rules(kind):
    if kind not in ('logo', 'card'): raise ValueError('Known scene stage required')
    return COMMON+'\n'+(LOGO if kind == 'logo' else CARD)


def expected_copy(kind, plan, brief):
    return [brief['restaurant_name']] if kind == 'logo' else [plan['tagline'], *brief['contacts']]


def schema(kind, plan, brief):
    result = b.scene_schema(kind, plan)
    result['properties']['texts']['items']['properties']['text'] = {
        'type': 'string', 'enum': expected_copy(kind, plan, brief)}
    return result


def compile_scene(raw, plan, *, kind, brief, logo=None):
    scene = json.loads(raw, object_pairs_hook=b.unique_object)
    texts = scene.get('texts', []) if isinstance(scene, dict) else []
    observed = [v.get('text') for v in texts if isinstance(v, dict)] if isinstance(texts, list) else []
    expected = expected_copy(kind, plan, brief)
    if any(not isinstance(v, str) for v in observed) or sorted(observed) != sorted(expected):
        raise ValueError(json.dumps({'kind': 'required_stage_copy_mismatch', 'stage': kind,
            'expected_texts': expected, 'observed_texts': observed}))
    return b.compile_scene(raw, plan, kind=kind, logo=logo)


def margin_findings(svg, rendered, kind, paper):
    root = ET.fromstring(svg); tags = {'rect', 'circle', 'ellipse', 'line', 'path'}
    nodes = [e for e in root.iter() if e.tag.rsplit('}', 1)[-1] in tags]
    if len(nodes) != len(rendered['shape_layout']): raise ValueError('Exact margin shape mapping required')
    parents = {child: parent for parent in root.iter() for child in parent}
    width, height, margin = (600, 360, 18) if kind == 'logo' else (850, 550, 35)
    findings = []
    for index, (node, row) in enumerate(zip(nodes, rendered['shape_layout'])):
        tag = node.tag.rsplit('}', 1)[-1]
        if tag != row['tag']: raise ValueError('Margin shape order changed')
        bounds = box(row['bbox']); fill, stroke = node.get('fill', 'black'), node.get('stroke', 'none')
        if fill == 'none' and stroke == 'none': continue
        if (kind == 'card' and parents[node] is root and tag == 'rect'
                and bounds == [0, 0, width, height] and fill.lower() == paper.lower() and stroke == 'none'):
            continue
        scale = 1
        parent = parents[node]
        if parent is not root:
            match = re.fullmatch(r'translate\([\d.]+ [\d.]+\) scale\(([\d.]+)\)', parent.get('transform', ''))
            if not match or parents.get(parent) is not root: raise ValueError('Bounded inserted-logo transform required')
            scale = float(match[1])
        pad = float(node.get('stroke-width', '1'))*scale/2 if stroke != 'none' else 0
        left, top, right, bottom = bounds
        bounds = [left-pad, top-pad, right+pad, bottom+pad]
        if left-pad < margin or top-pad < margin or right+pad > width-margin or bottom+pad > height-margin:
            findings.append({'kind': 'shape_margin_violation', 'shape_index': index,
                'measured_bounds_with_half_stroke': bounds, 'required_margin_px': margin,
                'canvas': [width, height], 'scope': 'Browser geometry plus half stroke width; not an exact bound for arbitrary miter joins.'})
    return findings
