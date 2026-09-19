"""Explicit cache release only when ComfyUI queue is empty; no process termination."""
import argparse
import http.client
import json
from pathlib import Path
import sys
import time
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.services.comfyui_provider import ComfyProvider


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', action='store_true')
    if not parser.parse_args().run:
        print('No cache release. Use --run only between GPU jobs.'); return
    provider = ComfyProvider()
    queue = provider.request('/queue')
    if queue.get('queue_running') != [] or queue.get('queue_pending') != []:
        raise RuntimeError('ComfyUI is busy; no cache released')
    conn = http.client.HTTPConnection('127.0.0.1', 8188, timeout=5)
    try:
        conn.request('POST', '/free', json.dumps({'unload_models':True, 'free_memory':True}), {'Content-Type':'application/json'})
        response = conn.getresponse(); response.read(4096)
        if response.status != 200: raise RuntimeError('Cache release not confirmed')
    finally: conn.close()
    # Request acknowledgement is not proof that CUDA memory has been released.
    time.sleep(2)
    stats = provider.request('/system_stats')
    print(json.dumps({'cache_release_requested':True, 'devices':stats['devices'], 'process_stopped':False}))


if __name__ == '__main__': main()
