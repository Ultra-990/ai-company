from hashlib import sha256
import json

import pytest

from scripts import repair_workshop_catalog_routes as repair


def sources(app="original app", ui=False):
    return {
        "app.py": app, "test_app.py": "tests", "index.html": "ui index" if ui else "index",
        "style.css": "style", "app.js": "ui script" if ui else "script", "README.md": "readme",
    }


def route_evidence():
    rows = (
        ("/api/sessions?day=all&level=all", 200, 200, True),
        ("/api/sessions;extra?day=all&level=all", 404, 200, False),
        ("/health;extra", 404, 200, False),
        ("/;extra", 404, 200, False),
    )
    probes=[]
    for path,expected,observed,passed in rows:
        raw={"exit_code":0,"cli_exit_code":0,"cleanup_confirmed":True,"reason":None,
             "log":json.dumps({"schema":"python-web-preview.v1",
                                "response":{"status":observed,"body":"fixture"}})}
        probes.append({"path":path,"expected_status":expected,"observed_status":observed,
                       "passed":passed,"raw_run":raw})
    return {"schema":"workshop-catalog-routes-check.v1","status":"failed",
            "source_report_sha256":repair.ORIGINAL_SHA256,"source_unchanged":True,
            "source_sha256":{"app.py":repair.ORIGINAL_APP_SHA256},"probes":probes}


def test_feedback_is_app_only_and_names_exact_route_behavior():
    assert repair.CHANGED_FILES == {"app.py"}
    for value in ("/api/sessions;extra", "/health;extra", "/;extra", "404"):
        assert value in repair.DESCRIPTION
    assert "app.py" in repair.EXPECTED and "5 plików" in repair.EXPECTED


def test_feedback_is_compact_but_lossless_for_conservative_context_gate():
    combined=(repair.DESCRIPTION+repair.EXPECTED).encode()
    assert len(combined)<=360
    required=("tylko app.py","/api/sessions;extra?day=all&level=all","/health;extra","/;extra",
              "404","/style.css","/app.js","parser day/level","katalog","json","all/all",
              "200","6 rekordów","5 plików","harness")
    text=(repair.DESCRIPTION+" "+repair.EXPECTED).lower()
    assert all(value in text for value in required)


def test_repair_scope_requires_only_app_change():
    base=sources();good=base|{"app.py":"fixed app"}
    assert repair.repair_scope(base,good)
    assert not repair.repair_scope(base,base)
    assert not repair.repair_scope(base,good|{"app.js":"changed too"})
    assert not repair.repair_scope(base,{k:v for k,v in good.items() if k!="README.md"})


def test_route_evidence_validates_all_raw_runs_and_rejects_tampering(monkeypatch,tmp_path):
    path=tmp_path/"report.json";data=route_evidence()
    path.write_text(json.dumps(data))
    digest=sha256(path.read_bytes()).hexdigest()
    monkeypatch.setattr(repair,"ROUTES",path);monkeypatch.setattr(repair,"ROUTES_SHA256",digest)
    monkeypatch.setattr(repair,"checked",lambda value:value)
    assert repair.evidence_state()==(path,digest)
    data["probes"][1]["raw_run"]["cleanup_confirmed"]=False
    path.write_text(json.dumps(data));monkeypatch.setattr(repair,"ROUTES_SHA256",sha256(path.read_bytes()).hexdigest())
    with pytest.raises(ValueError,match="invalid probe run"):
        repair.evidence_state()


def test_ui_source_validation_binds_original_app_package_and_exact_ui_scope(monkeypatch,tmp_path):
    original=sources();ui=sources(ui=True);database=tmp_path/"test.db";database.write_text("db")
    harness=tmp_path/"harness.py";harness.write_text("harness")
    report={"schema":"workshop-catalog-ui-repair.v1","source_report_sha256":repair.ORIGINAL_SHA256,
        "source_package_id":2,"source_package_checksum":"8b560f0eacc42150f0635da4638fe96b140a2cc5d1dca39b14583fb48d276938",
        "candidate_created":True,"exact_change_scope":True,"owner_accepted":False,"deployed":False,
        "revision":{"new_package_id":repair.PACKAGE_ID,"new_package_checksum":repair.PACKAGE_CHECKSUM,
                    "test_state":"passed","accepted":False},
        "final_sources":ui,"isolated_database":str(database)}
    path=tmp_path/"ui.json";path.write_text(json.dumps(report));digest=sha256(path.read_bytes()).hexdigest()
    monkeypatch.setattr(repair,"SOURCE_SHA256",digest);monkeypatch.setattr(repair,"HARNESS",harness)
    monkeypatch.setattr(repair,"HARNESS_SHA256",sha256(harness.read_bytes()).hexdigest())
    monkeypatch.setattr(repair,"original_state",lambda:( {},original))
    monkeypatch.setattr(repair,"checked",lambda value:value)
    assert repair.source_state(path)[2]==ui
    report["final_sources"]["app.py"]="quietly changed"
    path.write_text(json.dumps(report));monkeypatch.setattr(repair,"SOURCE_SHA256",sha256(path.read_bytes()).hexdigest())
    with pytest.raises(ValueError,match="pinned successful UI repair chain"):
        repair.source_state(path)


def test_dry_run_does_not_invoke_model_or_container(monkeypatch,capsys):
    monkeypatch.setattr("sys.argv",["repair_workshop_catalog_routes.py"])
    monkeypatch.setattr(repair,"check_idle",lambda:pytest.fail("unexpected resource/model call"))
    assert repair.main()==0
    result=json.loads(capsys.readouterr().out)
    assert result["model_invoked"] is False
    assert result["output_profile"]==repair.REPAIR_PROFILE
    assert result["requested_change"]==["app.py"]


def test_browser_registry_accepts_route_repair_without_changing_expectations():
    from scripts import check_business_website_browser as browser
    assert browser.SCENARIOS["workshop-catalog-route-repair.v1"] is browser.SCENARIOS["workshop-catalog-delivery.v1"]
