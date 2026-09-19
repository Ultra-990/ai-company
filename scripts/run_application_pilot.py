"""Owner-authorized bounded application pilot, local model + isolated tests only.

Stable IDs prevent duplicate generation/execution. No automated acceptance.
The new pilot's first task is deliberately scoped as a builder task, with the
complete specification below as its input (not a fictitiously accepted analysis).
"""
import json
import sys
from pathlib import Path
from sqlalchemy import select,text
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import app.main
from app.core.config import load_settings
from app.core.database import create_database_engine,create_session_factory
from app.models.local_inference import LocalInference
from app.models.package_run import PackageRun
from app.models.task import Task
from app.models.organization import OrganizationUnit
from app.models.organization_os import Agent
from app.models.delegation import TaskDelegation
from app.models.audit import AuditEvent
from app.services.work_orders import create_order
from app.services.agent_teams import initialize_teams,delegate_order,team_key
from app.services.agent_packets import prepare_packet
from app.services.local_inference import enqueue,execute
from app.services.local_ollama import OllamaProvider
from app.services.package_runner import start,candidate_zip
from app.services.container_runner import ContainerRunner

PROJECT='8d8d5318-9f91-4b22-b2cf-b84cae8b2f01'
GENERATION='201767e3-b0f1-479d-a369-38a470b3f67b'
TEST='7a71d5be-ced6-4a8b-b1b3-170dba613e81'
engine=create_database_engine(load_settings().database.url)
PackageRun.__table__.create(engine,checkfirst=True)
factory=create_session_factory(engine)
with factory() as s:
    s.execute(text('BEGIN IMMEDIATE'))
    unit=s.scalar(select(OrganizationUnit).where(OrganizationUnit.os_key=='web-platforms.business'))
    brief={'title':'Pilotaż fabryki aplikacji — kalkulator zakresu',
           'goal':'Build a small Polish web app: an hours × hourly rate calculator. GET /api/estimate?hours=2&rate=50 returns JSON {"total":100}. Numbers must be finite and non-negative; missing, negative, NaN or malformed inputs return HTTP400. GET /health returns {"status":"ok"}. GET / serves a polished responsive HTML page with labelled inputs and app.js using fetch and textContent. No saving data, no external resources, no dependencies. app.py exposes only /, /health, /api/estimate, /style.css and /app.js; all other paths 404. Include at least five real unittest cases for arithmetic and invalid inputs. No financial/tax advice.',
           'audience':'Właściciel AI Company, wewnętrzny demonstrator bez danych klientów.',
           'constraints':'Python 3.10 standard library only. HOST=127.0.0.1, PORT=8080. Four required root files app.py test_app.py index.html README.md plus optional style.css app.js. Tests must not bind port at import. No external network, code on host, publication or automatic acceptance.',
           'organization_unit_id':unit.id,
           'acceptance_criteria':['Poprawny iloczyn godzin i stawki; HTTP400 dla błędnych wartości.',
                                  'Interfejs po polsku; etykiety pól i wynik jako tekst.',
                                  'Rzeczywiste testy w izolacji, raport oraz paczka źródeł.']}
    order=create_order(s,PROJECT,brief);initialize_teams(s);delegate_order(s,order)
    previous=s.scalar(select(LocalInference).where(LocalInference.request_id==GENERATION))
    if previous:run_id=previous.id
    else:
        task=s.get(Task,order.task_ids[0]);delegation=s.get(TaskDelegation,task.id)
        builder=s.scalar(select(Agent).where(Agent.agent_key==team_key(delegation.department_id,'builder')))
        task.title='Implementacja demonstratora: kalkulator zakresu'
        criterion='Pliki kompletnej aplikacji zgodne ze specyfikacją wejściową; wynik wymaga testów i odbioru.'
        task.description=brief['goal']+'\nKryterium etapu: '+criterion
        task.assigned_agent=builder.agent_key;delegation.worker_id=builder.id
        delegation.execution_brief=task.description
        delegation.completion_criterion=criterion
        s.add(AuditEvent(event_type='pilot_scope',operation='configure_builder',allowed=True,decision='planned',
                        reason=f'owner delegated pilot; task={task.id}; full input specification; no predecessor accepted or fabricated'))
        instruction=prepare_packet(s,task.id)
        run=enqueue(s,task.id,instruction.id,instruction.checksum,GENERATION,output_profile='python-web-v1');run_id=run['id']
    project_id=order.project_id;s.commit()
    generated=execute(s,run_id,OllamaProvider)
    print(json.dumps({'stage':'generation','project_id':project_id,'run_id':run_id,'state':generated['state'],
                      'task_id':generated['task_id'],'metrics':generated['metrics'],'error_code':generated['error_code']},ensure_ascii=False),flush=True)
    if generated['state']!='awaiting_review' or not generated['metrics'].get('package_id'):sys.exit(1)
    task_id=generated['task_id'];metrics=generated['metrics'];s.rollback()
    tested=start(s,task_id,metrics['package_id'],metrics['package_checksum'],TEST,ContainerRunner())
    print(json.dumps({'stage':'isolated_tests',**tested},ensure_ascii=False,indent=2),flush=True)
    if tested['state']!='passed':sys.exit(2)
    archive=candidate_zip(s,tested['id'])
    import tempfile
    directory=Path(tempfile.mkdtemp(prefix='candidate-',dir='/home/marcin/ai-company-workspaces'))
    target=directory/'application-candidate.zip';target.write_bytes(archive)
    print(json.dumps({'candidate_zip':str(target),'accepted':False,'deployed':False}))
