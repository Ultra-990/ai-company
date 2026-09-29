from PIL import Image

from scripts import product_silhouette as silhouette


def rows(widths):
    return [{'y': 100+i, 'left': 300-width//2, 'right': 299-width//2+width,
             'width': width} for i, width in enumerate(widths)]


def smooth_widths():
    return list(range(60, 121, 2))+[120]*180+list(range(118, 59, -2))


def test_smooth_joined_body_passes_without_claiming_visual_acceptance():
    assert silhouette.contour_issues(rows(smooth_widths())) == []


def test_square_shoulders_and_notched_base_are_distinct_observations():
    widths = [60]*30+[120]*180+[90, 98, 106, 114, 120]+list(range(118, 59, -2))
    issues = silhouette.contour_issues(rows(widths))
    assert {issue['kind'] for issue in issues} == {'abrupt_square_shoulders', 'base_contour_notch'}


def test_no_visible_shoulders_fail_without_mislabeling_surface_bands_as_gaps():
    profile = rows([120]*200+list(range(118, 59, -2)))
    del profile[50]
    assert {issue['kind'] for issue in silhouette.contour_issues(profile)} == {'body_shoulders_not_visible'}


def test_foreign_color_bands_do_not_become_false_physical_gap_findings():
    profile = rows(smooth_widths())
    del profile[70:76]
    assert silhouette.contour_issues(profile) == []


def test_new_contour_catches_shoulder_body_notches_without_changing_historical_base_check():
    profile = rows(list(range(60, 121, 2))+[100, 108, 114]+[120]*180+list(range(118, 59, -2)))
    assert silhouette.contour_issues(profile) == []
    assert silhouette.full_contour_issues(profile)[0]['kind'] == 'body_contour_notch'
    assert silhouette.full_contour_issues(rows(smooth_widths())) == []


def test_measurement_uses_visible_body_paint_and_ignores_clear_or_foreign_pixels():
    image = Image.new('RGBA', (600, 800), (0, 0, 0, 0))
    image.putpixel((100, 100), (51, 102, 153, 255))
    image.putpixel((110, 100), (51, 102, 153, 255))
    image.putpixel((120, 100), (51, 102, 153, 0))
    image.putpixel((130, 100), (250, 250, 250, 255))
    assert silhouette.body_rows(image, '#336699') == [
        {'y': 100, 'left': 100, 'right': 110, 'width': 11}]
