from hashlib import sha256
import json
from pathlib import Path

import pytest

from scripts import workshop_catalog_case as case


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def test_public_case_is_explicit_synthetic_development_transfer():
    public = case.public_case()
    rendered = json.dumps(public, ensure_ascii=False)
    assert "PLAN ZAJĘĆ" in rendered
    assert "ROWEROWNIA" not in rendered and "CREMA" not in rendered
    assert "nie jest ślepym holdoutem" in public["status_note"]
    assert "zaakceptowanym przykładem treningowym" in public["status_note"]
    assert all(name in public["goal"] for name in case.FILES)
    assert all(target not in rendered for target, _, _ in case.PROBES if "?" in target)


def test_catalog_is_six_explicit_unique_records_with_exact_schema():
    assert len(case.SESSIONS) == 6
    assert len({row["id"] for row in case.SESSIONS}) == 6
    assert all(set(row) == {"id", "title", "day", "start", "level", "duration_minutes"}
               for row in case.SESSIONS)
    assert {row["day"] for row in case.SESSIONS} == {"monday", "tuesday", "saturday"}
    assert {row["level"] for row in case.SESSIONS} == {"beginner", "intermediate", "advanced"}
    for row in case.SESSIONS:
        assert " | ".join(str(row[key]) for key in
                          ("id", "title", "day", "start", "level", "duration_minutes")) in case.GOAL


def test_frozen_probes_cover_filters_empty_invalid_routing_and_exact_json():
    assert sha256(canonical(case.PROBES).encode()).hexdigest() == case.PROBES_SHA256
    assert len({target for target, _, _ in case.PROBES}) == len(case.PROBES)
    assert {status for _, status, _ in case.PROBES} == {200, 400, 404}
    assert any(status == 200 and sessions == [] for _, status, sessions in case.PROBES)
    assert any(target == "/api/sessions" and status == 400 for target, status, _ in case.PROBES)
    invalid = [target for target, status, _ in case.PROBES if status == 400]
    assert any("extra=" in target for target in invalid)
    assert any(target.count("day=") == 2 for target in invalid)
    assert any(target.count("level=") == 2 for target in invalid)
    assert all(set(row) == {"id", "title", "day", "start", "level", "duration_minutes"}
               for _, status, rows in case.PROBES if status == 200 for row in rows)


def test_success_probes_follow_and_filter_in_catalog_order():
    from urllib.parse import parse_qs, urlsplit

    for target, status, expected in case.PROBES:
        if status != 200:
            continue
        query = parse_qs(urlsplit(target).query, keep_blank_values=True)
        actual = [row for row in case.SESSIONS
                  if (query["day"] == ["all"] or row["day"] == query["day"][0])
                  and (query["level"] == ["all"] or row["level"] == query["level"][0])]
        assert expected == actual


def test_public_contract_names_api_dom_assets_file_mode_and_test_response_shape():
    for required in (
        "dokładnie po jednym parametrze day oraz level", "Parametry brakujące, puste, powtórzone, dodatkowe",
        "{\"sessions\": [...]}", "GET /api/sessions bez query zwraca 400", "main#main",
        "#catalog", "#schedule", "#faq", "#contact", "select#day", "select#level",
        "style.css przez link", "app.js przez script src",
        "#apply-filters", "#sessions", "#filter-status", "aria-live=polite",
        "aria-controls=site-nav", "aria-expanded=false", "Escape", "details#faq-filtering",
        "location.protocol === 'file:'", "(status, headers, body)",
    ):
        assert required in case.GOAL


def test_trusted_harness_is_pinned_compilable_and_contains_bounded_examiner():
    source = case.harness_source()
    compile(source, "workshop-catalog-harness", "exec")
    assert "isolation_checks()" in source and "signal.alarm(35)" in source
    assert "expected exactly six root files" in source
    assert "success body must be JSON" in source
    assert "incorrect sessions body" in source
    assert "JavaScript must not assign innerHTML" in source
    assert "'textContent' not in js_body" not in source
    assert "'location.protocol' not in js_body" not in source
    assert "ast.parse" not in source and "request_helpers" not in source
    assert source.count("/api/sessions") == sum(
        target.startswith("/api/sessions") for target, _, _ in case.PROBES)


def test_current_base_harness_digest_matches_pin():
    path = Path(case.__file__).resolve().parents[1] / "app/runner/harness.py"
    assert sha256(path.read_bytes()).hexdigest() == case.BASE_HARNESS_SHA256


def test_harness_rejects_changed_trusted_base(monkeypatch, tmp_path):
    fake_script = tmp_path / "scripts" / "workshop_catalog_case.py"
    fake_script.parent.mkdir()
    fake_script.write_text("placeholder")
    base = tmp_path / "app" / "runner" / "harness.py"
    base.parent.mkdir(parents=True)
    base.write_text("changed")
    monkeypatch.setattr(case, "__file__", str(fake_script))
    with pytest.raises(ValueError, match="Base harness changed"):
        case.harness_source()


def teacher_fixture(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    html = """<!doctype html><html><head><link href="style.css" rel="stylesheet"></head><body>
    <a href="#catalog">Katalog</a><a href="#schedule">Plan</a><a href="#faq">FAQ</a><a href="#contact">Kontakt</a>
    <button id="menu-toggle" aria-controls="site-nav" aria-expanded="false">Menu</button><nav id="site-nav"></nav>
    <main id="main"><section id="catalog"></section><section id="schedule">
    <label for="day">Dzień</label><select id="day"></select><label for="level">Poziom</label><select id="level"></select>
    <button id="apply-filters">Filtruj</button><div id="sessions"></div>
    <p id="filter-status" aria-live="polite"></p><p id="runtime-note" aria-live="polite"></p>
    </section><section id="faq"><details id="faq-filtering"></details></section><section id="contact"></section></main>
    <script src="app.js"></script><p>Fikcyjna demonstracja</p></body></html>"""
    js = "document.createTextNode('safe implementation');"
    responses = {
        target: (status, json.dumps({"sessions": expected} if status == 200 else {"error": "bad"}))
        for target, status, expected in case.PROBES if status != 404
    }
    responses["/missing"] = (404, "not found")
    responses.update({"/": (200, html), "/style.css": (200, "body{}"), "/app.js": (200, js)})
    for name in case.FILES:
        (workspace / name).write_text("fixture", encoding="utf-8")
    (workspace / "README.md").write_text(
        "python app.py; unittest; file://; ograniczenia", encoding="utf-8")
    (workspace / "runner_harness.py").write_text("trusted", encoding="utf-8")
    namespace = {"__name__": "trusted_teacher_fixture"}
    exec(case.harness_source(), namespace)
    namespace["WORKSPACE"] = workspace
    namespace["_base_fetch"] = lambda path: responses[path]
    return namespace, responses, workspace


def test_acceptance_hook_executes_against_trusted_teacher_http_fixture(tmp_path):
    namespace, responses, _ = teacher_fixture(tmp_path)
    assert namespace["fetch"]("/") == responses["/"]


@pytest.mark.parametrize("failure", ("bad_success_body", "extra_record", "bad_error", "missing_asset"))
def test_acceptance_hook_rejects_false_green_http_and_asset_results(tmp_path, failure):
    namespace, responses, _ = teacher_fixture(tmp_path)
    success_target = next(target for target, status, _ in case.PROBES if status == 200)
    error_target = next(target for target, status, _ in case.PROBES if status == 400)
    if failure == "bad_success_body":
        responses[success_target] = (200, json.dumps({"sessions": "not-a-list"}))
    elif failure == "extra_record":
        expected = json.loads(responses[success_target][1])["sessions"]
        responses[success_target] = (200, json.dumps({"sessions": expected + [{"id": "extra"}]}))
    elif failure == "bad_error":
        responses[error_target] = (400, json.dumps({"message": "bad"}))
    else:
        responses["/app.js"] = (404, "missing")
    with pytest.raises(ValueError, match="Workshop acceptance"):
        namespace["fetch"]("/")


def test_case_building_and_tests_do_not_invoke_models_or_candidate_code(monkeypatch):
    monkeypatch.setattr("subprocess.run", lambda *args, **kwargs: pytest.fail("unexpected subprocess"))
    public = case.public_case()
    source = case.harness_source()
    assert public["title"] == case.TITLE
    assert source and "app.py" in source
