"""Explicit short GPU probe. Public synthetic prompt; no database or client data."""
import json
import argparse
import sys
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.services.local_ollama import configuration, OllamaProvider

parser=argparse.ArgumentParser();parser.add_argument('--run-id',type=int)
args=parser.parse_args()
config=configuration() | {'num_predict':256,'timeout_seconds':60}
messages=[
    {'role':'system','content':'Odpowiadaj krótko po polsku. Nie twierdź, że wykonano testy lub działania.'},
    {'role':'user','content':'W maksymalnie 80 słowach podaj trzy kryteria odbioru specyfikacji małej strony firmowej. To próba tekstowego wykonawcy AI Company.'},
]
if args.run_id is not None:
    import app.main
    from app.core.config import load_settings
    from app.core.database import create_database_engine, create_session_factory
    from app.models.local_inference import LocalInference
    from app.services.agent_packets import export_prompt
    factory=create_session_factory(create_database_engine(load_settings().database.url))
    with factory() as session:
        run=session.get(LocalInference,args.run_id)
        if run is None or run.state not in {'failed','uncertain'}:raise ValueError('Diagnostic probe requires a failed run.')
        messages=export_prompt(session,run.task_id,run.packet_id)['messages']
    config=configuration()
result=OllamaProvider(config).complete(messages)
print(json.dumps(result,ensure_ascii=False,indent=2))
