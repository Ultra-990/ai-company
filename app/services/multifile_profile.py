"""Pure, bounded inspection of a future stdlib-only multi-module runner profile.

Source is data. This module never imports it, installs dependencies or starts
processes. Compatibility is not execution authorization or a test result.
"""
from __future__ import annotations

import ast
import keyword
from pathlib import PurePosixPath

from app.services.workspace_packages import validate_files

PROFILE = 'python-web-multifile-v1'
REQUIRED = {'app.py', 'index.html', 'README.md', 'modules/__init__.py', 'tests/__init__.py'}
ROOT_FILES = {'app.py', 'index.html', 'README.md', 'style.css', 'app.js'}
STATIC_SUFFIXES = {'.html', '.css', '.js', '.json', '.txt'}
MAX_DEPTH = 6


def inspect_sources(files: dict[str, str], *, check_syntax: bool = True) -> dict:
    issues = []

    def issue(code, path, message, line=None):
        issues.append(dict(code=code, path=path, message=message, line=line))

    result = dict(profile=PROFILE, compatible=False, can_execute=False,
                  runtime_status='tests_available', executed=False,
                  tests_passed=None, issues=issues, test_files=[])
    try:
        validate_files(files)
    except (ValueError, TypeError) as exc:
        issue('invalid_package', None, str(exc))
        return result
    for path in sorted(REQUIRED - files.keys()):
        issue('missing_file', path, 'Dodaj wymagany plik profilu.')
    for path, content in sorted(files.items()):
        parts = path.split('/')
        name = PurePosixPath(path)
        python_package = len(parts) > 1 and parts[0] in {'modules', 'tests'} and name.suffix == '.py'
        static = len(parts) > 1 and parts[0] == 'static' and name.suffix in STATIC_SUFFIXES
        if path not in ROOT_FILES and not python_package and not static:
            issue('unsupported_path', path, 'Dozwolone: pliki główne, modules/*.py, tests/*.py i lokalne static/. Bez instalacji zależności.')
            continue
        if len(parts) > MAX_DEPTH:
            issue('path_depth', path, 'Maksymalnie sześć segmentów ścieżki.')
        if not content.strip() and not (python_package and name.name == '__init__.py'):
            issue('empty_file', path, 'Plik jest pusty; pusty może być jedynie __init__.py.')
        if python_package:
            identifiers = parts[:-1] + [name.stem]
            if any(not value.isidentifier() or keyword.iskeyword(value) for value in identifiers):
                issue('python_name', path, 'Nazwy pakietów i modułów muszą być identyfikatorami Pythona.')
            for depth in range(1, len(parts)):
                initializer = '/'.join(parts[:depth] + ['__init__.py'])
                if initializer not in files:
                    issue('missing_initializer', initializer, 'Dodaj __init__.py, aby importy i odkrywanie testów były jednoznaczne.')
            if parts[0] == 'tests' and name.name.startswith('test_') and name.name != 'test_.py':
                result['test_files'].append(path)
        if check_syntax and name.suffix == '.py':
            try:
                # Parser only: no compile/exec/import of the application on the host.
                ast.parse(content, filename=path, feature_version=(3, 10))
            except SyntaxError as exc:
                issue('python_syntax', path, 'Nieprawidłowa składnia dla profilu Python 3.10.', exc.lineno)
            except (ValueError, RecursionError, MemoryError):
                issue('python_syntax', path, 'Nie można bezpiecznie przeanalizować składni pliku.')
    if not result['test_files']:
        issue('missing_tests', 'tests/', 'Dodaj tests/test_*.py z rzeczywistymi testami unittest. Sama nazwa nie dowodzi istnienia asercji.')
    # Shared missing initializers can be referenced by multiple modules.
    result['issues'] = list({(i['code'], i['path'], i['line']): i for i in issues}.values())
    result['compatible'] = not result['issues']
    return result


def require_sources(files: dict[str, str]) -> None:
    result = inspect_sources(files)
    if not result['compatible']:
        first = result['issues'][0]
        raise ValueError(f"{first['path'] or 'Paczka'}: {first['message']}")


def private_http_paths(files: dict[str, str]) -> list[str]:
    """Trusted probe targets, derived from every non-public source, not caller commands."""
    require_sources(files)
    public = {'index.html', 'style.css', 'app.js'}
    return ['/' + path for path in sorted(files) if path not in public and not path.startswith('static/')]
