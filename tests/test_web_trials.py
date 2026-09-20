"""Read-only trial transport: bytes, range handling, host boundary and archives."""
from hashlib import sha256
import http.client
import io
import json
from pathlib import Path
import threading
from http.server import ThreadingHTTPServer
from zipfile import ZipFile

import pytest
from scripts.web_trials.serve import read_files, range_bytes, handler, SITES

@pytest.mark.parametrize('header,want',[(None,None),('bytes=0-3',(0,3)),('bytes=8-',(8,9)),('bytes=-4',(6,9)),('bytes=2-99',(2,9)),('bytes=-99',(0,9))])
def test_bounded_ranges(header,want):assert range_bytes(header,10)==want

@pytest.mark.parametrize('header',['bytes=10-','bytes=5-2','bytes=-0','bytes=-','bytes=0-1,3-4','items=0-3','bytes=NaN-3'])
def test_invalid_ranges(header):
    with pytest.raises(ValueError):range_bytes(header,10)

@pytest.fixture
def packages(tmp_path):
    for site in SITES:
        folder=tmp_path/site;folder.mkdir();(folder/'assets').mkdir()
        files={'index.html':b'<!doctype html><h1>Test</h1>','assets/audio.mp3':b'0123456789'}
        for name,raw in files.items():(folder/name).write_bytes(raw)
        (folder/'manifest.json').write_text(json.dumps({'files':{n:sha256(v).hexdigest() for n,v in files.items()},'accepted':False}))
        (folder/'README.md').write_text('Synthetic demo')
    return tmp_path

def test_inventory_zip_and_tampering(packages):
    files,_=read_files(packages)
    assert read_files(packages)[0]['/downloads/music.zip']==files['/downloads/music.zip']
    with ZipFile(io.BytesIO(files['/downloads/music.zip'][0])) as z:
        assert z.read('assets/audio.mp3')==b'0123456789'
        assert json.loads(z.read('manifest.json'))['accepted'] is False
        assert 'proposal.json' not in z.namelist()
        assert all(info.date_time==(1980,1,1,0,0,0) for info in z.infolist())
    (packages/'music/assets/audio.mp3').write_bytes(b'changed')
    with pytest.raises(ValueError,match='Changed'):read_files(packages)

def test_host_csp_range_and_no_private_routes(packages):
    files,_=read_files(packages);server=ThreadingHTTPServer(('127.0.0.1',0),http.client.HTTPConnection)
    host=f'127.0.0.1:{server.server_port}';server.RequestHandlerClass=handler(files,host)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    def get(path,method='GET',headers=None):
        c=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=3)
        try:c.request(method,path,headers=headers or {});r=c.getresponse();return r.status,r.read(),dict(r.getheaders())
        finally:c.close()
    try:
        code,raw,headers=get('/music/index.html');assert code==200
        assert 'sandbox allow-scripts allow-forms allow-downloads;' in headers['Content-Security-Policy']
        assert "connect-src 'none'" in headers['Content-Security-Policy']
        code,raw,headers=get('/music/assets/audio.mp3',headers={'Range':'bytes=2-4'})
        assert code==206 and raw==b'234' and headers['Content-Range']=='bytes 2-4/10'
        assert get('/music/assets/audio.mp3',headers={'Range':'bytes=99-'})[0]==416
        code,raw,headers=get('/music/assets/audio.mp3',method='HEAD');assert code==200 and raw==b'' and headers['Content-Length']=='10'
        assert get('/music',headers={'Host':'foreign.invalid'})[0]==421
        for path in ['/evidence/media-provenance.json','/music/proposal.json','/../etc/passwd','/api/tasks','/music/index.html?x=1']:
            assert get(path)[0]==404
        assert get('/music',method='POST')[0]==405
    finally:server.shutdown();server.server_close();thread.join(timeout=2)
