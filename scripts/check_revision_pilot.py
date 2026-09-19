"""Opt-in real Qwen revision on a synthetic copy, never changes the real demo task."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import argparse

root=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser();parser.add_argument('--automatic',action='store_true');args=parser.parse_args()
destination=Path(tempfile.mkdtemp(prefix='automatic-quality-pilot-' if args.automatic else 'revision-pilot-',dir='/home/marcin/ai-company-workspaces'))
env=dict(os.environ,AIC_REVISION_PILOT='1',AIC_QUALITY_PILOT='1' if args.automatic else '0',AIC_REVISION_PILOT_OUTPUT=str(destination))
result=subprocess.run([sys.executable,'-m','pytest','-q',
    'tests/test_application_quality.py::test_real_qwen_automatic_repair_pilot' if args.automatic else 'tests/test_application_revisions.py::test_real_qwen_revision_pilot',
    '--basetemp',str(destination/'test-data')],cwd=root,env=env,timeout=600 if args.automatic else 260,check=False)
print(json.dumps({'directory':str(destination),'exit_code':result.returncode}))
sys.exit(result.returncode)
