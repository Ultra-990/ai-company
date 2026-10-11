"""Check semicolon route boundaries for an isolated PLAN ZAJĘĆ candidate."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.services.application_preview import HARNESS as PREVIEW_HARNESS
from app.services.application_profile import parse_sources
from app.services.container_runner import ContainerRunner, configuration
from scripts.compare_local_models import check_idle

PILOT = Path("/home/marcin/ai-company-workspaces/workshop-catalog-r59rfvqy")
SOURCE = PILOT / "report.json"
EXPECTED_SOURCE_SHA256 = "80c6bb4d63dfd3fabedc8a2d6a7b0b4808cd61fbddbfa91c6a269c3704aee1e5"
SCHEMAS = {"workshop-catalog-delivery.v1", "workshop-catalog-ui-repair.v1",
           "workshop-catalog-route-repair.v1", "workshop-catalog-route-refinement.v1"}
UI_REPAIR_SHA256 = "7d28033d294b96281ae2d22b2c41f64d226a000301c3b7392455ca6a397d1a74"
ROUTES_SHA256 = "9ce14a5268ee443f4624a76111a5201af1788c0fc55a9956d9d1f6dae52cd824"
ROUTE_REPAIR_SHA256 = "27e607b4fae6da9c5868489a464ecc8ca12aed70ab1634b560de7714216d44a7"
ROUTE_REPAIR_EVIDENCE_SHA256 = "95b62355921be5ba6462fd091cd16b52e988c7e464fc4543828190ef7b1be354"
ROUTE_REFINEMENT1_SHA256 = "3857aca7fba6598c0ba9ea0daa49f0d549f2c0f95244999f237a01fa73a64e8a"
ROUTE_REFINEMENT1_EVIDENCE_SHA256 = "c23d8fa3007dba4f5e850d40cfbc1831eff6a973fe543f27c1a87351f17acdbd"
ROUTE_REFINEMENT2_FAILED_SHA256 = "bee2701ac4a40e01a9a0a4a4a77d28d7022f6f34823f90f86aae209cddb5fba7"
FILES = {"app.py", "test_app.py", "index.html", "style.css", "app.js", "README.md"}
PROBES = (
    ("valid-control", "/api/sessions?day=all&level=all", 200),
    ("api-semicolon-suffix", "/api/sessions;extra?day=all&level=all", 404),
    ("health-semicolon-suffix", "/health;extra", 404),
    ("root-semicolon-suffix", "/;extra", 404),
)
SUPPLEMENTAL_PROBES = (
    ("health-empty-semicolon", "/health;", 404),
)
ALLOWED_PATHS = {path for _, path, _ in (*PROBES, *SUPPLEMENTAL_PROBES)}


def route_configuration():
    return configuration() | {
        "profile": "workshop-catalog-route-preview-v1",
        "harness_checksum": sha256(PREVIEW_HARNESS.read_bytes()).hexdigest(),
        "stateless": True,
    }


class RouteProbeRunner(ContainerRunner):
    """Trusted CLI runner restricted to the four frozen diagnostic paths."""
    def __init__(self, path):
        if path not in ALLOWED_PATHS:
            raise ValueError("Route probe path is outside the frozen allowlist")
        super().__init__(PREVIEW_HARNESS)
        self.path = path

    def run(self, files, config, name):
        if config != route_configuration():
            raise ValueError("Stale route probe profile")
        request = json.dumps({"path": self.path}, ensure_ascii=True)
        return super().run(files | {"preview_request.json": request}, config, name)


def digest_bytes(raw):
    return sha256(raw).hexdigest()


def save(path, value):
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def checked_report(path):
    path = Path(path)
    if any(item.is_symlink() for item in (path, *path.parents)):
        raise ValueError("Symlink report path is not allowed")
    resolved = path.resolve(strict=True)
    if not resolved.is_relative_to(PILOT.resolve(strict=True)):
        raise ValueError("Report is outside the workshop pilot")
    return resolved


def _original():
    path = checked_report(SOURCE)
    raw = path.read_bytes()
    if digest_bytes(raw) != EXPECTED_SOURCE_SHA256:
        raise ValueError("Fixed workshop delivery report changed")
    report = json.loads(raw)
    files = report.get("final_sources")
    if (report.get("schema") != "workshop-catalog-delivery.v1"
            or report.get("candidate_created") is not True
            or report.get("owner_accepted") is not False
            or report.get("deployed") is not False
            or not isinstance(files, dict) or set(files) != FILES):
        raise ValueError("Fixed workshop delivery report is not the reviewed candidate")
    parse_sources(json.dumps({"files": files}, ensure_ascii=False))
    return path, report, files


def load_source(path=SOURCE):
    original_path, original, original_files = _original()
    path = checked_report(path)
    raw = path.read_bytes()
    source_sha = digest_bytes(raw)
    if path == original_path:
        return path, source_sha, original, original_files
    report = json.loads(raw)
    files = report.get("final_sources")
    if report.get("schema") == "workshop-catalog-route-refinement.v1":
        source_path = checked_report(Path(report.get("source_report", "")))
        source_raw = source_path.read_bytes()
        source_report = json.loads(source_raw)
        source_files = source_report.get("final_sources", {})
        preserved = {name: sha256(content.encode()).hexdigest()
                     for name, content in source_files.items() if name != "app.py"}
        later_round=report.get('refinement_round') in {2,3}
        expected_source_sha=ROUTE_REFINEMENT1_SHA256 if later_round else ROUTE_REPAIR_SHA256
        expected_evidence_sha=ROUTE_REFINEMENT1_EVIDENCE_SHA256 if later_round else ROUTE_REPAIR_EVIDENCE_SHA256
        if (digest_bytes(source_raw) != expected_source_sha
                or report.get("source_report_sha256") != expected_source_sha
                or report.get("routes_report_sha256") != expected_evidence_sha
                or (report.get('refinement_round')==3
                    and report.get('failed_refinement_report_sha256')!=ROUTE_REFINEMENT2_FAILED_SHA256)
                or report.get("candidate_created") is not True
                or report.get("exact_change_scope") is not True
                or report.get("owner_accepted") is not False or report.get("deployed") is not False
                or not isinstance(files, dict) or set(files) != FILES
                or files.get("app.py") == source_files.get("app.py")
                or any(sha256(files[name].encode()).hexdigest() != value
                       for name, value in preserved.items())):
            raise ValueError("Selected report is not an intact workshop route refinement chain")
        parse_sources(json.dumps({"files": files}, ensure_ascii=False))
        return path, source_sha, report, files
    if report.get("schema") == "workshop-catalog-route-repair.v1":
        source_path = checked_report(Path(report.get("source_report", "")))
        source_raw = source_path.read_bytes()
        source_report = json.loads(source_raw)
        source_files = source_report.get("final_sources", {})
        preserved = {name: sha256(content.encode()).hexdigest()
                     for name, content in source_files.items() if name != "app.py"}
        if (digest_bytes(source_raw) != UI_REPAIR_SHA256
                or report.get("source_report_sha256") != UI_REPAIR_SHA256
                or report.get("routes_report_sha256") != ROUTES_SHA256
                or report.get("candidate_created") is not True
                or report.get("exact_change_scope") is not True
                or report.get("owner_accepted") is not False or report.get("deployed") is not False
                or not isinstance(files, dict) or set(files) != FILES
                or files.get("app.py") == source_files.get("app.py")
                or any(sha256(files[name].encode()).hexdigest() != value
                       for name, value in preserved.items())):
            raise ValueError("Selected report is not an intact workshop route repair chain")
        parse_sources(json.dumps({"files": files}, ensure_ascii=False))
        return path, source_sha, report, files
    if (report.get("schema") != "workshop-catalog-ui-repair.v1"
            or report.get("source_report_sha256") != EXPECTED_SOURCE_SHA256
            or report.get("candidate_created") is not True
            or report.get("owner_accepted") is not False
            or report.get("deployed") is not False
            or not isinstance(files, dict) or set(files) != FILES):
        raise ValueError("Selected report is not an intact workshop UI repair")
    parse_sources(json.dumps({"files": files}, ensure_ascii=False))
    return path, source_sha, report, files


def new_output():
    for number in range(1, 1000):
        candidate = PILOT / f"routes-check-{number}"
        try:
            candidate.mkdir(mode=0o700)
            return candidate
        except FileExistsError:
            continue
    raise ValueError("Route check directory limit reached")


def run(source, include_supplemental=False):
    source, source_sha, selected, files = load_source(source)
    output = new_output()
    report_path = output / "report.json"
    selected_probes = (*PROBES, *SUPPLEMENTAL_PROBES) if include_supplemental else PROBES
    report = {
        "schema": "workshop-catalog-routes-check.v1", "status": "running",
        "source_report": str(source), "source_report_sha256": source_sha,
        "selected_source_schema": selected["schema"],
        "source_sha256": {name: sha256(content.encode()).hexdigest()
                          for name, content in files.items()},
        "probes": [], "supplemental_probes_included": include_supplemental,
        "passed": False, "owner_accepted": False, "deployed": False,
    }
    save(report_path, report)
    profile = route_configuration()
    for name, path, expected in selected_probes:
        try:
            check_idle()
            raw = RouteProbeRunner(path).run(files, profile, "aic-package-" + uuid4().hex)
        except Exception as exc:
            report["status"] = "incomplete"
            report["error_type"] = type(exc).__name__
            report["source_unchanged"] = digest_bytes(source.read_bytes()) == source_sha
            save(report_path, report)
            print(json.dumps({"report": str(report_path), "status": "incomplete",
                              "error_type": report["error_type"]}))
            return 2
        try:
            payload = json.loads(raw.get("log", ""))
            response = payload["response"]
            observed = response["status"]
            valid = (raw.get("exit_code") == 0 and raw.get("cli_exit_code") == 0
                     and raw.get("cleanup_confirmed") is True and raw.get("reason") is None
                     and raw.get("profile") == profile
                     and payload.get("schema") == "python-web-preview.v1"
                     and type(observed) is int and isinstance(response.get("body"), str))
        except (ValueError, KeyError, TypeError, json.JSONDecodeError):
            response = {}
            observed = None
            valid = False
        report["probes"].append({
            "name": name, "path": path, "expected_status": expected,
            "observed_status": observed, "passed": valid and observed == expected,
            "response": response, "raw_run": raw,
        })
        save(report_path, report)
    report["passed"] = all(item["passed"] for item in report["probes"])
    report["status"] = "passed" if report["passed"] else "failed"
    report["source_unchanged"] = digest_bytes(source.read_bytes()) == source_sha
    save(report_path, report)
    print(json.dumps({"report": str(report_path), "status": report["status"]}))
    return 0 if report["passed"] else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="store_true", help="run four isolated CPU previews, plus optional supplemental probe")
    parser.add_argument("--report", type=Path, default=SOURCE,
                        help="delivery, UI repair, or intact workshop route repair report")
    parser.add_argument("--include-supplemental", action="store_true",
                        help="also diagnose the separately frozen /health; boundary")
    args = parser.parse_args()
    source, source_sha, selected, _ = load_source(args.report)
    if not args.run:
        print(json.dumps({
            "containers_started": False, "source_report": str(source),
            "source_report_sha256": source_sha, "selected_source_schema": selected["schema"],
            "probes": [{"name": name, "path": path, "expected_status": expected}
                       for name, path, expected in ((*PROBES, *SUPPLEMENTAL_PROBES)
                                                    if args.include_supplemental else PROBES)],
            "supplemental_probes_included": args.include_supplemental,
            "required_flag": "--run",
        }))
        return 0
    return run(source, args.include_supplemental)


if __name__ == "__main__":
    raise SystemExit(main())
