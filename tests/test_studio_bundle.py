from hashlib import sha256
from html.parser import HTMLParser
import io
import json
import stat
import warnings
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED

import pytest

from scripts import studio_bundle as bundle, studio_gallery
from scripts import upwork_web_case as case
from tests.test_studio_media import media


@pytest.fixture
def assembled(tmp_path, monkeypatch):
    path, _ = media(tmp_path, monkeypatch)
    files = {'app.py': "raise RuntimeError('must never execute on host')",
        'index.html': '<!doctype html><html><head></head><body><main id="main">'
            '<div class="art" aria-hidden="true"><i></i><i></i><i></i></div>'
            '<section id="services"></section></main></body></html>',
        'style.css': 'body{color:black}', 'app.js': '// base app', 'README.md': 'Demo',
        'modules/__init__.py': '', 'modules/logic.py': 'def estimate(*args): return 1200',
        'tests/__init__.py': '', 'tests/test_logic.py': 'import unittest\n'}
    report = {'schema': 'qwen-multifile-pilot.v1', 'scenario': 'studio', 'status': 'passed',
        'brief': case.BRIEF, 'independent_tests': case.ACCEPTANCE, 'accepted': False,
        'deployed': False, 'generation': {'content': json.dumps({'files': files})},
        'source_checksums': {k: sha256(v.encode()).hexdigest() for k, v in files.items()}}
    return bundle.assemble(report, studio_gallery.load_assets(path))


def test_roundtrip_includes_all_html_dependencies_and_original_business_logic(assembled):
    raw = bundle.pack(assembled, {'source_report_sha256': 'synthetic'})
    files, manifest = bundle.unpack(raw)
    assert files == assembled
    assert manifest['accepted'] is False and manifest['deployed'] is False
    assert files['modules/logic.py'] == b'def estimate(*args): return 1200'
    assert len(bundle.ASSETS) == 3
    class References(HTMLParser):
        def handle_starttag(self, tag, attrs):
            attrs = dict(attrs)
            ref = attrs.get('src') if tag in ('img', 'script') else attrs.get('href') if tag == 'link' else None
            if ref:
                assert ref in files, ref
    References().feed(files['index.html'].decode())
    assert b'static/studio-focus.js' in files['index.html']
    assert b'PUBLIC = {}' not in files['app.py']
    routes = bundle.public_routes(files)
    assert '/app.py' not in routes and '/modules/logic.py' not in routes
    assert all('/' + name in routes for name in bundle.ASSETS)
    # Stable bytes make archive identity independent of wall-clock creation time.
    assert raw == bundle.pack(assembled, {'source_report_sha256': 'synthetic'})


def rewrite(raw, mutation):
    with ZipFile(io.BytesIO(raw)) as archive:
        entries = [(i, archive.read(i)) for i in archive.infolist()]
    output = io.BytesIO()
    with ZipFile(output, 'w') as archive:
        for entry, data in mutation(entries):
            with warnings.catch_warnings():
                warnings.filterwarnings('ignore', message='Duplicate name:')
                archive.writestr(entry, data)
    return output.getvalue()


@pytest.mark.parametrize('mutation', ['missing', 'extra', 'traversal', 'duplicate', 'symlink', 'compressed', 'corrupt', 'accepted'])
def test_archive_rejects_incomplete_unsafe_or_changed_entries(assembled, mutation):
    raw = bundle.pack(assembled, {})
    def change(entries):
        for entry, data in entries:
            if mutation == 'symlink' and entry.filename == 'app.py':
                entry.external_attr = (stat.S_IFLNK | 0o777) << 16
            if mutation == 'compressed' and entry.filename == 'app.py':
                entry.compress_type = ZIP_DEFLATED
            if mutation == 'corrupt' and entry.filename in bundle.ASSETS:
                data += b'changed'
            if mutation == 'accepted' and entry.filename == 'bundle.json':
                data = json.dumps(json.loads(data) | {'accepted': True}).encode()
            yield entry, data
    # This helper deliberately constructs invalid archives, never extracts them.
    def mutated(entries):
        if mutation == 'missing': return entries[:-1]
        if mutation in ('extra', 'traversal', 'duplicate'):
            name = {'extra': 'secret.txt', 'traversal': '../escape', 'duplicate': entries[0][0].filename}[mutation]
            return entries + [(ZipInfo(name), b'bad')]
        return list(change(entries))
    with pytest.raises(ValueError):
        bundle.unpack(rewrite(raw, mutated))


def test_frame_uses_only_archived_bytes_even_if_repository_changes(assembled, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail('Preview must not reread overlay files')
    monkeypatch.setattr(studio_gallery, 'enhance', forbidden)
    html, frontend = bundle.frame_content(assembled)
    assert 'src="static/sculpture.png"' not in html
    assert html.count('data:image/png;base64,') == 4
    for name, text in frontend.items():
        assert text.encode() == assembled[name]


def test_binary_size_limits_do_not_weaken_production_packages(assembled):
    from app.services.workspace_packages import MAX_FILE_BYTES, MAX_TOTAL_BYTES
    assert MAX_FILE_BYTES == 256 * 1024 and MAX_TOTAL_BYTES == 1024 * 1024
    for name, content in [('static/sculpture.png', b'x' * 4_000_001), ('index.html', b'x' * 262145)]:
        with pytest.raises(ValueError):
            bundle.pack(assembled | {name: content}, {})


def test_staging_validates_before_write_and_preserves_exact_bytes(assembled, tmp_path):
    folder = tmp_path / 'stage'
    folder.mkdir(mode=0o700)
    runner = bundle.BundleRunner()
    with pytest.raises(ValueError):
        runner.stage_sources(folder, assembled | {'../escape': b'bad'})
    assert not list(folder.iterdir())
    runner.stage_sources(folder, assembled)
    for name, raw in assembled.items():
        assert (folder / name).read_bytes() == raw
        assert (folder / name).stat().st_mode & 0o222 == 0
    assert (folder / 'tests/test_independent_acceptance.py').read_text() == case.ACCEPTANCE
    with pytest.raises(ValueError):
        runner.stage_sources(folder, assembled)


def test_no_arbitrary_probe_or_bundle_location(tmp_path):
    for path in ['/api/tasks', 'https://remote/api/estimate', '../escape']:
        with pytest.raises(ValueError):
            bundle.BundleRunner(path)
    with pytest.raises(ValueError):
        bundle.read_bundle(tmp_path / 'outside.zip')


@pytest.mark.parametrize('result', [{'tests_ok': False, 'checks': []}, {'tests_ok': True, 'checks': ['/']}])
def test_incomplete_container_evidence_is_retained_and_never_passes(assembled, monkeypatch, result):
    monkeypatch.setattr(bundle, 'check_idle', lambda: None)
    monkeypatch.setattr(bundle, 'configuration', lambda: {})
    monkeypatch.setattr(bundle, 'checked_report', lambda *args: result)
    run = {'exit_code': 0, 'log': 'incomplete evidence'}
    monkeypatch.setattr(bundle.BundleRunner, 'run', lambda *args: run)
    with pytest.raises(bundle.BundleRunError) as exc:
        bundle.BundleRunner().execute(assembled)
    assert exc.value.run is run
