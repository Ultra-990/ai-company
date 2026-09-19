"""Explicit browser check of a retained synthetic model result, no new inference."""
import asyncio
from hashlib import sha256
import json
import os
from pathlib import Path

import pytest

from app.services.multifile_generation import parse_sources
from tests.browser_multifile_probe import check
from tests.test_multifile_execution import package
from tests.conftest import OWNER_HEADERS


@pytest.mark.skipif(not os.environ.get('AIC_QWEN_MULTIFILE_REPORT'),reason='Explicit retained synthetic pilot only')
def test_retained_qwen_app_browser(client,task_repository):
    path=Path(os.environ['AIC_QWEN_MULTIFILE_REPORT']).resolve()
    assert path.is_relative_to(Path('/home/marcin/ai-company-workspaces/qwen-training'))
    report=json.loads(path.read_text())
    assert report['schema']=='qwen-multifile-pilot.v1' and report['status']=='passed'
    files=parse_sources(report['generation']['content'])
    assert {k:sha256(v.encode()).hexdigest() for k,v in files.items()}==report['source_checksums']
    body=package(client,task_repository,files)
    cases=[
        dict(inputs={'#hours':'8','#rate':'322'},result='Razem: 2576',path='/api/quote?hours=8&rate=322'),
        dict(inputs={'#hours':'2.5','#rate':'20'},result='Razem: 50',path='/api/quote?hours=2.5&rate=20'),
        dict(inputs={'#hours':'0','#rate':'20'},result='Razem: 0',path='/api/quote?hours=0&rate=20'),
        dict(inputs={'#hours':'-1','#rate':'2'},result='Błąd: negative value',path='/api/quote?hours=-1&rate=2'),
        dict(inputs={'#hours':'','#rate':'2'},result='Podaj godziny i stawkę.',path=None),
    ]
    asyncio.run(check(client,body,OWNER_HEADERS,cases=cases,expected_color=None))
    assert task_repository.get_required(body['task_id']).progress==0
