"""Resume the preserved ROWEROWNIA pilot without regenerating its initial sources."""
import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import sys
from uuid import uuid4

from sqlalchemy import select

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app.main  # Register all persisted model tables.
from app.core.database import create_database_engine, create_session_factory
from app.models.local_inference import LocalInference
from app.models.package_run import PackageRun
from app.services import application_quality, container_runner, local_inference, package_runner
from app.services.local_ollama import OllamaProvider, configuration
from app.services.workspace_packages import read_package
from scripts.compare_local_models import check_idle

WORKSPACE = Path("/home/marcin/ai-company-workspaces")
PILOT = WORKSPACE / "business-website-pilot-fkf_d3w0"
SOURCE_REPORT = PILOT / "report.json"


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def new_output_directory():
    for number in range(1, 1000):
        candidate = PILOT / f"resume-{number}"
        try:
            candidate.mkdir(mode=0o700)
            return candidate
        except FileExistsError:
            continue
    raise ValueError("Resume directory limit reached")


def checked_path(path, *, root, filename=None):
    if any(item.is_symlink() for item in (path, *path.parents)):
        raise ValueError("Symlink path is not allowed")
    resolved = path.resolve(strict=True)
    if not resolved.is_relative_to(root.resolve(strict=True)):
        raise ValueError("Path is outside the preserved pilot")
    if filename is not None and resolved.name != filename:
        raise ValueError("Unexpected isolated database filename")
    return resolved


class IdleCheckedProvider:
    def __init__(self, config):
        self.provider = OllamaProvider(config)

    def complete(self, messages):
        check_idle()
        return self.provider.complete(messages)


class CheckedRunner(container_runner.ContainerRunner):
    def run(self, *args, **kwargs):
        check_idle()
        return super().run(*args, **kwargs)


def run():
    source = checked_path(SOURCE_REPORT, root=PILOT)
    raw = source.read_bytes()
    original = json.loads(raw)
    source_sha = sha256(raw).hexdigest()
    if original.get("schema") != "business-website-delivery.v1":
        raise ValueError("Unexpected source report schema")
    if not isinstance(original.get("task_id"), int) or not original.get("final_sources"):
        raise ValueError("Source report has no preserved task or sources")
    database = checked_path(Path(original["isolated_database"]), root=PILOT, filename="test.db")
    if database.stat().st_dev != Path("/home").stat().st_dev:
        raise ValueError("Isolated database must remain on the Linux workspace disk")
    harness = checked_path(PILOT / "independent-harness.py", root=PILOT)
    harness_sha = sha256(harness.read_bytes()).hexdigest()
    if harness_sha != original.get("harness_checksum"):
        raise ValueError("Frozen independent harness changed")

    resources = check_idle()
    output = new_output_directory()
    report_path = output / "report.json"
    report = {"schema": "business-website-resume.v1", "status": "running",
        "source_report": str(source), "source_report_sha256": source_sha,
        "isolated_database": str(database), "frozen_harness_sha256": harness_sha,
        "task_id": original["task_id"], "initial_generation_reused": True,
        "new_initial_generation": False, "source_final_sources": original["final_sources"],
        "resources_before": resources,
        "candidate_created": False, "owner_accepted": False, "deployed": False}
    save(report_path, report)

    engine = create_database_engine("sqlite:///" + str(database))
    factory = create_session_factory(engine)
    old_package_configuration = package_runner.configuration
    old_inference_configuration = local_inference.enabled_config
    current_config = container_runner.configuration() | {"harness_checksum": harness_sha}
    runner = CheckedRunner(harness=harness)
    package_runner.configuration = lambda: dict(current_config)
    local_inference.enabled_config = configuration
    try:
        with factory() as session:
            recorded = original.get("tests")
            if not isinstance(recorded, list) or len(recorded) != 1:
                raise ValueError("Expected exactly one recorded infrastructure run")
            old_id = recorded[0].get("id")
            old = session.get(PackageRun, old_id)
            quality = original.get("quality", {})
            if (not old or old.task_id != original["task_id"]
                    or old.package_id != quality.get("package_id")
                    or old.package_checksum != quality.get("package_checksum")
                    or old.state not in {"running", "uncertain", "interrupted"}):
                raise ValueError("Recorded uncertain run does not match the preserved package")
            report["reconciliation"] = package_runner.reconcile(session, old.id, runner)
            session.commit()
            save(report_path, report)

            created = application_quality.create(session,
                request_id=str(uuid4()), task_id=original["task_id"],
                package_id=quality["package_id"], package_checksum=quality["package_checksum"],
                max_repairs=1, confirm_automatic_repairs=True,
                acceptance_plan_id=None, acceptance_plan_checksum=None)
            session.commit()
            report["quality_id"] = created["id"]
            save(report_path, report)
            result = application_quality.execute(session, created["id"], IdleCheckedProvider, runner)
            report["quality"] = result
            session.commit()
            if result.get("state") == "passed":
                _, manifest = read_package(session, original["task_id"], result["final_package_id"])
                report["final_sources"] = {item["path"]: item["content"] for item in manifest["files"]}
                archive = package_runner.candidate_zip(session, result["test_run_id"])
                (output / "business-website-candidate.zip").write_bytes(archive)
                report["candidate_created"] = True
            report["status"] = result.get("state", "unknown")
    except Exception as exc:
        report["status"] = "failed"
        report["failure"] = {"type": type(exc).__name__, "message": str(exc)[:1000]}
        raise
    finally:
        package_runner.configuration = old_package_configuration
        local_inference.enabled_config = old_inference_configuration
        try:
            with factory() as session:
                report["tests"] = [{"id": row.id, "task_id": row.task_id,
                    "package_id": row.package_id, "package_checksum": row.package_checksum,
                    "state": row.state, "profile": row.profile, "result": row.result,
                    "report_id": row.report_id} for row in session.scalars(
                        select(PackageRun).where(PackageRun.task_id == original["task_id"]))]
                inferences = list(session.scalars(select(LocalInference).where(
                    LocalInference.task_id == original["task_id"])))
                report["inferences"] = [{"id": row.id, "state": row.state,
                    "attempt_id": row.attempt_id, "metrics": row.metrics,
                    "error_code": row.error_code, "result_checksum": row.result_checksum,
                    "result_content": row.result_content} for row in inferences]
                if "final_sources" not in report:
                    package_ids = [row.metrics.get("package_id") for row in inferences
                        if isinstance(row.metrics, dict) and row.metrics.get("package_id")]
                    if package_ids:
                        try:
                            _, manifest = read_package(session, original["task_id"], package_ids[-1])
                            report["final_sources"] = {
                                item["path"]: item["content"] for item in manifest["files"]}
                            report["final_sources_package_id"] = package_ids[-1]
                        except Exception as exc:
                            report["final_sources_error"] = str(exc)[:500]
        finally:
            engine.dispose()
            report["source_report_unchanged"] = (
                sha256(source.read_bytes()).hexdigest() == source_sha)
            save(report_path, report)
    print(json.dumps({"report": str(report_path), "status": report["status"]}))
    return 0 if report["status"] == "passed" else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="store_true",
                        help="reconcile and resume using the preserved isolated database")
    args = parser.parse_args()
    if not args.run:
        print(json.dumps({"model_invoked": False, "source_report": str(SOURCE_REPORT),
                          "required_flag": "--run"}))
        return 0
    return run()


if __name__ == "__main__":
    raise SystemExit(main())
