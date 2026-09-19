"""Fresh synthetic app + local Qwen + isolated Docker; never production DB."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

root=Path(__file__).resolve().parents[1]
destination=Path(tempfile.mkdtemp(prefix='application-delivery-pilot-',dir='/home/marcin/ai-company-workspaces'))
env=dict(os.environ,AIC_DELIVERY_PILOT='1',AIC_DELIVERY_PILOT_OUTPUT=str(destination))
print(json.dumps({'directory':str(destination)}),flush=True)
result=subprocess.run([sys.executable,'-m','pytest','-q',
    'tests/test_application_delivery_pilot.py::test_fresh_application_delivery',
    '--basetemp',str(destination/'test-data')],cwd=root,env=env,timeout=850,check=False)
print(json.dumps({'directory':str(destination),'exit_code':result.returncode}))
sys.exit(result.returncode)
