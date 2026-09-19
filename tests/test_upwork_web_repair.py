from hashlib import sha256
import json

import pytest

from scripts import repair_upwork_web_pilot as repair, upwork_web_case as case
from scripts.check_multifile_isolation import sources


def original_files():
    files = sources('success')
    files['tests/test_logic.py'] = files.pop('tests/nested/test_logic.py')
    return files | {'app.js':'// original', 'style.css':'body{color:black}'}


@pytest.mark.parametrize('changes', [
    {'tests/test_logic.py':'weaken assertions'}, {'modules/logic.py':'pass'},
    {'README.md':'accepted'}, {'new.js':'new'}, {'../escape':'x'}, {},
])
def test_revision_cannot_weaken_immutable_files(changes):
    with pytest.raises(ValueError):repair.merge_revision(original_files(), json.dumps({'files':changes}))


def test_revision_preserves_every_other_file():
    files = original_files()
    revised = repair.merge_revision(files, json.dumps({'files':{'app.js':'// corrected'}}))
    assert revised['app.js'] == '// corrected'
    assert {k:v for k,v in revised.items() if k != 'app.js'} == {k:v for k,v in files.items() if k != 'app.js'}


def test_revision_respects_narrower_file_scope():
    with pytest.raises(ValueError):
        repair.merge_revision(original_files(), json.dumps({'files':{'style.css':'body{}'}}), {'app.js'})


@pytest.mark.parametrize('content', ['[]','{"files": []}', '{"files":{"app.js":"x","app.js":"y"}}',
                                   '{"files":{"app.js":7}}'])
def test_revision_rejects_invalid_output(content):
    with pytest.raises((TypeError,ValueError)):repair.merge_revision(original_files(), content)


def fixture_report():
    files = original_files()
    return {'schema':'qwen-multifile-pilot.v1','scenario':'studio','brief':case.BRIEF,
            'independent_tests':case.ACCEPTANCE,'accepted':False,'deployed':False,
            'generation':{'content':json.dumps({'files':files})},
            'source_checksums':{k:sha256(v.encode()).hexdigest() for k,v in files.items()}}


@pytest.mark.parametrize('mutation', [dict(repair_attempts=2), dict(repair_attempts=True),
                                    dict(accepted=True), dict(brief='different'), dict(source_checksums={})])
def test_repair_rejects_changed_evidence_or_exhausted_attempts(tmp_path, monkeypatch, mutation):
    monkeypatch.setattr(repair,'ROOT',tmp_path)
    path = tmp_path/'report.json'
    path.write_text(json.dumps(fixture_report() | mutation))
    with pytest.raises(ValueError):repair.load_original(path)


def test_repair_dry_run_never_invokes_model(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(repair,'ROOT',tmp_path)
    monkeypatch.setattr(repair,'check_idle',lambda:pytest.fail('no resources in dry-run'))
    path = tmp_path/'report.json'
    path.write_text(json.dumps(fixture_report()))
    assert repair.main([str(path),'--feedback','Health route missing']) == 0
    assert json.loads(capsys.readouterr().out)['inference'] is False
