"""Owner-authorized internal pilot. Creates one real project, never auto-accepts.

Stable IDs make restarting this script observational after a committed start.
No synthetic success, customer data, shell tool use or background model loop.
"""
import json
import argparse
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select, text
import app.main  # Register existing models; no application lifespan is started.
from app.core.config import load_settings
from app.core.database import create_database_engine, create_session_factory
from app.models.local_inference import LocalInference
from app.models.organization import OrganizationUnit
from app.services.work_orders import create_order
from app.services.agent_teams import initialize_teams, delegate_order
from app.services.agent_packets import prepare_packet
from app.services.local_inference import enqueue, execute, requeue
from app.services.local_ollama import OllamaProvider, ensure_idle

parser=argparse.ArgumentParser()
parser.add_argument('--retry',action='store_true',help='Explicit retry after confirming Ollama is idle; preserves failed history.')
args=parser.parse_args()
if args.retry:ensure_idle()

PROJECT_REQUEST='da3af974-5e4c-4d71-909f-9a8b9a5cc20c'
RUN_REQUEST='ea90e032-cc98-486d-bdf6-6cdd0f2f5d09'
engine=create_database_engine(load_settings().database.url)
LocalInference.__table__.create(engine,checkfirst=True)
factory=create_session_factory(engine)
with factory() as session:
    session.execute(text('BEGIN IMMEDIATE'))
    unit=session.scalar(select(OrganizationUnit).where(OrganizationUnit.os_key=='quality-security.testing'))
    if not unit:raise RuntimeError('Brak gałęzi jakości; nie utworzono alternatywnej struktury.')
    brief={'title':'Pilotaż Qwen — standard odbioru działu jakości',
           'goal':'Opracować specyfikację procedury odbioru tekstowych wyników agentów AI Company. Pierwszy etap: maksymalnie 300 słów; zakres, wyłączenia, kryteria, pytania i ryzyka. Oddziel istnienie tekstu od dowodu wykonania testów. Nie gwarantuj jakości bez kontroli.',
           'audience':'Właściciel i kierownik działu jakości AI Company.',
           'constraints':'Lokalny tekst, bez kodu wykonywanego na hoście, sieci zewnętrznej i danych klienta. Bez deklaracji wykonanych testów i automatycznej akceptacji.',
           'organization_unit_id':unit.id,
           'acceptance_criteria':['Każde kryterium można sprawdzić na konkretnej wersji wyniku.',
                                  'Wykonawca i odbiorca mają oddzielne obowiązki.',
                                  'Braki i ograniczenia są jawne; specyfikacja nie udaje wykonanej kontroli.']}
    order=create_order(session,PROJECT_REQUEST,brief)
    initialize_teams(session);delegate_order(session,order)
    previous=session.scalar(select(LocalInference).where(LocalInference.request_id==RUN_REQUEST))
    if previous:
        run_id=previous.id
        if args.retry:
            requeue(session,run_id,'60bfccf2-6763-4b39-8176-f8a6c0691ead')
    else:
        instruction=prepare_packet(session,order.task_ids[0])
        run=enqueue(session,order.task_ids[0],instruction.id,instruction.checksum,RUN_REQUEST);run_id=run['id']
    project_id=order.project_id;session.commit()
    result=execute(session,run_id,OllamaProvider)
    print(json.dumps({'project_id':project_id,**{k:result[k] for k in ('id','task_id','state','attempt_id','model','model_digest','metrics','error_code','result_checksum')},
                      'preview':(result['result_content'] or '')[:1500]},ensure_ascii=False,indent=2))
