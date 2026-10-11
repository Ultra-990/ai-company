"""Opt-in production-path canary for bounded filewise application generation.

The pytest fixture supplies an isolated SQLite database. This wrapper never
changes config/local_inference.json and does nothing without --run.
"""
import argparse
import os
from pathlib import Path
import signal
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
WORKSPACE_ROOT=Path('/home/marcin/ai-company-workspaces')


def output_directory(value):
    path=Path(value)
    if (not path.is_absolute() or '..' in path.parts or path==WORKSPACE_ROOT
            or not path.is_relative_to(WORKSPACE_ROOT) or path.exists()
            or any(parent.is_symlink() for parent in path.parents)):
        raise argparse.ArgumentTypeError('output must be a new child of the workspace root')
    return path


def command(output):
    return [str(ROOT/'.venv/bin/pytest'),'-q',
        'tests/test_filewise_production_canary.py::test_real_filewise_production_path_canary','-s']


def main(argv=None):
    parser=argparse.ArgumentParser()
    parser.add_argument('--run',action='store_true')
    parser.add_argument('--output',type=output_directory,required=True)
    args=parser.parse_args(argv)
    if not args.run:parser.error('--run is required')
    args.output.mkdir(mode=0o700,parents=False,exist_ok=False)
    environment=os.environ.copy()
    environment['AIC_FILEWISE_PRODUCTION_CANARY']='1'
    environment['AIC_FILEWISE_PRODUCTION_CANARY_OUTPUT']=str(args.output)
    process=subprocess.Popen(command(args.output),cwd=ROOT,env=environment,start_new_session=True)
    try:return process.wait(timeout=900)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid,signal.SIGTERM)
        try:process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid,signal.SIGKILL);process.wait(timeout=5)
        return 124


if __name__=='__main__':sys.exit(main())
