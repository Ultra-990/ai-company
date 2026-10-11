"""Run the fresh PLAN ZAJĘĆ workshop catalogue through the shared delivery path."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run',action='store_true',help='invoke the local model and isolated Docker runner')
    args=parser.parse_args()
    if not args.run:
        print(json.dumps({'model_invoked':False,'docker_invoked':False,
                          'scenario':'workshop-catalog','required_flag':'--run'}))
        return 0
    root=Path(__file__).resolve().parents[1]
    workspace=Path('/home/marcin/ai-company-workspaces');workspace.mkdir(exist_ok=True)
    destination=Path(tempfile.mkdtemp(prefix='workshop-catalog-',dir=workspace))
    env=dict(os.environ,AIC_WORKSHOP_CATALOG_PILOT='1',
             AIC_WORKSHOP_CATALOG_OUTPUT=str(destination.resolve()),
             AIC_BUSINESS_WEBSITE_PILOT='0',AIC_SERVICE_QUOTE_TRANSFER_PILOT='0',
             AIC_BUSINESS_WEBSITE_FILEWISE='1')
    report=destination/'report.json';print(json.dumps({'report':str(report.resolve())}),flush=True)
    result=subprocess.run([sys.executable,'-m','pytest','-q',
        'tests/test_business_website_delivery.py::test_fresh_business_website_delivery',
        '--basetemp',str(destination/'test-data')],cwd=root,env=env,timeout=850,check=False)
    print(json.dumps({'report':str(report.resolve()),'exit_code':result.returncode}),flush=True)
    return result.returncode


if __name__=='__main__':raise SystemExit(main())
