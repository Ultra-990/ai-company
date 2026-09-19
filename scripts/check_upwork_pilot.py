"""Opt-in synthetic qualification with real local Qwen and an isolated test DB."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

root=Path(__file__).resolve().parents[1]
destination=Path(tempfile.mkdtemp(prefix='upwork-scope-pilot-',dir='/home/marcin/ai-company-workspaces'))
env=dict(os.environ,AIC_UPWORK_PILOT='1',AIC_UPWORK_PILOT_OUTPUT=str(destination))
result=subprocess.run([sys.executable,'-m','pytest','-q',
    'tests/test_upwork_orders.py::test_real_qwen_rejects_unsupported_scope',
    '--basetemp',str(destination/'test-data')],cwd=root,env=env,timeout=260,check=False)
print(json.dumps({'directory':str(destination),'exit_code':result.returncode}))
sys.exit(result.returncode)
