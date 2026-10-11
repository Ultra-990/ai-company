"""Run a fresh isolated ROWEROWNIA delivery pilot when explicitly requested."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="store_true", help="invoke the local model and isolated Docker runner")
    parser.add_argument("--filewise", action="store_true", help="generate six files in bounded separate model calls")
    args = parser.parse_args()
    if not args.run:
        print(json.dumps({"model_invoked": False, "required_flag": "--run"}))
        return 0
    root = Path(__file__).resolve().parents[1]
    workspace = Path("/home/marcin/ai-company-workspaces")
    workspace.mkdir(exist_ok=True)
    destination = Path(tempfile.mkdtemp(prefix="business-website-pilot-", dir=workspace))
    env = dict(os.environ, AIC_BUSINESS_WEBSITE_PILOT="1",
               AIC_BUSINESS_WEBSITE_OUTPUT=str(destination.resolve()),
               AIC_SERVICE_QUOTE_TRANSFER_PILOT="0", AIC_WORKSHOP_CATALOG_PILOT="0",
               AIC_BUSINESS_WEBSITE_FILEWISE="1" if args.filewise else "0")
    print(json.dumps({"report": str((destination / "report.json").resolve())}), flush=True)
    result = subprocess.run([sys.executable, "-m", "pytest", "-q",
        "tests/test_business_website_delivery.py::test_fresh_business_website_delivery",
        "--basetemp", str(destination / "test-data")], cwd=root, env=env,
        timeout=850, check=False)
    print(json.dumps({"report": str((destination / "report.json").resolve()),
                      "exit_code": result.returncode}), flush=True)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
