"""Fixed Docker profile. No caller commands, paths, images or Docker socket in guest."""
import fcntl
import json
import os
from pathlib import Path
import selectors
import subprocess
import tempfile
import time
import re
from uuid import uuid4
from hashlib import sha256

ROOT=Path(__file__).resolve().parents[2]
WORK=Path('/home/marcin/ai-company-workspaces/runner')
CONFIG=ROOT/'config/package_runner.json'
HARNESS=ROOT/'app/runner/harness.py'
IMAGE='sha256:bef522938ef068e9fe7c1f078b1eb929cf32bbb2047b8e67723996c1e050e6e9'
DOCKER='/usr/bin/docker'
LABEL='ai-company.package-runner'
PROFILE='python-web-v1'


def configuration():
    from app.core.config import load_settings
    if load_settings().safety.emergency_stop:raise ValueError('Emergency Stop: runner wyłączony.')
    try:data=json.loads(CONFIG.read_text())
    except (OSError,ValueError) as exc:raise ValueError('Brak konfiguracji runnera.') from exc
    if data.get('enabled') is not True or data.get('image')!=IMAGE:raise ValueError('Profil runnera jest wyłączony lub obraz zmieniony.')
    return {'profile':PROFILE,'image':IMAGE,'harness_checksum':sha256(HARNESS.read_bytes()).hexdigest(),
            'timeout_seconds':45,'memory_bytes':536870912,'cpus':1,'pids':64,'network':'none'}


def docker(*args,timeout=10):
    # Force the local engine; never use a context/remote DOCKER_HOST or credentials.
    return subprocess.run([DOCKER,'--host','unix:///var/run/docker.sock',*args],
        env={'PATH':'/usr/bin:/bin','LANG':'C.UTF-8'},capture_output=True,text=True,timeout=timeout,check=False)


def create_args(name,directory,config):
    return ['create','--pull=never','--name',name,'--label',f'{LABEL}={name}',
        '--runtime=runc','--network=none','--read-only','--user','65534:65534',
        '--cap-drop=ALL','--security-opt=no-new-privileges:true','--security-opt=apparmor=docker-default',
        '--pids-limit=64','--memory=512m','--memory-swap=512m','--cpus=1',
        '--ulimit','nofile=128:128','--ulimit','fsize=16777216:16777216','--ulimit','core=0:0',
        '--ipc=none','--log-driver=none','--stop-timeout=1',
        '--tmpfs','/tmp:rw,noexec,nosuid,nodev,size=32m,mode=1777',
        '--mount',f'type=bind,source={directory},target=/workspace,readonly',
        '--workdir','/workspace','--env','HOST=127.0.0.1','--env','PORT=8080',
        '--entrypoint','/usr/local/bin/python',config['image'],
        '-I','-S','-B','/workspace/runner_harness.py']


def bounded_start(container):
    process=subprocess.Popen([DOCKER,'--host','unix:///var/run/docker.sock','start','--attach',container],
        env={'PATH':'/usr/bin:/bin','LANG':'C.UTF-8'},stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    data=bytearray();deadline=time.monotonic()+45;reason=None
    try:
        with selectors.DefaultSelector() as selector:
            selector.register(process.stdout,selectors.EVENT_READ)
            while selector.get_map():
                if time.monotonic()>deadline:reason='timeout';break
                for key,_ in selector.select(.2):
                    chunk=os.read(key.fd,4096)
                    if not chunk:selector.unregister(key.fileobj);continue
                    if len(data)+len(chunk)>32768:reason='log_limit';break
                    data.extend(chunk)
                if reason:break
        if reason:
            process.kill();process.wait(timeout=2)
        else:process.wait(timeout=2)
        return {'cli_exit_code':process.returncode,'log':data.decode('utf-8',errors='replace'),'reason':reason}
    finally:
        if process.poll() is None:process.kill();process.wait(timeout=2)
        process.stdout.close()


class ContainerRunner:
    def __init__(self, harness=HARNESS):
        # Set only by trusted server code, never from an API payload.
        self.harness = harness

    def stage_sources(self, folder, files):
        # The production profile stays flat. Broader staging is a separate,
        # trusted pilot implementation, never selected by an API payload.
        for path,source in files.items():
            if Path(path).name!=path or path=='runner_harness.py':raise ValueError('Nieprawidłowy plik runnera.')
            (folder/path).write_text(source,encoding='utf-8');(folder/path).chmod(0o444)

    def cleanup(self,name):
        if not re.fullmatch(r'aic-package-[0-9a-f]{32}',name):raise ValueError('Nieprawidłowa tożsamość kontenera.')
        checked=docker('inspect','--format','{{json .Config.Labels}}',name)
        if checked.returncode==0 and json.loads(checked.stdout).get(LABEL)==name:
            return docker('rm','--force',name).returncode==0
        return checked.returncode!=0 and 'No such' in checked.stderr

    def run(self,files,config,name):
        if not re.fullmatch(r'aic-package-[0-9a-f]{32}',name):raise ValueError('Nieprawidłowa tożsamość kontenera.')
        # All ancestors must be real directories on the Linux /home filesystem.
        for parent in [*reversed(WORK.parents),WORK]:
            if parent.is_symlink():raise ValueError('Dowiązanie w ścieżce runnera.')
        WORK.mkdir(mode=0o700,parents=True,exist_ok=True)
        if WORK.stat().st_dev!=Path('/home').stat().st_dev or WORK.stat().st_uid!=os.geteuid() or WORK.stat().st_mode&0o077:
            raise ValueError('Runner wymaga prywatnego katalogu na dysku Linux.')
        with open(WORK/'slot.lock','a') as lock:
            try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BlockingIOError as exc:raise ValueError('Slot kontenera jest zajęty.') from exc
            return self._run(files,config,name)

    def _run(self,files,config,name):
        info=docker('info','--format','{{json .SecurityOptions}}')
        if info.returncode or 'name=seccomp,profile=builtin' not in info.stdout or 'name=apparmor' not in info.stdout:
            raise ValueError('Wymagane działające Docker, seccomp i AppArmor.')
        inspected=docker('image','inspect',config['image'],'--format','{{.Id}} {{json .Config.Volumes}}')
        if inspected.returncode or inspected.stdout.strip()!=config['image']+' null':
            raise ValueError('Brak przypiętego obrazu bez wolumenów. Nie pobrano zamiennika.')
        if sha256(self.harness.read_bytes()).hexdigest()!=config['harness_checksum']:
            raise ValueError('Tester zmienił się przed wykonaniem.')
        output={'container_name':name,'profile':config,'cleanup_confirmed':False,'exit_code':None,
                'cli_exit_code':None,'log':'','reason':None}
        with tempfile.TemporaryDirectory(prefix='source-',dir=WORK) as directory:
            folder=Path(directory)
            self.stage_sources(folder, files)
            (folder/'runner_harness.py').write_bytes(self.harness.read_bytes())
            (folder/'runner_harness.py').chmod(0o444);folder.chmod(0o755)
            try:
                created=docker(*create_args(name,directory,config))
                if created.returncode:raise ValueError('Nie udało się utworzyć izolowanego kontenera.')
                output.update(bounded_start(name))
                state=docker('inspect','--format','{{json .State}}',name)
                if state.returncode==0:
                    state=json.loads(state.stdout)
                    if state.get('Status')=='exited':output['exit_code']=state.get('ExitCode')
                    output['oom_killed']=state.get('OOMKilled',False)
            except Exception as exc:
                output['reason']='runner_'+type(exc).__name__
            finally:
                # Exact random identity + label; NEVER touch other containers.
                try:output['cleanup_confirmed']=self.cleanup(name)
                except Exception:output['cleanup_confirmed']=False
                if output['reason']=='runner_TimeoutExpired':output['cleanup_confirmed']=False
            return output
