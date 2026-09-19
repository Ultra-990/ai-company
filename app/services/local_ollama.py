"""Bounded Ollama text adapter. Fixed loopback endpoint, no tools or redirects."""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / 'config/local_inference.json'
ENDPOINT = 'http://127.0.0.1:11434'

ERROR_CODES={'model_inventory','model_changed','model_http_error','invalid_stream',
             'unsupported_model_output','invalid_text','output_limit','truncated_output','empty_output','invalid_generation_profile'}

# Server-side named profiles, never arbitrary options supplied by task text.
SAMPLING_PROFILES = {
    'gemma4-default.v1': {'temperature': 1.0, 'top_p': 0.95, 'top_k': 64},
    'bounded-default.v1': {'temperature': 0.2},
    'qwen-general-trial.v1': {'temperature': 0.7, 'top_p': 0.8, 'top_k': 20,
                            'min_p': 0.0, 'presence_penalty': 1.5, 'repeat_penalty': 1.0},
}


def generation_options(config):
    profile=config.get('sampling_profile','bounded-default.v1')
    if profile not in SAMPLING_PROFILES:
        raise ValueError('invalid_generation_profile')
    return {**{k:config[k] for k in ('num_ctx','num_predict','num_thread')},
            **SAMPLING_PROFILES[profile]}


def output_format(config):
    value=config.get('format')
    if value is None or value=='json':return value
    if not isinstance(value,dict) or len(json.dumps(value))>16000:
        raise ValueError('invalid_generation_profile')
    # Only internal references; schemas never resolve remote resources.
    def visit(item):
        if isinstance(item,dict):
            if '$ref' in item and (not isinstance(item['$ref'],str) or not item['$ref'].startswith('#/')):
                raise ValueError('invalid_generation_profile')
            for child in item.values():visit(child)
        elif isinstance(item,list):
            for child in item:visit(child)
    visit(value)
    return value


class ModelFailure(ValueError):
    def __init__(self,code):
        self.code=code if code in ERROR_CODES else 'local_model_transport_failed'
        super().__init__(self.code)


def configuration():
    try:
        data = json.loads(CONFIG_PATH.read_text(encoding='utf-8'))
        if data.get('enabled') is not True:
            raise ValueError('disabled')
        if data['model'] != 'qwen3.8:27b' or len(data['digest']) != 64 or any(c not in '0123456789abcdef' for c in data['digest']):
            raise ValueError('model')
        for key, low, high in [('timeout_seconds',10,180),('num_ctx',2048,16384),
                               ('num_predict',32,4096),('num_thread',1,8)]:
            if type(data[key]) is not int or not low <= data[key] <= high:
                raise ValueError('limits')
        generation_options(data)
        return data
    except (OSError, KeyError, TypeError, ValueError) as exc:
        raise ValueError('Lokalny model nie jest włączony lub konfiguracja wymaga poprawy.') from exc


def ensure_idle():
    """Conservative recovery check: no loaded models; never stops Ollama."""
    import http.client
    connection=http.client.HTTPConnection('127.0.0.1',11434,timeout=5)
    try:
        connection.request('GET','/api/ps');response=connection.getresponse();raw=response.read(1048577)
        if response.status!=200 or len(raw)>1048576 or json.loads(raw).get('models')!=[]:
            raise ValueError('Ollama nie potwierdza pustego stanu modeli. Nie zwolniono slotu.')
    except (OSError,ValueError) as exc:
        raise ValueError('Nie potwierdzono bezczynności Ollamy. Nie ponowiono zadania.') from exc
    finally:connection.close()


class OllamaProvider:
    def __init__(self, config):
        self.config = dict(config)

    def complete(self, messages):
        # A separate, owned transport process makes the overall client deadline
        # enforceable even when a server stalls between chunks. No user code.
        payload = {'config': self.config, 'messages': messages}
        try:
            result = subprocess.run([sys.executable, str(Path(__file__).resolve()), '--transport'],
                input=json.dumps(payload), text=True, capture_output=True,
                timeout=self.config['timeout_seconds']+2, check=False,
                cwd=ROOT)
        except subprocess.TimeoutExpired as exc:
            raise TimeoutError('local_model_deadline') from exc
        if result.returncode == 124:
            raise TimeoutError('local_model_deadline')
        if result.returncode != 0:
            try:code=json.loads(result.stdout).get('error')
            except ValueError:code=None
            raise ModelFailure(code)
        try:
            return json.loads(result.stdout)
        except ValueError as exc:
            raise ValueError('local_model_invalid_response') from exc


def transport(payload):
    import http.client
    import time
    config, messages = payload['config'], payload['messages']
    options=generation_options(config)
    schema=output_format(config)
    # No environment proxy, DNS, redirects, API key or arbitrary destination.
    start = time.monotonic()
    connection = http.client.HTTPConnection('127.0.0.1', 11434, timeout=config['timeout_seconds'])
    try:
        connection.request('GET','/api/tags')
        response = connection.getresponse()
        raw = response.read(1024*1024+1)
        if response.status != 200 or len(raw)>1024*1024:
            raise ValueError('model_inventory')
        models = json.loads(raw)['models']
        model = next((m for m in models if m.get('name') == config['model']), None)
        if not model or model.get('digest') != config['digest']:
            raise ValueError('model_changed')
        request = {'model':config['model'], 'messages':messages, 'stream':True,
                   'think':False, 'keep_alive':0,
                   'options':options}
        if schema is not None:request['format']=schema
        connection.request('POST','/api/chat',body=json.dumps(request).encode(),headers={'Content-Type':'application/json'})
        response = connection.getresponse()
        if response.status != 200:
            raise ValueError('model_http_error')
        text_parts=[]; size=0; total_bytes=0
        while True:
            if time.monotonic()-start>config['timeout_seconds']:
                raise TimeoutError('local_model_deadline')
            line=response.readline(65537);total_bytes+=len(line)
            if not line or len(line)>65536 or total_bytes>1024*1024:
                raise ValueError('invalid_stream')
            chunk=json.loads(line)
            if chunk.get('error') or chunk.get('message',{}).get('tool_calls'):
                raise ValueError('unsupported_model_output')
            content=chunk.get('message',{}).get('content','')
            if not isinstance(content,str):raise ValueError('invalid_text')
            text_parts.append(content);size+=len(content)
            if size>32000:raise ValueError('output_limit')
            if chunk.get('done') is True:
                if chunk.get('done_reason') != 'stop':raise ValueError('truncated_output')
                text=''.join(text_parts).strip()
                if not text or '\x00' in text:raise ValueError('empty_output')
                return {'content':text,'model':config['model'],'digest':config['digest'],
                        'elapsed_seconds':round(time.monotonic()-start,3),
                        'eval_count':chunk.get('eval_count'), 'prompt_eval_count':chunk.get('prompt_eval_count'),
                        'done_reason':'stop'}
    finally:
        connection.close()


if __name__ == '__main__':
    try:
        payload=json.loads(sys.stdin.read(256000))
        print(json.dumps(transport(payload)))
    except TimeoutError:
        sys.exit(124)
    except ValueError as exc:
        code=str(exc)
        print(json.dumps({'error':code if code in ERROR_CODES else 'local_model_transport_failed'}))
        sys.exit(1)
    except Exception:
        # Do not echo model input, prompts, HTTP bodies or exceptions to logs.
        sys.exit(1)
