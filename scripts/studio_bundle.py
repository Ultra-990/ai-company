"""Local synthetic binary bundle. No extraction, execution or production DB writes."""
import base64
from hashlib import sha256
import io
import json
import os
from pathlib import Path
import stat
from uuid import uuid4
from zipfile import ZipFile, ZipInfo, ZIP_STORED

from scripts import studio_gallery as gallery, upwork_web_case as case
from scripts.prepare_training_data import unique_object
from scripts.serve_studio_preview import sources, estimate_path
from scripts.check_qwen_multifile import checked_report
from scripts.compare_local_models import check_idle
from app.services.container_runner import ContainerRunner, configuration

ROOT = Path('/home/marcin/ai-company-workspaces/qwen-training')
HERE = Path(__file__).resolve().parent
OVERLAYS = ('studio-gallery.css', 'studio-scene.css', 'studio-tools.css',
            'studio-focus.js', 'studio-navigation.js', 'studio-gallery.js',
            'studio-scene.js', 'studio-tools.js')
BASE = {'app.py', 'index.html', 'style.css', 'app.js', 'README.md',
        'modules/__init__.py', 'modules/logic.py', 'tests/__init__.py', 'tests/test_logic.py'}
ASSETS = {'static/' + key + '.png' for key in gallery.IDS}
NAMES = BASE | ASSETS | {'static/' + name for name in OVERLAYS}
MAX_BYTES = 14_000_000
HARNESS = HERE.parent / 'app/runner/studio_bundle_harness.py'


def checksums(files):
    return {name: sha256(raw).hexdigest() for name, raw in sorted(files.items())}


def validate(files):
    if set(files) != NAMES or any(type(raw) is not bytes for raw in files.values()):
        raise ValueError('Exact standalone studio inventory required')
    if sum(map(len, files.values())) > MAX_BYTES:
        raise ValueError('Bundle exceeds total size limit')
    for name, raw in files.items():
        if len(raw) > (4_000_000 if name in ASSETS else 262144):
            raise ValueError('Bundle file exceeds size limit')
        if name not in ASSETS:
            raw.decode('utf-8')


def public_routes(files):
    types = {'.html': 'text/html; charset=utf-8', '.css': 'text/css; charset=utf-8',
             '.js': 'text/javascript; charset=utf-8', '.png': 'image/png'}
    return {('/' if name == 'index.html' else '/' + name): (name, types[Path(name).suffix])
            for name in sorted(files) if Path(name).suffix in types}


def assemble(report, assets):
    original = sources(report)
    if set(original) != BASE:
        raise ValueError('This assembler requires the exact reviewed FORMA source layout')
    if len(assets) != 3 or [a['id'] for a in assets] != gallery.IDS:
        raise ValueError('Three verified studio assets required')
    binary = {}
    local = []
    for asset in assets:
        path = 'static/' + asset['id'] + '.png'
        prefix = 'data:image/png;base64,'
        if not asset['src'].startswith(prefix):
            raise ValueError('Verified PNG data required')
        binary[path] = base64.b64decode(asset['src'][len(prefix):], validate=True)
        local.append(asset | {'src': path})
    html, frontend = gallery.enhance(original['index.html'],
        {k: v for k, v in original.items() if k.endswith(('.css', '.js'))}, local)
    for name in OVERLAYS:
        html = html.replace('"' + name + '"', '"static/' + name + '"')
    files = {name: text.encode() for name, text in original.items()}
    files['index.html'] = html.encode()
    files.update({'static/' + name: frontend[name].encode() for name in OVERLAYS})
    files.update(binary)
    entrypoint = (HERE / 'studio_bundle_app.py').read_text()
    files['app.py'] = entrypoint.replace('PUBLIC = {}', 'PUBLIC = ' + repr(public_routes(files)), 1).encode()
    files['README.md'] = '''# FORMA — kompletny kandydat demonstracyjny

Zawiera aplikację Python, trzy PNG ComfyUI, galerię, scenę, menu, nawigację,
ochronę fokusu i lokalny kreator briefu. Bez pakietów pip i zewnętrznych zasobów.
Python 3.10+. W wydzielonym środowisku: python app.py, adres
http://127.0.0.1:8080. Testy logiki: python -m unittest discover -s tests -t .
Plik file:// nie uruchamia kalkulatora. HOST domyślnie 127.0.0.1, PORT 8080.
W projekcie AI Company kod tej paczki wykonujemy tylko w ograniczonym kontenerze.

Qwen dostarczył bazowe źródła, design i opisy obrazów; ComfyUI wygenerował PNG.
Integracja, serwer tras statycznych i interakcje są kodem nadzorowanym.
Kalkulator jest demonstracyjny; brief pozostaje w pamięci strony.
Brak wysyłania, kont, płatności, trwałej bazy i wdrożenia. To kandydat,
nie odebrane wydanie klienta. Sam manifest nie oznacza zaliczenia testów.
Wyniki niezależnych kontroli znajdują się w osobnym raporcie związanym SHA-256
z dokładnym ZIP. Manifest zawiera sumy wszystkich plików, nie podpis autora.
'''.encode()
    validate(files)
    return files


def pack(files, provenance):
    validate(files)
    manifest = {'schema': 'studio-bundle.v1', 'accepted': False, 'deployed': False,
                'files': checksums(files), 'provenance': provenance}
    output = io.BytesIO()
    with ZipFile(output, 'w', compression=ZIP_STORED) as archive:
        entries = files | {'bundle.json': json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2).encode()}
        for name, raw in sorted(entries.items()):
            entry = ZipInfo(name, date_time=(2026, 9, 20, 0, 0, 0))
            entry.external_attr = (stat.S_IFREG | 0o444) << 16
            archive.writestr(entry, raw)
    return output.getvalue()


def unpack(raw):
    if len(raw) > MAX_BYTES + 100000:
        raise ValueError('Archive too large')
    with ZipFile(io.BytesIO(raw)) as archive:
        entries = archive.infolist()
        if len(entries) != len(NAMES) + 1 or {i.filename for i in entries} != NAMES | {'bundle.json'}:
            raise ValueError('Unexpected or duplicate archive entries')
        for entry in entries:
            if (entry.compress_type != ZIP_STORED or entry.flag_bits & 1
                    or stat.S_IFMT(entry.external_attr >> 16) != stat.S_IFREG
                    or entry.file_size > (4_000_000 if entry.filename in ASSETS else 262144)):
                raise ValueError('Invalid archive entry')
        files = {name: archive.read(name) for name in NAMES}
        manifest = json.loads(archive.read('bundle.json'), object_pairs_hook=unique_object)
    validate(files)
    if (manifest.get('schema') != 'studio-bundle.v1' or manifest.get('accepted') is not False
            or manifest.get('deployed') is not False or manifest.get('files') != checksums(files)):
        raise ValueError('Bundle identity or checksums changed')
    return files, manifest


def read_bundle(path):
    path = Path(path).resolve()
    if not path.is_relative_to(ROOT) or path.stat().st_size > MAX_BYTES + 100000:
        raise ValueError('Bounded local Linux bundle required')
    raw = path.read_bytes()
    files, manifest = unpack(raw)
    return files, manifest, sha256(raw).hexdigest()


def frame_content(files):
    """Opaque frame cannot fetch PNG paths; inline exactly the archived bytes."""
    validate(files)
    html = files['index.html'].decode()
    for name in sorted(ASSETS):
        html = html.replace('src="' + name + '"', 'src="data:image/png;base64,' + base64.b64encode(files[name]).decode() + '"')
    return html, {name: raw.decode() for name, raw in files.items() if name.endswith(('.css', '.js'))}


class BundleRunError(ValueError):
    def __init__(self, run):
        super().__init__('Bundle container validation failed')
        self.run = run


class BundleRunner(ContainerRunner):
    """Pilot-only binary staging; never registered as a production API profile."""
    def __init__(self, path=None):
        super().__init__(HARNESS)
        self.path = None if path is None else estimate_path(path)

    def stage_sources(self, folder, files):
        validate(files)
        if (any(p.is_symlink() for p in (folder, *folder.parents)) or any(folder.iterdir())
                or folder.stat().st_uid != os.geteuid() or folder.stat().st_mode & 0o077):
            raise ValueError('Fresh private Linux staging required')
        content = files | {'bundle_control.json': json.dumps({
            'checksums': checksums(files), 'public': public_routes(files), 'path': self.path,
            'probes': case.PROBES[1:],
        }).encode(), 'tests/test_independent_acceptance.py': case.ACCEPTANCE.encode(),
            'runner_support.py': (HARNESS.parent / 'multifile_harness.py').read_bytes()}
        for name, raw in sorted(content.items()):
            target = folder / name
            target.parent.mkdir(mode=0o755, exist_ok=True, parents=True)
            with target.open('xb') as stream:
                stream.write(raw)
            target.chmod(0o444)
        folder.chmod(0o755)

    def execute(self, files):
        validate(files)
        check_idle()
        config = configuration() | {'profile': 'studio-bundle-pilot-v1',
            'harness_checksum': sha256(HARNESS.read_bytes()).hexdigest(),
            'support_checksum': sha256((HARNESS.parent / 'multifile_harness.py').read_bytes()).hexdigest()}
        run = self.run(files, config, 'aic-package-' + uuid4().hex)
        try:
            result = checked_report(run, 'studio-bundle-test.v1')
            expected = set(public_routes(files)) | {'private-routes-denied', 'independent-http-cases'}
            if self.path is None and (result.get('tests_ok') is not True or set(result.get('checks', [])) != expected):
                raise ValueError('Incomplete bundle audit')
            return run, result
        except ValueError as exc:
            raise BundleRunError(run) from exc


def run_request(files, path):
    _, result = BundleRunner(path).execute(files)
    return {'response': result['response']}
