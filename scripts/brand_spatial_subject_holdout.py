"""Fresh grammatical-role examples, disjoint from the first extraction test."""
from scripts import brand_spatial_subject_review as REVIEWER

CONTRACT = 'brand-spatial-subject-holdout.v2'
CASES = (
    ('low-marks', {'a': 'A leaf emblem rests below the straight lettering.', 'b': 'The restaurant name sits above a circular mark.'}, {'a': ['below'], 'b': ['below']}),
    ('high-marks', {'a': 'A bowl is positioned above the name.', 'b': 'The wordmark is placed underneath a curved arc.'}, {'a': ['above'], 'b': ['above']}),
    ('right-marks', {'a': 'An emblem stands to the right of the wordmark.', 'b': 'The name appears to the left of the icon.'}, {'a': ['right'], 'b': ['right']}),
    ('left-marks', {'a': 'The lettering stands to the right of the circle.', 'b': 'The symbol sits to the left of the name.'}, {'a': ['left'], 'b': ['left']}),
    ('framed-names', {'a': 'A ring encloses the restaurant name.', 'b': 'The wordmark is inside an oval border.'}, {'a': ['surrounds'], 'b': ['surrounds']}),
    ('overlap', {'a': 'The wordmark overlaps the circular emblem.', 'b': 'A leaf passes through the letters.'}, {'a': ['overlaps'], 'b': ['overlaps']}),
    ('diagonal', {'a': 'The symbol sits below and to the right of the text.', 'b': 'The wordmark is to the right of and below the emblem.'}, {'a': ['below', 'right'], 'b': ['left', 'above']}),
    ('general-layout', {'a': 'An abstract sun motif suggests a relaxed mood.', 'b': 'The symbol and lettering are arranged side by side horizontally.'}, {'a': ['unspecified'], 'b': ['side_by_side']}),
)
