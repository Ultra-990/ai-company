"""Create and test one full model revision of the preserved CREMA transfer pilot."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys
from uuid import uuid4

from sqlalchemy import select

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app.main  # Register all persisted model tables.
from app.core.database import create_database_engine, create_session_factory
from app.models.local_inference import LocalInference
from app.models.package_run import PackageRun
from app.services import application_revisions, container_runner, local_inference, package_runner
from app.services.application_profile import PROFILE
from app.services.local_ollama import OllamaProvider, configuration
from app.services.workspace_packages import read_package
from scripts.compare_local_models import check_idle
from scripts.filewise_application_provider import FilewiseApplicationProvider, FILES

WORKSPACE = Path("/home/marcin/ai-company-workspaces")
PILOT = WORKSPACE / "service-quote-transfer-q4ylytju"
PARENT_REPORT = PILOT / "report.json"
HARNESS = PILOT / "independent-harness.py"
EXPECTED_PACKAGE_ID = 2
EXPECTED_PACKAGE_CHECKSUM = "5b8d741a3d597df1c6f89384dbb93b13f51af20a94e663478cf94376fed1f768"
EXPECTED_HARNESS_CHECKSUM = "13e64d0ab231b8e3bb83ec0d421daf0dc35c4a54267f78295f99c130876e10c1"

DESCRIPTION = """Pełna rewizja sześciu źródeł CREMA po pierwszym, zachowanym teście transferowym:
1. Napraw własny test_app.py tak, aby helper naprawdę wywoływał Handler.do_GET na kontrolowanym obiekcie testowym i oddzielnie rejestrował status, nagłówki oraz body. Sprawdzaj JSON semantycznie po json.loads zamiast zależeć od spacji json.dumps. Zachowaj wszystkie przypadki, statusy i asercje wartości; nie usuwaj ani nie osłabiaj testów.
2. index.html ma ładować zewnętrzne style.css i app.js. Usuń ich osadzone kopie, zachowując dokładnie sześć wymaganych plików.
3. Dodaj dokładnie jeden widoczny h1. Umieść menu-toggle poza ukrywanym mobilnie nav#site-nav; przycisk ma sterować nav i aria-expanded, a Escape zamykać menu i przywracać fokus.
4. Dodaj osobną, widoczną sekcję procesu poza FAQ. Kontakt ma być wyłącznie jasno oznaczonym fikcyjnym tekstem demonstracyjnym, bez konkretnego telefonu, e-maila lub adresu pocztowego.
5. Zachowaj /api/quote, ceny, identyfikatory DOM, kalkulator, FAQ i bezpieczny file://. onsite może być selectem 0/1 albo checkboxem, lecz app.js musi wysyłać właściwe 0/1.
Niezmieniony niezależny harness jest nadrzędnym testem odbiorczym. Nie dopasowuj kodu przez usuwanie wymagań testów."""

EXPECTED = """Zwróć kompletne nowe źródła dokładnie sześciu plików: app.py, test_app.py, index.html, style.css, app.js i README.md. Nie usuwaj ani nie osłabiaj testów. Kandydat musi przejść niezmieniony niezależny harness; wynik pozostaje do odbioru właściciela."""


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def save(path, value):
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def checked_file(path, root=PILOT):
    if any(item.is_symlink() for item in (path, *path.parents)):
        raise ValueError("Symlink path is not allowed")
    resolved = path.resolve(strict=True)
    if not resolved.is_relative_to(root.resolve(strict=True)):
        raise ValueError("Evidence is outside the preserved pilot")
    return resolved


def evidence():
    paths = (PARENT_REPORT, HARNESS)
    return {str(path.relative_to(PILOT)): digest(checked_file(path)) for path in paths}


def load_parent():
    parent = json.loads(checked_file(PARENT_REPORT).read_text(encoding="utf-8"))
    if (parent.get("schema") != "service-quote-transfer-delivery.v1"
            or parent.get("task_id") != 1 or parent.get("final_sources_package_id") != EXPECTED_PACKAGE_ID
            or parent.get("quality", {}).get("package_checksum") != EXPECTED_PACKAGE_CHECKSUM
            or set(parent.get("final_sources", {})) != set(FILES)):
        raise ValueError("Preserved parent revision is not the expected six-file package")
    database = checked_file(Path(parent["isolated_database"]), root=PILOT)
    if database.name != "test.db" or database.stat().st_dev != Path("/home").stat().st_dev:
        raise ValueError("Expected isolated Linux database")
    if digest(HARNESS) != EXPECTED_HARNESS_CHECKSUM or parent.get("harness_checksum") != EXPECTED_HARNESS_CHECKSUM:
        raise ValueError("Frozen independent harness changed")
    return parent, database


def new_output_directory():
    for number in range(1, 1000):
        candidate = PILOT / f"revision-{number}"
        try:
            candidate.mkdir(mode=0o700)
            return candidate
        except FileExistsError:
            continue
    raise ValueError("Revision directory limit reached")


class CheckedRunner(container_runner.ContainerRunner):
    def run(self, *args, **kwargs):
        check_idle()
        return super().run(*args, **kwargs)


def validate_database(session, parent):
    task_id = parent["task_id"]
    latest = session.scalar(select(LocalInference).where(
        LocalInference.task_id == task_id).order_by(LocalInference.id.desc()).limit(1))
    origin = session.scalar(select(LocalInference).where(
        LocalInference.task_id == task_id, LocalInference.state == "awaiting_review")
        .order_by(LocalInference.id.asc()).limit(1))
    if (not latest or latest.state != "failed" or latest.error_code != "invalid_file_repair"
            or not origin or origin.metrics.get("package_id") != EXPECTED_PACKAGE_ID
            or origin.metrics.get("package_checksum") != EXPECTED_PACKAGE_CHECKSUM):
        raise ValueError("Isolated database is not at the preserved failed-repair checkpoint")
    package, manifest = read_package(session, task_id, EXPECTED_PACKAGE_ID)
    files = {item["path"]: item["content"] for item in manifest["files"]}
    if package.checksum != EXPECTED_PACKAGE_CHECKSUM or files != parent["final_sources"]:
        raise ValueError("Package 2 no longer matches the preserved parent sources")
    return task_id


def run():
    parent, database = load_parent()
    proof = evidence()
    check_idle()
    output = new_output_directory()
    report_path = output / "report.json"
    report = {"schema": "service-quote-transfer-revision.v1", "status": "running",
        "task_id": parent["task_id"],
        "parent_report": str(PARENT_REPORT), "parent_report_sha256": proof["report.json"],
        "evidence_sha256": proof, "isolated_database": str(database),
        "source_package_id": EXPECTED_PACKAGE_ID,
        "source_package_checksum": EXPECTED_PACKAGE_CHECKSUM,
        "frozen_harness_sha256": proof["independent-harness.py"],
        "requested_files": list(FILES), "owner_accepted": False, "deployed": False,
        "candidate_created": False, "description": DESCRIPTION}
    save(report_path, report)
    engine = create_database_engine("sqlite:///" + str(database))
    factory = create_session_factory(engine)
    old_package_configuration = package_runner.configuration
    old_inference_configuration = local_inference.enabled_config
    runner = CheckedRunner(harness=HARNESS)
    fixed_configuration = container_runner.configuration() | {
        "harness_checksum": proof["independent-harness.py"]}
    package_runner.configuration = lambda: dict(fixed_configuration)
    local_inference.enabled_config = configuration
    try:
        with factory() as session:
            task_id = validate_database(session, parent)
            created = application_revisions.create(session, reviewer_role="automated_qa",
                output_profile=PROFILE, task_id=task_id, package_id=EXPECTED_PACKAGE_ID,
                package_checksum=EXPECTED_PACKAGE_CHECKSUM, request_id=str(uuid4()),
                description=DESCRIPTION, expected_result=EXPECTED,
                evidence=[f"{name}: sha256={value}" for name, value in sorted(proof.items())],
                auto_test=True)
            session.commit()
            report["revision_id"] = created["id"]
            report["inference_id"] = created["inference_id"]
            save(report_path, report)

            def provider(config):
                return FilewiseApplicationProvider(config, output / "filewise" / uuid4().hex,
                    provider_factory=OllamaProvider, idle_check=check_idle)

            result = application_revisions.execute(session, created["id"], provider, runner)
            session.commit()
            report["revision"] = result
            report["status"] = result["state"]
            if result.get("new_package_id"):
                _, manifest = read_package(session, task_id, result["new_package_id"])
                report["final_sources"] = {item["path"]: item["content"] for item in manifest["files"]}
            if result.get("test_state") == "passed":
                archive = package_runner.candidate_zip(session, result["test_run_id"])
                candidate = output / "service-quote-transfer-candidate.zip"
                candidate.write_bytes(archive)
                report["candidate_zip"] = str(candidate)
                report["candidate_zip_sha256"] = digest(candidate)
                report["candidate_created"] = True
    except Exception as exc:
        report["status"] = "failed"
        report["failure"] = {"type": type(exc).__name__, "message": str(exc)[:1000]}
        raise
    finally:
        package_runner.configuration = old_package_configuration
        local_inference.enabled_config = old_inference_configuration
        try:
            with factory() as session:
                report["tests"] = [{"id": row.id, "package_id": row.package_id,
                    "package_checksum": row.package_checksum, "state": row.state,
                    "profile": row.profile, "result": row.result, "report_id": row.report_id}
                    for row in session.scalars(select(PackageRun).where(
                        PackageRun.task_id == parent["task_id"]))]
                report["inferences"] = [{"id": row.id, "state": row.state,
                    "attempt_id": row.attempt_id, "metrics": row.metrics,
                    "error_code": row.error_code, "result_checksum": row.result_checksum,
                    "result_content": row.result_content} for row in session.scalars(
                        select(LocalInference).where(LocalInference.task_id == parent["task_id"]))]
        finally:
            engine.dispose()
            report["evidence_unchanged"] = evidence() == proof
            save(report_path, report)
    print(json.dumps({"report": str(report_path), "status": report["status"]}))
    return 0 if report["status"] == "awaiting_review" and report["candidate_created"] else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="store_true",
                        help="invoke Qwen, create a full six-file revision and run the frozen harness")
    args = parser.parse_args()
    parent, database = load_parent()
    engine = create_database_engine("sqlite:///" + str(database))
    try:
        with create_session_factory(engine)() as session:
            task_id = validate_database(session, parent)
    finally:
        engine.dispose()
    if not args.run:
        print(json.dumps({"model_invoked": False, "task_id": task_id,
            "source_package_id": EXPECTED_PACKAGE_ID,
            "source_package_checksum": EXPECTED_PACKAGE_CHECKSUM,
            "parent_report_sha256": digest(PARENT_REPORT),
            "frozen_harness_sha256": digest(HARNESS), "requested_files": list(FILES),
            "output_profile": PROFILE, "required_flag": "--run"}, ensure_ascii=False))
        return 0
    return run()


if __name__ == "__main__":
    raise SystemExit(main())
