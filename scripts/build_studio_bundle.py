"""Assemble a synthetic standalone FORMA candidate; optional isolated validation."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts import studio_bundle as bundle
from scripts.design_upwork_web_pilot import read_report
from scripts.studio_gallery import load_assets


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report', type=Path)
    parser.add_argument('--media-report', type=Path, required=True)
    parser.add_argument('--run', action='store_true', help='Run exact archive sources in restricted Docker')
    args = parser.parse_args(argv)
    report, source_hash = read_report(args.report)
    assets = load_assets(args.media_report)
    media_hash = sha256(args.media_report.read_bytes()).hexdigest()
    files = bundle.assemble(report, assets)
    raw = bundle.pack(files, {'source_report_sha256': source_hash, 'media_report_sha256': media_hash})
    # The runner and preview consume the round-tripped ZIP, never the input map.
    files, manifest = bundle.unpack(raw)
    if any(p.is_symlink() for p in (bundle.ROOT, *bundle.ROOT.parents)) or bundle.ROOT.stat().st_dev != Path('/home').stat().st_dev:
        raise ValueError('Linux workspace required')
    out = Path(tempfile.mkdtemp(prefix='studio-bundle-', dir=bundle.ROOT))
    (out / 'forma-candidate.zip').write_bytes(raw)
    result = dict(schema='studio-bundle-audit.v1', status='assembled',
        bundle='forma-candidate.zip', bundle_sha256=sha256(raw).hexdigest(),
        source_checksums=manifest['files'], provenance=manifest['provenance'],
        accepted=False, deployed=False, browser_validation='pending')
    def save():
        (out / 'report.json').write_text(json.dumps(result, ensure_ascii=False, indent=2))
    save()
    print(json.dumps({'report': str(out / 'report.json'), 'bundle': str(out / 'forma-candidate.zip')}), flush=True)
    if args.run:
        try:
            run, checks = bundle.BundleRunner().execute(files)
            result.update(status='passed', container_run=run, checks=checks['checks'])
        except Exception as exc:
            result.update(status='failed', error_type=type(exc).__name__)
            if isinstance(exc, bundle.BundleRunError):
                result['container_run'] = exc.run
            raise
        finally:
            save()
    print(json.dumps({'status': result['status'], 'bytes': len(raw), 'files': len(files), 'accepted': False}), flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
