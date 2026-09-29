"""Keep large product-colored decorations clear of the inserted product.

This is a conservative bounding-box rule for the synthetic exercise. It does
not identify arbitrary real product parts or replace visual acceptance. Thin
annotation bars and small endpoint marks remain allowed.
"""
import xml.etree.ElementTree as ET

from scripts.vector_school_contract import NS

CONTRACT = 'product-paint-separation.v1'
INSTRUCTION = ('Keep large filled decorative shapes in body_color or cap_color '
    'outside the complete measured product bounding box. Such same-color paint '
    'can merge into the bottle and change its visible silhouette even though '
    'the inserted source is unchanged. Thin annotation bars and small endpoint '
    'marks are allowed; choose all corrections yourself.')


def issues(svg, measured, style):
    groups = measured.get('group_layout', [])
    if len(groups) != 1:
        return [{'kind': 'missing_product_paint_reference'}]
    product = groups[0]['bbox']
    shapes = [node for node in ET.fromstring(svg) if node.tag not in (NS+'g', NS+'text')]
    layouts = measured.get('shape_layout', [])
    if len(layouts) < len(shapes):
        return [{'kind': 'missing_decoration_paint_measurements'}]
    colors = {style['body_color'].lower(), style['cap_color'].lower()}
    found = []
    px, py, pw, ph = product
    for index, (node, layout) in enumerate(zip(shapes, layouts)):
        if layout.get('tag') != node.tag.removeprefix(NS):
            raise ValueError('Decoration geometry does not match its measured shape')
        if node.attrib.get('fill', 'none').lower() not in colors: continue
        x, y, w, h = layout['bbox']
        # The annotation contract already recognizes bars up to 16 units.
        if min(w, h) <= 16: continue
        overlap = [min(x+w, px+pw)-max(x, px), min(y+h, py+ph)-max(y, py)]
        if min(overlap) > 0:
            found.append({'kind': 'decoration_merges_with_product', 'shape_index': index,
                'decoration_bbox': layout['bbox'], 'product_bbox': product,
                'fill': node.attrib['fill'], 'required': INSTRUCTION})
    return found
