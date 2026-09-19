import json
import subprocess
import pytest
from app.services import local_ollama as adapter

CONFIG={'model':'qwen3.8:27b','digest':'a'*64,'timeout_seconds':30,'num_ctx':8192,'num_predict':128,'num_thread':2}


@pytest.mark.parametrize('extra', [{}, {'format':'json'},
    {'format':{'type':'object','required':['questions'],'properties':{'questions':{'type':'array','maxItems':6,'items':{'type':'string'}}}}},
    {'sampling_profile':'qwen-general-trial.v1'}])
def test_transport_is_loopback_streamed_pinned_and_toolless(monkeypatch,extra):
    requests=[]
    class Response:
        status=200
        def __init__(self,inventory):self.inventory=inventory
        def read(self,limit):return json.dumps({'models':[{'name':CONFIG['model'],'digest':CONFIG['digest']}]}).encode()
        def readline(self,limit):return json.dumps({'message':{'content':'Wynik'},'done':True,'done_reason':'stop','eval_count':1}).encode()+b'\n'
    class Connection:
        def __init__(self,host,port,timeout):assert (host,port,timeout)==('127.0.0.1',11434,30);self.calls=0
        def request(self,method,path,**kw):requests.append((method,path,kw));self.calls+=1
        def getresponse(self):return Response(self.calls==1)
        def close(self):requests.append('closed')
    monkeypatch.setattr('http.client.HTTPConnection',Connection)
    result=adapter.transport({'config':CONFIG|extra,'messages':[{'role':'user','content':'Publiczna próba'}]})
    assert result['content']=='Wynik' and result['digest']==CONFIG['digest']
    assert requests[-1]=='closed'
    payload=json.loads(requests[1][2]['body'])
    assert payload['stream'] and payload['keep_alive']==0 and payload['think'] is False
    assert 'tools' not in payload and payload['options']['num_predict']==128
    assert payload.get('format')==extra.get('format')
    assert payload['options']['temperature']==(0.7 if extra.get('sampling_profile') else 0.2)


@pytest.mark.parametrize('extra', [{'sampling_profile':'arbitrary'}, {'format':'other'},
    {'format':{'$ref':'https://example.com/schema'}}, {'format':{'type':'object','description':'x'*16000}}])
def test_invalid_generation_settings_fail_before_network(monkeypatch,extra):
    monkeypatch.setattr('http.client.HTTPConnection',lambda *a,**k:pytest.fail('Unexpected network'))
    with pytest.raises(ValueError,match='invalid_generation_profile'):
        adapter.transport({'config':CONFIG|extra,'messages':[]})


def test_overall_deadline_terminates_only_owned_transport(monkeypatch):
    def timeout(args,**kwargs):
        assert args[-1]=='--transport' and kwargs['timeout']==32
        assert 'shell' not in kwargs
        raise subprocess.TimeoutExpired(args,32)
    monkeypatch.setattr(adapter.subprocess,'run',timeout)
    with pytest.raises(TimeoutError):adapter.OllamaProvider(CONFIG).complete([])


def test_changed_digest_is_refused_before_generation(monkeypatch):
    calls=[]
    class Connection:
        def __init__(self,*a,**kw):pass
        def request(self,method,path):calls.append(path)
        def getresponse(self):return self
        status=200
        def read(self,limit):return json.dumps({'models':[{'name':CONFIG['model'],'digest':'b'*64}]}).encode()
        def close(self):pass
    monkeypatch.setattr('http.client.HTTPConnection',Connection)
    with pytest.raises(ValueError,match='model_changed'):adapter.transport({'config':CONFIG,'messages':[]})
    assert calls==['/api/tags']
