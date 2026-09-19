"""Explicit local model pilot; all tasks and results live in a separate test DB."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

root=Path(__file__).resolve().parents[1]
destination=Path(tempfile.mkdtemp(prefix='department-agent-pilot-',dir='/home/marcin/ai-company-workspaces'))
env=dict(os.environ,AIC_DEPARTMENT_PILOT='1',AIC_DEPARTMENT_PILOT_OUTPUT=str(destination))
result=subprocess.run([sys.executable,'-m','pytest','-q',
    'tests/test_department_agents.py::test_real_department_analyst_without_invented_finances',
    '--basetemp',str(destination/'test-data')],cwd=root,env=env,timeout=260,check=False)
print(json.dumps({'directory':str(destination),'exit_code':result.returncode}))
sys.exit(result.returncode)
