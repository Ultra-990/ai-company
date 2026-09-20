"""Opt-in synthetic PNG runner pilot; no application imports or live DB writes."""
import argparse
import base64
from hashlib import sha256
import json
from pathlib import Path
import sys
import tempfile
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.services.media_package_runner import MediaPackageRunner, pilot_configuration
from scripts.studio_bundle import read_bundle, ROOT
from scripts.compare_local_models import check_idle
from scripts.check_qwen_multifile import checked_report
from scripts import upwork_web_case as case


def request_from_bundle(path):
    files, _, digest = read_bundle(path)
    sources = {name: raw.decode() for name, raw in files.items() if not name.endswith('.png')}
    sources['tests/test_independent_acceptance.py'] = case.ACCEPTANCE
    return {'purpose':'Kompletna demonstracja FORMA z niezależnymi testami kalkulatora',
        'files':sources, 'images':{name:base64.b64encode(raw).decode() for name,raw in files.items() if name.endswith('.png')}}, digest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle', type=Path, required=True)
    parser.add_argument('--run', action='store_true')
    args = parser.parse_args(argv)
    payload, digest = request_from_bundle(args.bundle)
    output = Path(tempfile.mkdtemp(prefix='media-package-pilot-', dir=ROOT))
    (output/'package-request.json').write_text(json.dumps(payload, ensure_ascii=False))
    report = {'schema':'media-package-pilot.v1', 'bundle_sha256':digest, 'status':'not_executed',
        'accepted':False,'deployed':False,'runs':[]}
    def save(): (output/'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))
    save(); print(json.dumps({'report':str(output/'report.json'),'import_json':str(output/'package-request.json')}),flush=True)
    if not args.run: return 0
    files = payload['files'] | payload['images']
    try:
        check_idle()
        run = MediaPackageRunner().run(files, pilot_configuration(), 'aic-package-'+uuid4().hex)
        report['runs'].append(run); save()
        result = checked_report(run, 'python-web-media-test.v1')
        if not all(result.get(k) is True for k in ('tests_ok','http_ok','assets_ok','source_not_exposed')):
            raise ValueError('Incomplete test evidence')
        for path,status,total in case.PROBES:
            check_idle()
            run = MediaPackageRunner(path).run(files, pilot_configuration(True)|{'request_path':path}, 'aic-package-'+uuid4().hex)
            report['runs'].append(run); save()
            result = checked_report(run, 'python-web-media-preview.v1')['response']
            if result['status'] != status: raise ValueError('HTTP status mismatch')
            if path == '/':
                if sha256(result['body'].encode()).hexdigest()!=sha256(files['index.html'].encode()).hexdigest():
                    raise ValueError('HTML changed')
            elif status == 200 and json.loads(result['body']).get('total')!=total:
                raise ValueError('Calculation mismatch')
        report['status']='passed'
    except Exception as exc:
        report.update(status='failed',error_type=type(exc).__name__)
        raise
    finally: save()
    print(json.dumps({'status':report['status'],'runs':len(report['runs'])}),flush=True)
    return 0


if __name__=='__main__': raise SystemExit(main())
