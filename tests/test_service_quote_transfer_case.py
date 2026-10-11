from hashlib import sha256
import json
from pathlib import Path

import pytest

from scripts import service_quote_transfer_case as case


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def test_public_case_is_new_bounded_six_file_transfer_without_private_inputs():
    public = case.public_case()
    rendered = json.dumps(public, ensure_ascii=False)
    assert "SERWIS CREMA" in rendered and "ROWEROWNIA" not in rendered
    assert "jedną stałą opłatę 70 PLN" in public["goal"]
    assert all(name in public["goal"] for name in case.FILES)
    assert "nie jest to ślepy holdout" in public["status_note"]
    assert "Brak zaakceptowanego przykładu treningowego" in public["status_note"]
    assert all(target not in rendered for target, _, _ in case.PROBES)


def test_probes_are_frozen_fresh_and_cover_parser_body_status_boundaries():
    assert len(case.PROBES) == 19
    assert len({target for target, _, _ in case.PROBES}) == len(case.PROBES)
    assert sha256(canonical(case.PROBES).encode()).hexdigest() == case.PROBES_SHA256
    statuses = {status for _, status, _ in case.PROBES}
    assert statuses == {200, 400, 404}
    successful = [(target, body) for target, status, body in case.PROBES if status == 200]
    assert successful and all(set(body) == {"total", "currency"} and body["currency"] == "PLN"
                              for _, body in successful)
    invalid = [target for target, status, _ in case.PROBES if status == 400]
    assert any("&plan=" in target for target in invalid)
    assert any("&machines=" in target.split("machines=", 1)[-1] for target in invalid)
    assert any("coupon=" in target for target in invalid)
    assert any("machines=0" in target for target in invalid)
    assert any("machines=7" in target for target in invalid)


def test_valid_probe_totals_follow_new_one_time_onsite_rule():
    from urllib.parse import parse_qs, urlsplit

    prices = {"check": 85, "restore": 235}
    for target, status, expected in case.PROBES:
        if status != 200:
            continue
        query = parse_qs(urlsplit(target).query, keep_blank_values=True)
        total = prices[query["plan"][0]] * int(query["machines"][0])
        total += 70 if query["onsite"][0] == "1" else 0
        assert expected == {"total": total, "currency": "PLN"}


def test_trusted_harness_is_pinned_compilable_and_contains_independent_contract():
    source = case.harness_source()
    compile(source, "service-quote-transfer-harness", "exec")
    assert "isolation_checks()" in source and "signal.alarm(35)" in source
    assert "expected exactly six root files" in source
    assert "success body must be JSON" in source
    assert "HTTP 400 requires nonempty error field" in source
    assert "calculator/file-mode implementation missing" in source
    assert source.count("/api/quote?") == sum(
        target.startswith("/api/quote?") for target, _, _ in case.PROBES)
    assert "('/missing-page', 404, None)" in source


def test_harness_rejects_changed_trusted_base(monkeypatch, tmp_path):
    fake_script = tmp_path / "scripts" / "service_quote_transfer_case.py"
    fake_script.parent.mkdir()
    fake_script.write_text("placeholder")
    base = tmp_path / "app" / "runner" / "harness.py"
    base.parent.mkdir(parents=True)
    base.write_text("changed")
    monkeypatch.setattr(case, "__file__", str(fake_script))
    with pytest.raises(ValueError, match="Base harness changed"):
        case.harness_source()


def test_current_base_harness_digest_matches_pin():
    path = Path(case.__file__).resolve().parents[1] / "app/runner/harness.py"
    assert sha256(path.read_bytes()).hexdigest() == case.BASE_HARNESS_SHA256


def test_public_contract_has_accessibility_menu_faq_filemode_and_readme_scope():
    goal = case.GOAL
    for required in ("aria-live=polite", "aria-controls=site-nav", "aria-expanded=false",
                     "Escape", "details#faq-process", "location.protocol === 'file:'",
                     "wyłączyć #calculate", "README", "ograniczenia"):
        assert required in goal


def test_acceptance_hook_executes_against_trusted_teacher_http_fixture(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    html = """<!doctype html><html><head><link href="style.css" rel="stylesheet"></head><body>
    <a href="#services">Usługi</a><a href="#quote">Wycena</a><a href="#faq">FAQ</a><a href="#contact">Kontakt</a>
    <button id="menu-toggle" aria-controls="site-nav" aria-expanded="false">Menu</button><nav id="site-nav"></nav>
    <main id="main"><section id="services"></section><section id="quote">
    <label for="plan">Plan</label><select id="plan"></select>
    <label for="machines">Liczba</label><input id="machines">
    <label for="onsite">Dojazd</label><input id="onsite"><button id="calculate">Licz</button>
    <p id="result" aria-live="polite"></p><p id="runtime-note" aria-live="polite">Uruchom python app.py</p>
    </section><section id="faq"><details id="faq-process"></details></section><section id="contact"></section></main>
    <script src="app.js"></script><p>Fikcyjna demonstracja</p></body></html>"""
    js = "location.protocol === 'file:'; calculate.disabled = true; result.textContent = 'x';" + " " * 200
    responses = {target: (status, json.dumps(expected if expected is not None else {"error": "bad"}))
                 for target, status, expected in case.PROBES}
    responses.update({"/": (200, html), "/style.css": (200, "body{}" + " " * 160),
                      "/app.js": (200, js)})
    for name in case.FILES:
        (workspace / name).write_text("fixture", encoding="utf-8")
    (workspace / "README.md").write_text(
        "python app.py; unittest; file://; ograniczenia", encoding="utf-8")
    (workspace / "runner_harness.py").write_text("trusted", encoding="utf-8")
    namespace = {"__name__": "trusted_teacher_fixture"}
    exec(case.harness_source(), namespace)
    namespace["WORKSPACE"] = workspace
    namespace["_base_fetch"] = lambda path: responses[path]
    assert {path.name for path in workspace.iterdir() if path.is_file()} == set(case.FILES) | {"runner_harness.py"}
    assert namespace["_required_files"] == set(case.FILES)
    assert namespace["fetch"]("/") == responses["/"]


def test_existing_delivery_selects_transfer_without_changing_business_default(monkeypatch):
    from tests import test_business_website_delivery as delivery
    from app.api.work_orders import Intake
    from uuid import uuid4

    monkeypatch.delenv("AIC_SERVICE_QUOTE_TRANSFER_PILOT", raising=False)
    monkeypatch.delenv("AIC_BUSINESS_WEBSITE_PILOT", raising=False)
    assert delivery.selected_delivery_case()["module"].TITLE == "Syntetyczny pilot — ROWEROWNIA"
    monkeypatch.setenv("AIC_SERVICE_QUOTE_TRANSFER_PILOT", "1")
    selected = delivery.selected_delivery_case()
    assert selected["module"] is case
    assert selected["schema"] == "service-quote-transfer-delivery.v1"
    public = selected["module"].public_case()
    payload = delivery.intake_case(public)
    assert set(payload) == {"title", "goal", "audience", "constraints", "acceptance_criteria"}
    assert "status_note" in public and "status_note" not in payload
    parsed = Intake(request_id=uuid4(), organization_unit_id=1, **payload)
    assert parsed.title == case.TITLE


def test_transfer_wrapper_dry_run_never_invokes_subprocess(monkeypatch, capsys):
    from scripts import check_service_quote_transfer as wrapper

    monkeypatch.setattr("sys.argv", ["check_service_quote_transfer.py"])
    monkeypatch.setattr(wrapper.subprocess, "run",
                        lambda *args, **kwargs: pytest.fail("unexpected model/Docker subprocess"))
    assert wrapper.main() == 0
    result = json.loads(capsys.readouterr().out)
    assert result == {"model_invoked": False, "docker_invoked": False,
                      "scenario": "service-quote-transfer", "required_flag": "--run"}
