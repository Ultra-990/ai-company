"""Closed export sizes; these are not claims about native model resolution."""

EXPORT_RESOLUTIONS = {
    '720p': (1280, 720),
    '1080p': (1920, 1080),
    '1440p': (2560, 1440),
    '2160p': (3840, 2160),
}


def export_dimensions(resolution, framing='landscape'):
    if resolution not in EXPORT_RESOLUTIONS or framing not in {'landscape', 'portrait', 'square'}:
        raise ValueError('video_format_invalid')
    dimensions = EXPORT_RESOLUTIONS[resolution]
    # Legacy square sources are fitted inside a landscape export.
    return dimensions[::-1] if framing == 'portrait' else dimensions
