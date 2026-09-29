from pathlib import Path
import json

import pytest

from scripts import product_revised_package as assembly


def setup_sources(tmp_path, monkeypatch, parts=('materials',)):
    monkeypatch.setattr(assembly.revision, 'ROOT', tmp_path)
    package = tmp_path/'original'; package.mkdir()
    monkeypatch.setattr(assembly.product, 'verify', lambda path: {'verified': True})
    pairs, reports, folders = [], {}, {}
    for i, part in enumerate(parts):
        folder = tmp_path/f'revision-{i}'; folder.mkdir()
        report_path, judgment = folder/'report.json', folder/'judgment.json'
        report_path.write_text('{}'); judgment.write_text('{}'); (folder/'artwork.svg').write_text(f'model-{i}')
        pairs.append((report_path, judgment))
        reports[report_path] = {'part': part, 'package': str(package)}
        folders[report_path] = folder
    monkeypatch.setattr(assembly.revision, 'authenticate', lambda path: (reports[path], folders[path], {}, {}))
    monkeypatch.setattr(assembly.revision, 'collect', lambda *args: ([], {}))
    return package, pairs, reports, folders


def test_assembly_selects_literal_authenticated_files_and_binds_separate_judgment(tmp_path, monkeypatch):
    package, pairs, _, folders = setup_sources(tmp_path, monkeypatch)
    sources, bindings = assembly.selected_sources(package, pairs)
    assert sources['materials'] == folders[pairs[0][0]]/'artwork.svg'
    assert sources['capacity'] == package/'capacity/artwork.svg'
    assert sources['source'] == package/'source/artwork.svg'
    assert set(bindings[0]) == {'part', 'report', 'report_sha256', 'judgment', 'judgment_sha256', 'svg_sha256'}


@pytest.mark.parametrize('parts', [('cap',), ('care', 'care')])
def test_assembly_rejects_source_replacement_and_duplicate_panels(tmp_path, monkeypatch, parts):
    package, pairs, _, _ = setup_sources(tmp_path, monkeypatch, parts)
    with pytest.raises(ValueError, match='Unique panel'): assembly.selected_sources(package, pairs)


def test_assembly_rejects_valid_revision_for_different_original(tmp_path, monkeypatch):
    package, pairs, reports, _ = setup_sources(tmp_path, monkeypatch)
    reports[pairs[0][0]]['package'] = str(tmp_path/'different')
    with pytest.raises(ValueError, match='exact original'): assembly.selected_sources(package, pairs)


def test_assembly_does_not_bypass_independent_approval(tmp_path, monkeypatch):
    package, pairs, _, _ = setup_sources(tmp_path, monkeypatch)
    def reject(*args): raise ValueError('Independent positive review required')
    monkeypatch.setattr(assembly.revision, 'collect', reject)
    with pytest.raises(ValueError, match='Independent'): assembly.selected_sources(package, pairs)


def test_assembly_refuses_empty_selection(tmp_path, monkeypatch):
    package, _, _, _ = setup_sources(tmp_path, monkeypatch)
    with pytest.raises(ValueError, match='One to four'): assembly.selected_sources(package, [])


@pytest.mark.parametrize('approved', [True, False])
def test_headline_assembly_requires_its_separate_authorship_and_independent_approval(tmp_path, monkeypatch, approved):
    from scripts import product_headline_repair as headline
    package, pairs, reports, folders = setup_sources(tmp_path, monkeypatch, ('capacity',))
    report_path, judgment_path = pairs[0]
    report_path.write_text(json.dumps({'schema': headline.CONTRACT}))
    def checked(report, judgment):
        assert (report, judgment) == (report_path, judgment_path)
        if not approved: raise ValueError('Independent positive headline review required')
        return reports[report], folders[report]
    monkeypatch.setattr(headline, 'approved_source', checked)
    monkeypatch.setattr(assembly.revision, 'authenticate', lambda *args: pytest.fail('Must use literal headline verifier'))
    if approved:
        sources, _ = assembly.selected_sources(package, pairs)
        assert sources['capacity'] == folders[report_path]/'artwork.svg'
    else:
        with pytest.raises(ValueError, match='Independent'): assembly.selected_sources(package, pairs)
