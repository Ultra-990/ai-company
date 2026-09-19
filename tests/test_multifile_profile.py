import ast
from pathlib import Path

import pytest
from sqlalchemy import func, select

from app.models.artifact import Artifact
from app.models.package_run import PackageRun
from app.services.application_layout import execution_profile
from app.services.application_profile import parse_sources
from app.services.multifile_profile import inspect_sources, private_http_paths
from app.services.multifile_staging import stage_sources
from tests.conftest import OWNER_HEADERS, WORKER_HEADERS
from tests.test_workspace_packages import save

FILES = {
    'app.py': 'from modules.logic import total\nif __name__ == "__main__":\n    raise RuntimeError("never execute on host")\n',
    'modules/__init__.py': '',
    'modules/logic.py': 'def total(hours, rate):\n    return hours * rate\n',
    'tests/__init__.py': '',
    'tests/test_logic.py': 'import unittest\nfrom modules.logic import total\nclass Checks(unittest.TestCase):\n    def test_total(self):\n        self.assertEqual(total(8, 322), 2576)\n',
    'index.html': '<!doctype html><title>Fixture</title>',
    'README.md': 'Synthetic fixture, not a working HTTP server.',
    'static/css/site.css': 'body { color: blue; }',
}


def test_valid_layout_is_not_execution_or_test_success():
    original = dict(FILES)
    result = inspect_sources(FILES)
    assert result['compatible'] and result['issues'] == []
    assert result['test_files'] == ['tests/test_logic.py']
    assert result['tests_passed'] is None
    assert not result['can_execute'] and not result['executed']
    assert result['runtime_status'] == 'tests_available'
    assert FILES == original
    assert execution_profile(FILES) == 'python-web-multifile-v1'
    import json
    with pytest.raises(ValueError):
        parse_sources(json.dumps({'files': FILES}))


@pytest.mark.parametrize('path,source,code', [
    ('../escape.py', 'pass', 'invalid_package'),
    ('/etc/passwd', 'pass', 'invalid_package'),
    ('modules/.secret.py', 'pass', 'invalid_package'),
    ('Modules/logic.py', 'pass', 'invalid_package'),
    ('modules', 'pass', 'invalid_package'),
    ('requirements.txt', 'requests', 'unsupported_path'),
    ('runner_harness.py', 'pass', 'unsupported_path'),
    ('preview_request.json', '{}', 'unsupported_path'),
    ('sys.py', 'pass', 'unsupported_path'),
    ('static/plugin.py', 'pass', 'unsupported_path'),
    ('static/graphic.svg', '<svg/>', 'unsupported_path'),
    ('modules/bad-name.py', 'pass', 'python_name'),
    ('modules/class.py', 'pass', 'python_name'),
    ('modules/bad.py', 'def broken(:', 'python_syntax'),
    ('modules/empty.py', ' ', 'empty_file'),
    ('modules/typed.py', 'type NewType = int', 'python_syntax'),
    ('modules/sub/logic.py', 'pass', 'missing_initializer'),
    ('static/a/b/c/d/e/file.txt', 'x', 'path_depth'),
])
def test_rejects_incompatible_files(path, source, code):
    result = inspect_sources(FILES | {path: source})
    assert not result['compatible']
    assert code in {i['code'] for i in result['issues']}
    assert not result['can_execute']


def test_nested_modules_and_test_packages_require_initializers():
    sources = FILES | {'modules/sub/__init__.py': '', 'modules/sub/calc.py': 'pass',
                      'tests/sub/__init__.py': '', 'tests/sub/test_calc.py': 'pass'}
    assert inspect_sources(sources)['compatible']
    del sources['modules/sub/__init__.py']
    sources['modules/sub/other.py'] = 'pass'
    missing = [i for i in inspect_sources(sources)['issues'] if i['path'] == 'modules/sub/__init__.py']
    assert len(missing) == 1


def test_missing_tests_and_entrypoint_are_explicit():
    sources = {p: c for p, c in FILES.items() if p not in {'app.py', 'tests/test_logic.py'}}
    result = inspect_sources(sources)
    assert {'missing_file', 'missing_tests'} <= {i['code'] for i in result['issues']}


def test_source_paths_are_private_but_static_assets_are_public():
    probes = private_http_paths(FILES)
    assert '/modules/logic.py' in probes and '/tests/test_logic.py' in probes
    assert '/README.md' in probes and '/app.py' in probes
    assert '/static/css/site.css' not in probes and '/index.html' not in probes


def test_staging_preserves_text_and_does_not_execute(tmp_path):
    folder = tmp_path / 'staging'
    folder.mkdir(mode=0o700)
    files = FILES | {'modules/text.py': '# Zażółć\r\nraise RuntimeError("never run")\r\n'}
    stage_sources(folder, files)
    for path, content in files.items():
        assert (folder / path).read_bytes() == content.encode()
        assert (folder / path).stat().st_mode & 0o777 == 0o444
    assert (folder / 'modules').stat().st_mode & 0o777 == 0o755
    assert not (folder / 'runner_harness.py').exists()


@pytest.mark.parametrize('kind', ['not_empty', 'public', 'symlink', 'bad_sources'])
def test_staging_refuses_unsafe_destinations_before_writing(tmp_path, kind):
    folder = tmp_path / 'staging'
    folder.mkdir(mode=0o700)
    if kind == 'not_empty':
        (folder / 'keep').write_text('keep')
    if kind == 'public':
        folder.chmod(0o755)
    if kind == 'symlink':
        link = tmp_path / 'link'
        link.symlink_to(folder, target_is_directory=True)
        folder = link
    sources = FILES | ({'../escape': 'bad'} if kind == 'bad_sources' else {})
    with pytest.raises(ValueError):
        stage_sources(folder, sources)
    assert not (folder / 'app.py').exists()
    if kind == 'not_empty':
        assert (folder / 'keep').read_text() == 'keep'


def test_inspection_is_authenticated_version_bound_and_read_only(client, task_repository):
    task = task_repository.create(title='Synthetic multifile task')
    package = save(client, task.id, files=FILES).json()
    route = f"/api/tasks/{task.id}/workspace-packages/{package['artifact_id']}/multifile-inspection"
    for headers, status in (({}, 401), (WORKER_HEADERS, 403), (OWNER_HEADERS, 200)):
        response = client.get(route, headers=headers)
        assert response.status_code == status, response.text
    result = response.json()
    assert result['compatible'] and not result['can_execute']
    assert result['package_checksum'] == package['checksum'] and result['task_id'] == task.id
    assert response.headers['cache-control'] == 'no-store'
    assert 'never execute' not in response.text
    assert task_repository.get_required(task.id).progress == task.progress
    with task_repository._session_factory() as session:
        assert session.scalar(select(func.count()).select_from(PackageRun)) == 0
        assert session.scalar(select(func.count()).select_from(Artifact)) == 1
        session.get(Artifact, package['artifact_id']).content = '{}'
        session.commit()
    assert client.get(route, headers=OWNER_HEADERS).status_code == 409


def test_no_foreign_task_package_inspection(client, task_repository):
    task = task_repository.create(title='First task')
    other = task_repository.create(title='Other task')
    package = save(client, task.id, files=FILES).json()
    route = f"/api/tasks/{other.id}/workspace-packages/{package['artifact_id']}/multifile-inspection"
    assert client.get(route, headers=OWNER_HEADERS).status_code == 404


def test_harness_bootstrap_contract_without_import_or_execution():
    tree = ast.parse(Path('app/runner/multifile_harness.py').read_text())
    strings = {n.targets[0].id: ast.literal_eval(n.value) for n in tree.body
               if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name)
               and n.targets[0].id in {'TEST_LOADER', 'APP_LOADER'}}
    for value in strings.values():
        ast.parse(value)
        assert "sys.path.insert(0,'/workspace')" in value
    assert "pattern='test_*.py'" in strings['TEST_LOADER']
    assert 'suite.countTestCases()<1:sys.exit(3)' in strings['TEST_LOADER']
    assert "runpy.run_path('/workspace/app.py',run_name='__main__')" in strings['APP_LOADER']
    # Trusted harness launches both children with the same fixed isolation flags.
    commands = [n for n in ast.walk(tree) if isinstance(n, ast.List) and len(n.elts) == 6
                and isinstance(n.elts[-1], ast.Name) and n.elts[-1].id in strings]
    assert len(commands) == 2
    assert all([ast.literal_eval(v) for v in n.elts[1:5]] == ['-I', '-S', '-B', '-c'] for n in commands)
