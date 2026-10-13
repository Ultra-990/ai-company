"""Bounded CPU-only four-stem separation using a pinned Demucs runtime."""
from __future__ import annotations
from pathlib import Path
import hashlib, json, os, shutil, subprocess, tempfile
from typing import Callable

MODEL = "htdemucs"
STEMS = ("vocals", "drums", "bass", "other")
RUNTIME = Path("/home/marcin/ai-company-workspaces/demucs-runtime")
PYTHON = Path("/home/marcin/ai-company-workspaces/comfyui/venv/bin/python")
PYDEPS = RUNTIME / "pydeps"
MODEL_FILE = RUNTIME / "models-cache/hub/checkpoints/955717e8-8726e21a.th"
MODEL_SHA256 = "8726e21a993978c7ba086d3872e7608d7d5bfca646ca4aca459ffda844faa8b4"
MAX_SOURCE = 512 * 1024 * 1024


class StemError(ValueError): pass


def _atomic_json(path: Path, value: dict):
    tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2));tmp.chmod(0o600);tmp.replace(path)


def _probe(path: Path, run: Callable[..., subprocess.CompletedProcess], maximum: float = 60.5) -> dict:
    try:
        p=run(["ffprobe","-v","error","-protocol_whitelist","file,pipe","-show_entries",
            "format=duration:stream=codec_type,sample_rate,channels","-of","json",str(path)],
            capture_output=True,text=True,timeout=20,check=False)
        d=json.loads(p.stdout) if p.returncode==0 else None; duration=float(d['format']['duration']); streams=d['streams']
    except subprocess.TimeoutExpired as exc: raise StemError('stems_probe_timeout') from exc
    except (KeyError,TypeError,ValueError,json.JSONDecodeError) as exc: raise StemError('stems_probe_invalid') from exc
    audio=[x for x in streams if x.get('codec_type')=='audio']
    if len(streams)!=1 or len(audio)!=1 or not 0<duration<=maximum: raise StemError('stems_audio_invalid')
    return {'duration_seconds':duration,'sample_rate':audio[0].get('sample_rate'),'channels':audio[0].get('channels')}


def runtime_preflight() -> dict:
    code=(PYDEPS/'demucs').is_dir() and PYTHON.is_file(); model=MODEL_FILE.is_file()
    digest=hashlib.sha256(MODEL_FILE.read_bytes()).hexdigest() if model else None
    return {'runtime_ready':code,'model_present':model,'model_sha256':digest,'ready':code and model and digest==MODEL_SHA256,
            'model':MODEL,'device':'cpu','stems':list(STEMS)}


def separate_stems(source: Path, output_dir: Path,
        run: Callable[..., subprocess.CompletedProcess]=subprocess.run, timeout_seconds: int=900,
        *, lossless: bool=False, maximum_seconds: float=60.5) -> dict:
    """Paths are resolved by the authenticated orchestration layer, never request fields."""
    if source.is_symlink(): raise StemError('stems_source_invalid')
    source=source.resolve()
    if not source.is_file() or source.suffix.lower() not in {'.mp3','.wav','.flac'} or source.stat().st_size>MAX_SOURCE:
        raise StemError('stems_source_invalid')
    if output_dir.is_symlink() or (output_dir.exists() and not output_dir.is_dir()): raise StemError('stems_output_invalid')
    if not output_dir.exists(): output_dir.mkdir(parents=True,mode=0o700)
    if not 0<maximum_seconds<=900.1:raise StemError('stems_duration_limit_invalid')
    output_dir=output_dir.resolve(); probe=_probe(source,run,maximum_seconds); preflight=runtime_preflight()
    if not preflight['ready']: raise StemError('stems_runtime_not_ready')
    receipt_path=output_dir/'stems-report.json'
    if receipt_path.exists(): raise StemError('stems_receipt_exists')
    receipt={'schema':'music-stems.v1','status':'prepared','model':MODEL,'device':'cpu','source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
        'source_probe':probe,'stems':{},'limitations':['source separation may contain bleed','other includes melodic material and remaining mix'],
        'owner_accepted':False,'published':False}
    _atomic_json(receipt_path,receipt); temp=Path(tempfile.mkdtemp(prefix='.stems-',dir=output_dir))
    env={k:v for k,v in os.environ.items() if k not in {'PYTHONPATH','CUDA_VISIBLE_DEVICES'}}
    env.update({'PYTHONPATH':str(PYDEPS),'CUDA_VISIBLE_DEVICES':'','OMP_NUM_THREADS':'2','MKL_NUM_THREADS':'2','OPENBLAS_NUM_THREADS':'2',
                'TORCH_HOME':str(RUNTIME/'models-cache')})
    entry=[str(Path(__file__).resolve().parents[2]/'scripts/demucs_wav.py')] if lossless else ['-m','demucs.separate']
    command=[str(PYTHON),*entry,'-n',MODEL,'-d','cpu','-j','1','--shifts','1','--overlap','0.25','--segment','7']
    command+=['--clip-mode','clamp'] if lossless else ['--mp3','--mp3-bitrate','320']
    command+=['-o',str(temp),str(source)]
    extension='.wav' if lossless else '.mp3'
    try:
        receipt['status']='running';_atomic_json(receipt_path,receipt)
        try: result=run(command,capture_output=True,timeout=timeout_seconds,check=False,env=env)
        except subprocess.TimeoutExpired as exc:
            receipt.update(status='failed',error_type='TimeoutExpired');raise StemError('stems_timeout') from exc
        if result.returncode:
            error=result.stderr if isinstance(result.stderr,str) else result.stderr.decode('utf-8','replace')
            diagnostic=output_dir/'worker-error.log';diagnostic.write_text(error[-8000:]);diagnostic.chmod(0o600)
            receipt.update(status='failed',error_type='DemucsFailure');raise StemError('stems_failed')
        track=temp/MODEL/source.stem
        for name in STEMS:
            candidate=track/(name+extension)
            if not candidate.is_file(): receipt.update(status='failed',error_type='MissingStem');raise StemError('stems_output_missing')
            measured=_probe(candidate,run,maximum_seconds)
            if abs(measured['duration_seconds']-probe['duration_seconds'])>.6:
                receipt.update(status='failed',error_type='DurationMismatch');raise StemError('stems_output_invalid')
            candidate.chmod(0o600); destination=output_dir/(name+extension)
            try: os.link(candidate,destination)
            except FileExistsError as exc: receipt.update(status='failed',error_type='OutputExists');raise StemError('stems_output_exists') from exc
            receipt['stems'][name]={'file':destination.name,'sha256':hashlib.sha256(destination.read_bytes()).hexdigest(),
                                  'size_bytes':destination.stat().st_size,'format':extension[1:].upper(),**measured}
        receipt['status']='completed_unreviewed';return receipt
    except Exception as exc:
        if receipt['status'] in {'prepared','running'}:receipt.update(status='failed',error_type=type(exc).__name__)
        raise
    finally:
        shutil.rmtree(temp,ignore_errors=True);_atomic_json(receipt_path,receipt)
