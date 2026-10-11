import json
from pathlib import Path

import pytest

from scripts import check_workshop_catalog_routes as routes


def test_probe_contract_is_bounded_to_control_and_three_semicolon_routes():
    assert routes.PROBES == (
        ("valid-control", "/api/sessions?day=all&level=all", 200),
        ("api-semicolon-suffix", "/api/sessions;extra?day=all&level=all", 404),
        ("health-semicolon-suffix", "/health;extra", 404),
        ("root-semicolon-suffix", "/;extra", 404),
    )
    assert routes.SUPPLEMENTAL_PROBES == (("health-empty-semicolon", "/health;", 404),)
    assert routes.ALLOWED_PATHS == {path for _, path, _ in (*routes.PROBES,*routes.SUPPLEMENTAL_PROBES)}
    with pytest.raises(ValueError, match="allowlist"):
        routes.RouteProbeRunner("/health")


def test_dry_run_validates_source_without_preview(monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["check_workshop_catalog_routes.py"])
    monkeypatch.setattr(routes, "RouteProbeRunner",
                        lambda *args, **kwargs: pytest.fail("preview started in dry run"))
    assert routes.main() == 0
    result = json.loads(capsys.readouterr().out)
    assert result["containers_started"] is False
    assert result["required_flag"] == "--run"
    assert result["selected_source_schema"] == "workshop-catalog-delivery.v1"


def test_checked_report_rejects_path_outside_fixed_pilot(tmp_path):
    report = tmp_path / "report.json"
    report.write_text("{}")
    with pytest.raises(ValueError, match="outside"):
        routes.checked_report(report)


def test_run_records_raw_results_and_checks_idle_before_each_probe(monkeypatch, tmp_path):
    source = tmp_path / "report.json"
    source.write_text("source")
    files = {name: name for name in routes.FILES}
    selected = {"schema": "workshop-catalog-delivery.v1"}
    monkeypatch.setattr(routes, "load_source", lambda path: (source, routes.digest_bytes(b"source"), selected, files))
    monkeypatch.setattr(routes, "new_output", lambda: tmp_path / "output")
    (tmp_path / "output").mkdir()
    idle = []
    monkeypatch.setattr(routes, "check_idle", lambda: idle.append("checked"))
    profile = {"profile": "fixture"}
    monkeypatch.setattr(routes, "route_configuration", lambda: profile)

    class Runner:
        def __init__(self, path):
            self.path = path

        def run(self, sources, actual_profile, name):
            expected = dict((path, status) for _, path, status in routes.PROBES)[self.path]
            return {"exit_code": 0, "cli_exit_code": 0, "cleanup_confirmed": True,
                    "reason": None, "profile": profile,
                    "log": json.dumps({"schema": "python-web-preview.v1",
                                       "response": {"status": expected, "body": "fixture"}})}

    monkeypatch.setattr(routes, "RouteProbeRunner", Runner)
    assert routes.run(source) == 0
    report = json.loads((tmp_path / "output" / "report.json").read_text())
    assert idle == ["checked"] * 4
    assert report["status"] == "passed" and report["source_unchanged"] is True
    assert all(item["raw_run"]["cleanup_confirmed"] is True for item in report["probes"])


def test_invalid_cleanup_cannot_pass(monkeypatch, tmp_path):
    source = tmp_path / "report.json"
    source.write_text("source")
    files = {name: name for name in routes.FILES}
    monkeypatch.setattr(routes, "load_source", lambda path: (
        source, routes.digest_bytes(b"source"), {"schema": "workshop-catalog-delivery.v1"}, files))
    output = tmp_path / "output"
    output.mkdir()
    monkeypatch.setattr(routes, "new_output", lambda: output)
    monkeypatch.setattr(routes, "check_idle", lambda: None)
    monkeypatch.setattr(routes, "route_configuration", lambda: {"profile": "fixture"})

    class Runner:
        def __init__(self, path): pass
        def run(self, *args):
            return {"exit_code": 0, "cli_exit_code": 0, "cleanup_confirmed": False,
                    "reason": None, "profile": {"profile": "fixture"},
                    "log": json.dumps({"schema": "python-web-preview.v1",
                                       "response": {"status": 200, "body": "fixture"}})}

    monkeypatch.setattr(routes, "RouteProbeRunner", Runner)
    assert routes.run(source) == 1
    report = json.loads((output / "report.json").read_text())
    assert report["status"] == "failed" and not any(item["passed"] for item in report["probes"])


def test_preflight_exception_persists_incomplete_without_raw_exception(monkeypatch, tmp_path):
    source = tmp_path / "report.json"
    source.write_text("source")
    files = {name: name for name in routes.FILES}
    monkeypatch.setattr(routes, "load_source", lambda path: (
        source, routes.digest_bytes(b"source"), {"schema": "workshop-catalog-delivery.v1"}, files))
    output = tmp_path / "output"
    output.mkdir()
    monkeypatch.setattr(routes, "new_output", lambda: output)
    monkeypatch.setattr(routes, "route_configuration", lambda: {"profile": "fixture"})
    monkeypatch.setattr(routes, "check_idle", lambda: (_ for _ in ()).throw(RuntimeError("secret detail")))
    assert routes.run(source) == 2
    report = json.loads((output / "report.json").read_text())
    assert report["status"] == "incomplete"
    assert report["error_type"] == "RuntimeError"
    assert report["source_unchanged"] is True
    assert "secret detail" not in json.dumps(report)


def test_route_repair_source_must_bind_pinned_ui_report_and_preserve_five_files(monkeypatch,tmp_path):
    original_files={name:"original "+name for name in routes.FILES}
    ui_files=original_files|{"index.html":"ui index","app.js":"ui script"}
    ui=tmp_path/"ui.json";ui.write_text(json.dumps({"schema":"workshop-catalog-ui-repair.v1",
                                                     "final_sources":ui_files}))
    ui_sha=routes.digest_bytes(ui.read_bytes())
    repair_files=ui_files|{"app.py":"repaired app"}
    report={"schema":"workshop-catalog-route-repair.v1","source_report":str(ui),
            "source_report_sha256":ui_sha,"routes_report_sha256":routes.ROUTES_SHA256,
            "candidate_created":True,"exact_change_scope":True,"owner_accepted":False,
            "deployed":False,"final_sources":repair_files}
    selected=tmp_path/"route.json";selected.write_text(json.dumps(report))
    monkeypatch.setattr(routes,"UI_REPAIR_SHA256",ui_sha)
    monkeypatch.setattr(routes,"checked_report",lambda path:Path(path))
    monkeypatch.setattr(routes,"_original",lambda:(tmp_path/"original.json",{},original_files))
    assert routes.load_source(selected)[3]==repair_files
    report["final_sources"]["app.js"]="hidden second change"
    selected.write_text(json.dumps(report))
    with pytest.raises(ValueError,match="route repair chain"):
        routes.load_source(selected)
