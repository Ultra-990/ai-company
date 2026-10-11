"""Fresh model-authored ROWEROWNIA site, independent tests, repair and ZIP."""
from hashlib import sha256
import json
import os
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.main import app
from app.api.local_inference import get_provider_factory
from app.api.package_runner import get_runner
from app.models.delegation import TaskDelegation
from app.models.local_inference import LocalInference
from app.models.organization_os import Agent
from app.models.package_run import PackageRun
from app.models.task import Task
from app.services import application_quality, container_runner, local_inference, package_runner
from app.services.agent_teams import team_key
from app.services.local_ollama import OllamaProvider, configuration, ensure_idle
from app.services.workspace_packages import read_package
from scripts import business_website_case, service_quote_transfer_case, workshop_catalog_case
from scripts.compare_local_models import check_idle
from tests.conftest import OWNER_HEADERS
from tests.test_agent_packets import packet
from tests.test_agent_teams import delegate, setup


def selected_delivery_case():
    transfer = os.environ.get("AIC_SERVICE_QUOTE_TRANSFER_PILOT") == "1"
    business = os.environ.get("AIC_BUSINESS_WEBSITE_PILOT") == "1"
    workshop = os.environ.get("AIC_WORKSHOP_CATALOG_PILOT") == "1"
    if sum((transfer,business,workshop)) > 1:
        raise ValueError("Select exactly one website delivery case")
    if workshop:
        return {"module": workshop_catalog_case,
                "output_env": "AIC_WORKSHOP_CATALOG_OUTPUT",
                "schema": "workshop-catalog-delivery.v1",
                "task_title": "Implementacja strony PLAN ZAJĘĆ",
                "archive": "workshop-catalog-candidate.zip"}
    if transfer:
        return {"module": service_quote_transfer_case,
                "output_env": "AIC_SERVICE_QUOTE_TRANSFER_OUTPUT",
                "schema": "service-quote-transfer-delivery.v1",
                "task_title": "Implementacja strony SERWIS CREMA",
                "archive": "service-quote-transfer-candidate.zip"}
    return {"module": business_website_case,
            "output_env": "AIC_BUSINESS_WEBSITE_OUTPUT",
            "schema": "business-website-delivery.v1",
            "task_title": "Implementacja strony ROWEROWNIA",
            "archive": "business-website-candidate.zip"}


def intake_case(public):
    """Keep report-only case metadata outside the extra-forbid work-order API."""
    fields = ("title", "goal", "audience", "constraints", "acceptance_criteria")
    return {field: public[field] for field in fields}


def test_business_harness_is_frozen_separate_and_syntax_valid():
    source = business_website_case.harness_source()
    compile(source, "business-website-harness", "exec")
    assert len(business_website_case.PROBES) == 16
    assert "Independent acceptance" in source
    assert "isolation_checks()" in source and "signal.alarm(35)" in source
    prompt = json.dumps(business_website_case.public_case(), ensure_ascii=False)
    assert "/api/estimate?service=full&bikes=2&express=1" not in prompt


@pytest.mark.skipif(os.environ.get("AIC_BUSINESS_WEBSITE_PILOT") != "1"
                    and os.environ.get("AIC_SERVICE_QUOTE_TRANSFER_PILOT") != "1"
                    and os.environ.get("AIC_WORKSHOP_CATALOG_PILOT") != "1",
                    reason="Explicit local model and Docker pilot only")
def test_fresh_business_website_delivery(client, task_repository, monkeypatch, tmp_path):
    resources = check_idle()
    selected = selected_delivery_case()
    scenario = selected["module"]
    class CheckedProvider(OllamaProvider):
        def complete(self, messages):
            check_idle()
            return super().complete(messages)
    class CheckedRunner(container_runner.ContainerRunner):
        def run(self, *args, **kwargs):
            check_idle()
            return super().run(*args, **kwargs)
    destination = Path(os.environ[selected["output_env"]]).resolve()
    assert destination.is_relative_to(Path("/home/marcin/ai-company-workspaces"))
    tester = destination / "independent-harness.py"
    tester.write_text(scenario.harness_source(), encoding="utf-8")
    harness_checksum = sha256(tester.read_bytes()).hexdigest()

    def test_config():
        return container_runner.configuration() | {"harness_checksum": harness_checksum}

    filewise = os.environ.get('AIC_BUSINESS_WEBSITE_FILEWISE') == '1'
    if filewise:
        from scripts.filewise_application_provider import FilewiseApplicationProvider
        def model_factory(config):
            return FilewiseApplicationProvider(config, destination/'filewise'/uuid4().hex, idle_check=check_idle)
    else:
        model_factory = CheckedProvider
    monkeypatch.setattr(package_runner, "configuration", test_config)
    monkeypatch.setattr(local_inference, "enabled_config", configuration)
    monkeypatch.setattr(application_quality, "LOCK_ROOT", tmp_path / "quality-locks")
    app.dependency_overrides[get_provider_factory] = lambda: model_factory
    app.dependency_overrides[get_runner] = lambda: CheckedRunner(harness=tester)

    report = {"schema": selected["schema"], "case": scenario.public_case(),
              "scope": "Synthetic isolated DB; no production work modified.",
              "isolated_database": str((tmp_path / "test.db").resolve()),
              "harness_checksum": harness_checksum, "independent_probes": scenario.PROBES,
              "candidate_created": False, "owner_accepted": False, "deployed": False,
              "resources_before": resources, "filewise_generation": filewise}
    try:
        setup(client)
        units = client.get("/api/work-orders/options", headers=OWNER_HEADERS).json()["units"]
        target = next(unit for unit in units if unit["key"] == "web-platforms.business")
        case = scenario.public_case()
        intake = intake_case(case)
        saved_response = client.post("/api/work-orders", headers=OWNER_HEADERS, json={
            "request_id": str(uuid4()), **intake, "organization_unit_id": target["id"]})
        assert saved_response.status_code == 201, saved_response.text
        saved = saved_response.json()
        report["project_id"] = saved["project_id"]
        assert delegate(client, saved).status_code == 200
        task_id = saved["tasks"][0]["id"]
        report["task_id"] = task_id
        with task_repository._session_factory() as session:
            task = session.get(Task, task_id)
            assignment = session.get(TaskDelegation, task_id)
            builder = session.scalar(select(Agent).where(
                Agent.agent_key == team_key(assignment.department_id, "builder")))
            task.title = selected["task_title"]
            task.description = intake["goal"]
            task.assigned_agent = builder.agent_key
            assignment.worker_id = builder.id
            assignment.execution_brief = intake["goal"]
            assignment.completion_criterion = "Pełne źródła modelu, testy i niezależny odbiór techniczny."
            session.commit()
        prepared = packet(client, task_id)
        queued_response = client.post("/api/local-inference", headers=OWNER_HEADERS, json={
            "request_id": str(uuid4()), "task_id": task_id, "packet_id": prepared["packet_id"],
            "packet_checksum": prepared["checksum"], "output_profile": "python-web-v1"})
        assert queued_response.status_code == 200, queued_response.text
        queued = queued_response.json()
        report["initial_inference_id"] = queued["id"]
        generated_response = client.post(f"/api/local-inference/{queued['id']}/run", headers=OWNER_HEADERS)
        report["generation_http_status"] = generated_response.status_code
        if generated_response.status_code == 200:
            report["generation"] = generated_response.json()
        else:
            report["generation_error"] = generated_response.text[:2000]
        assert generated_response.status_code == 200, generated_response.text
        assert report["generation"]["state"] == "awaiting_review", report["generation"].get("error_code")
        metrics = report["generation"]["metrics"]
        created_response = client.post("/api/application-quality", headers=OWNER_HEADERS, json={
            "request_id": str(uuid4()), "task_id": task_id, "package_id": metrics["package_id"],
            "package_checksum": metrics["package_checksum"], "max_repairs": 1,
            "confirm_automatic_repairs": True})
        assert created_response.status_code == 200, created_response.text
        quality_id = created_response.json()["id"]
        report["quality_id"] = quality_id
        run_response = client.post(f"/api/application-quality/{quality_id}/run", headers=OWNER_HEADERS)
        report["quality_http_status"] = run_response.status_code
        report["quality"] = run_response.json() if run_response.status_code == 200 else {"error": run_response.text[:2000]}
        assert run_response.status_code == 200, run_response.text
        assert report["quality"]["state"] == "passed", report["quality"]
        with task_repository._session_factory() as session:
            _, manifest = read_package(session, task_id, report["quality"]["final_package_id"])
            report["final_sources"] = {item["path"]: item["content"] for item in manifest["files"]}
            assert session.get(Task, task_id).progress == 0
        downloaded = client.get(
            f"/api/package-runs/{report['quality']['test_run_id']}/candidate.zip", headers=OWNER_HEADERS)
        assert downloaded.status_code == 200, downloaded.text
        (destination / selected["archive"]).write_bytes(downloaded.content)
        report["candidate_created"] = True
    except Exception as exc:
        report["failure"] = {"type": type(exc).__name__, "message": str(exc)[:2000]}
        raise
    finally:
        with task_repository._session_factory() as session:
            test_rows = list(session.scalars(select(PackageRun)))
            inference_rows = list(session.scalars(select(LocalInference)))
            report["tests"] = [{"id": row.id, "state": row.state, "result": row.result}
                               for row in test_rows]
            report["inferences"] = [{"id": row.id, "state": row.state,
                "metrics": row.metrics, "error_code": row.error_code,
                "result_checksum": row.result_checksum, "result_content": row.result_content}
                for row in inference_rows]
            if "final_sources" not in report and report.get("task_id"):
                package_ids = [row.metrics.get("package_id") for row in inference_rows
                               if isinstance(row.metrics, dict) and row.metrics.get("package_id")]
                if package_ids:
                    try:
                        _, manifest = read_package(session, report["task_id"], package_ids[-1])
                        report["final_sources"] = {
                            item["path"]: item["content"] for item in manifest["files"]}
                        report["final_sources_package_id"] = package_ids[-1]
                    except Exception as exc:
                        report["final_sources_error"] = str(exc)[:500]
        (destination / "report.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
