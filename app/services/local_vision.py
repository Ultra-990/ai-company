"""One bounded PNG to the existing pinned local Qwen; no URLs, paths or tools."""
import base64
import io
import json
from pathlib import Path
import subprocess
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from app.services.local_ollama import ROOT,configuration,transport,ModelFailure

MAX_IMAGE=4*1024*1024
MAX_PAYLOAD=6*1024*1024


def validate_payload(payload):
    config=payload['config'];expected=configuration()
    if config['model']!=expected['model'] or config['digest']!=expected['digest']:
        raise ValueError('Pinned vision model required')
    for key,low,high in [('num_ctx',2048,16384),('num_predict',32,2400),
                         ('num_thread',1,6),('timeout_seconds',10,180)]:
        if type(config[key]) is not int or not low<=config[key]<=high:raise ValueError('Vision limits')
    messages=payload['messages']
    if len(messages)!=2:raise ValueError('One system/user image request required')
    for message,role,keys in zip(messages,('system','user'),({'role','content'},{'role','content','images'})):
        if (set(message)!=keys or message['role']!=role or not isinstance(message['content'],str)
                or not 1<=len(message['content'])<=12000):raise ValueError('Invalid vision message')
    images=messages[1]['images']
    if not isinstance(images,list) or len(images)!=1 or not isinstance(images[0],str):raise ValueError('One PNG required')
    if len(images[0])>MAX_IMAGE*4//3+4:raise ValueError('Image too large')
    raw=base64.b64decode(images[0],validate=True)
    if not 0<len(raw)<=MAX_IMAGE:raise ValueError('Image too large')
    from PIL import Image
    with Image.open(io.BytesIO(raw)) as img:
        if img.format!='PNG' or not(128<=img.width<=1536 and 128<=img.height<=1536) or img.width*img.height>1024*1024:
            raise ValueError('Bounded PNG required')
        img.verify()


def complete(config,system,user,image):
    payload={'config':config,'messages':[{'role':'system','content':system},
             {'role':'user','content':user,'images':[base64.b64encode(image).decode('ascii')]}]}
    validate_payload(payload)
    serialized=json.dumps(payload)
    if len(serialized.encode())>MAX_PAYLOAD:raise ValueError('Vision payload too large')
    try:
        result=subprocess.run([sys.executable,str(Path(__file__).resolve()),'--transport'],
            input=serialized,text=True,capture_output=True,cwd=ROOT,timeout=config['timeout_seconds']+2)
    except subprocess.TimeoutExpired as exc:raise TimeoutError('local_vision_deadline') from exc
    if result.returncode==124:raise TimeoutError('local_vision_deadline')
    if result.returncode:raise ModelFailure('local_vision_failed')
    return json.loads(result.stdout)


if __name__=='__main__':
    try:
        raw=sys.stdin.buffer.read(MAX_PAYLOAD+1)
        if len(raw)>MAX_PAYLOAD:raise ValueError('Oversized vision request')
        payload=json.loads(raw);validate_payload(payload)
        print(json.dumps(transport(payload)))
    except TimeoutError:sys.exit(124)
    except Exception:
        print(json.dumps({'error':'local_vision_failed'}));sys.exit(1)
