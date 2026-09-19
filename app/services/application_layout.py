"""Source-layout compatibility only, not proof of execution or available resources."""
REQUIRED_FILES = {'app.py', 'test_app.py', 'index.html', 'README.md'}
OPTIONAL_FILES = {'style.css', 'app.js'}


def execution_profile(files):
    if (REQUIRED_FILES <= set(files) <= REQUIRED_FILES | OPTIONAL_FILES
            and all(isinstance(value, str) and value.strip() for value in files.values())):
        return 'python-web-v1'
    # Metadata describes the supported layout, not a test verdict. Syntax is
    # checked at the execution boundary rather than parsing every list item.
    from app.services.multifile_profile import inspect_sources, PROFILE
    if inspect_sources(files, check_syntax=False)['compatible']:
        return PROFILE
    return None
