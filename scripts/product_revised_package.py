"""Assemble independently reviewed local revisions without editing any artwork.

Targeted approval permits assembly only. The complete new package still needs
its own independent visual review; nothing is published or promoted here.
"""
import asyncio
import json
from pathlib import Path
import shutil
import tempfile
import zipfile

from PIL import Image

from scripts import product_infographic_school as product
from scripts import product_visual_revision as revision

SCHEMA = 'product-reviewed-assembly.v1'


def selected_sources(package, pairs):
    package = Path(package)
    product.verify(package)
    if not 1 <= len(pairs) <= 4:
        raise ValueError('One to four independently approved panel revisions required')
    sources = {name: package/name/'artwork.svg' for name in ('source', *product.PANELS)}
    bindings = []
    seen = set()
    for report_path, judgment_path in pairs:
        report_path, judgment_path = Path(report_path), Path(judgment_path)
        if revision.read(report_path).get('schema') == 'product-headline-literal-repair.v1':
            from scripts import product_headline_repair as headline
            report, folder = headline.approved_source(report_path, judgment_path)
        else:
            report, folder, _, _ = revision.authenticate(report_path)
            # collect verifies the separately bound positive judgment, without
            # exporting any training data or calling the model.
            revision.collect(report_path, judgment_path)
        part = report['part']
        if part not in product.PANELS or part in seen:
            raise ValueError('Unique panel revisions required; source replacements need a separate generation')
        if Path(report['package']).resolve() != package.resolve():
            raise ValueError('Every revision must belong to this exact original package')
        seen.add(part)
        sources[part] = folder/'artwork.svg'
        bindings.append({'part': part, 'report': str(report_path), 'report_sha256': product.school.checksum(report_path),
                         'judgment': str(judgment_path), 'judgment_sha256': product.school.checksum(judgment_path),
                         'svg_sha256': product.school.checksum(sources[part])})
    return sources, bindings


def verify(out):
    out = Path(out)
    report = revision.read(out/'report.json')
    if report.get('schema') != SCHEMA or report.get('status') != 'pending_independent_review':
        raise ValueError('Completed reviewed assembly required')
    package = Path(report['original_package'])
    if product.school.checksum(revision.bounded(package/'report.json')) != report['original_report_sha256']:
        raise ValueError('Original package changed')
    original = revision.read(package/'report.json')
    if original['brief'] != product.BRIEF:
        from scripts.product_full_exam import matching_case, exercise_context
        case = matching_case(original)
        if case is None: raise ValueError('Known synthetic assembly brief required')
        with exercise_context(case): return verify(out)
    pairs = [(item['report'], item['judgment']) for item in report['revisions']]
    sources, bindings = selected_sources(package, pairs)
    if bindings != report['revisions']:
        raise ValueError('Revision evidence changed')
    for name, digest in report['artifacts'].items():
        path = out/name
        if not path.resolve().is_relative_to(out.resolve()) or product.school.checksum(revision.bounded(path)) != digest:
            raise ValueError('Assembly artifact changed')
    original = revision.read(package/'report.json')
    if ((report['model'], report['digest']) != (original['model'], original['digest'])
            or report['annotation_contract'] not in ('functional-callouts.v2', 'functional-callouts.v3', 'functional-callouts.v4', 'functional-callouts.v5')):
        raise ValueError('Assembly model and annotation contract must remain bound')
    placement = original.get('placement_contract', product.LEGACY_PLACEMENT)
    style = product.style_value(product.accepted_raw(package, 'style'))
    checks = {}
    for part, source in sources.items():
        folder = out/part
        svg = revision.bounded(source).read_text()
        if revision.bounded(folder/'artwork.svg').read_text() != svg:
            raise ValueError('Assembled artwork differs from authenticated local answer')
        profile = 'product_source' if part == 'source' else product.panel_profile(placement)
        measured = revision.read(folder/'render.json')
        issues = product.quality_issues(measured, panel=part != 'source', panel_contrast=part != 'source',
                                       placement_contract=placement, line_check=part != 'source')
        if part == 'source':
            issues += product.source_fidelity_issues(measured, label_check=True, label_bounds=True, style=style)
        else:
            issues += product.callouts.issues(measured, part, style, contract=report['annotation_contract'])
            small = revision.read(folder/'small/render.json')
            issues += product.quality_issues(small, panel=True, panel_contrast=True, placement_contract=placement, line_check=True)
            issues += product.callouts.issues(small, part, style, contract=report['annotation_contract'])
            with Image.open(folder/'small/preview.png') as image:
                if image.size != (600, 600): raise ValueError('600px preview required')
            for local, target in (('artwork.svg', '.svg'), ('preview.png', '.png'), ('preview.pdf', '.pdf'), ('small/preview.png', '-small.png')):
                if (folder/local).read_bytes() != (out/'delivery'/(part+target)).read_bytes():
                    raise ValueError('Delivery copy differs')
        if issues: raise ValueError('Unresolved assembly defects: '+json.dumps(issues))
        product.pdf_checks(folder/'preview.pdf', product.validate_svg(svg, profile=profile)['texts'], size_mm=product.PROFILES[profile]['size_mm'])
        checks[part] = {'source_svg_sha256': product.school.checksum(source), 'literal_copy': True, 'measured_pass': True}
    manifest = revision.read(out/'delivery/manifest.json')
    for name in ('style.json', 'supplier-brief.json'):
        if (out/'delivery'/name).read_bytes() != (package/'delivery'/name).read_bytes():
            raise ValueError('Supplier brief or shared style changed')
    names = {p.name for p in (out/'delivery').iterdir() if p.is_file()}
    if set(manifest['files']) != names-{'manifest.json'}:
        raise ValueError('Exact delivery manifest required')
    for name, digest in manifest['files'].items():
        if product.school.checksum(out/'delivery'/name) != digest: raise ValueError('Delivery manifest changed')
    with zipfile.ZipFile(out/'infographics.zip') as archive:
        if len(archive.namelist()) != len(names) or set(archive.namelist()) != names: raise ValueError('Exact ZIP entries required')
        for name in names:
            if archive.read(name) != (out/'delivery'/name).read_bytes(): raise ValueError('ZIP copy changed')
    return {'schema': 'product-reviewed-assembly-verification.v1', 'report_sha256': product.school.checksum(out/'report.json'),
            'verified': True, 'checks': checks, 'model_called': False, 'commercial_approved': False,
            'full_visual_acceptance': False, 'training_exported': False}


def run(package, pairs):
    package = Path(package)
    original = revision.read(package/'report.json')
    if original['brief'] != product.BRIEF:
        from scripts.product_full_exam import matching_case, exercise_context
        case = matching_case(original)
        if case is None: raise ValueError('Known synthetic assembly brief required')
        with exercise_context(case): return run(package, pairs)
    sources, bindings = selected_sources(package, pairs)
    product.school.check_idle()
    original = revision.read(package/'report.json')
    placement = original.get('placement_contract', product.LEGACY_PLACEMENT)
    out = Path(tempfile.mkdtemp(prefix='reviewed-package-', dir=product.ROOT))
    report = {'schema': SCHEMA, 'status': 'running', 'original_package': str(package),
              'original_report_sha256': product.school.checksum(package/'report.json'), 'revisions': bindings,
              'annotation_contract': product.callouts.CONTRACT, 'placement_contract': placement,
              'model': original['model'], 'digest': original['digest'],
              'model_called': False, 'training_started': False, 'production_changed': False,
              'commercial_approved': False, 'full_visual_acceptance': False}
    product.school.save(out/'report.json', report)
    print(json.dumps({'output': str(out)}), flush=True)
    implementation = out/'implementation'; implementation.mkdir()
    for name in ('product_revised_package.py', 'product_infographic_school.py', 'product_visual_revision.py',
                 'product_callouts.py', 'render_school_svg.py', 'vector_school_contract.py',
                 'product_headline_repair.py', 'product_headline_probe.py', 'product_correction_evidence.py'):
        shutil.copyfile(Path(__file__).parent/name, implementation/name)
    try:
        delivery = out/'delivery'; delivery.mkdir()
        for part, source in sources.items():
            folder = out/part; folder.mkdir()
            shutil.copyfile(source, folder/'artwork.svg')
            svg = source.read_text()
            profile = 'product_source' if part == 'source' else product.panel_profile(placement)
            product.school.check_idle()
            product.school.save(folder/'render.json', asyncio.run(product.render(svg, folder, profile=profile)))
            if part == 'source': continue
            small = folder/'small'; small.mkdir(); product.school.check_idle()
            product.school.save(small/'render.json', asyncio.run(product.render(svg, small, profile=profile, png_scale=.4)))
            for local, target in (('artwork.svg', '.svg'), ('preview.png', '.png'), ('preview.pdf', '.pdf'), ('small/preview.png', '-small.png')):
                shutil.copyfile(folder/local, delivery/(part+target))
        for name in ('style.json', 'supplier-brief.json'):
            shutil.copyfile(package/'delivery'/name, delivery/name)
        product.school.save(delivery/'manifest.json', {'schema': SCHEMA, 'files': {p.name: product.school.checksum(p) for p in delivery.iterdir()},
            'synthetic': True, 'actual_product_photo': False, 'commercial_approved': False,
            'authorship': 'Literal copies of authenticated local model artwork, with separately reviewed panel replacements.'})
        with zipfile.ZipFile(out/'infographics.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(delivery.iterdir()): archive.write(path, path.name)
        report['status'] = 'pending_independent_review'
    except Exception as exc:
        report.update(status='failed', error_type=type(exc).__name__, error=str(exc)[:1000])
    report['artifacts'] = {str(p.relative_to(out)): product.school.checksum(p) for p in out.rglob('*') if p.is_file() and p.name != 'report.json'}
    product.school.save(out/'report.json', report)
    if report['status'] == 'pending_independent_review':
        try: product.school.save(out/'verification.json', verify(out))
        except Exception as exc:
            report.update(status='failed', error_type=type(exc).__name__, error=str(exc)[:1000])
            product.school.save(out/'report.json', report)
    print(json.dumps({'report': str(out/'report.json'), 'status': report['status']}), flush=True)
    return out, report
