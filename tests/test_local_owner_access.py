"""Automatic workstation login still requires direct loopback, origin and CSRF."""
import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from app.api.auth import require_owner, require_worker
from app.api.owner_session import router
from app.api.system import get_audit_repository
from app.services import owner_sessions as sessions

ORIGIN='http://127.0.0.1:8000'
HEADERS={'Origin':ORIGIN,'X-Owner-Origin':ORIGIN,'Sec-Fetch-Site':'same-origin'}


@pytest.fixture
def local_app(monkeypatch):
    monkeypatch.setenv('LOCAL_OWNER_ACCESS','1')
    sessions.SESSIONS.clear()
    app=FastAPI();app.include_router(router)
    app.dependency_overrides[get_audit_repository]=lambda:None
    @app.get('/api/protected',dependencies=[Depends(require_owner)])
    def read():return {'ok':True}
    @app.post('/api/protected',dependencies=[Depends(require_owner)])
    def write():return {'ok':True}
    @app.get('/api/worker',dependencies=[Depends(require_worker)])
    def worker():return {'ok':True}
    yield app
    sessions.SESSIONS.clear()


def browser(app,peer='127.0.0.1',origin=ORIGIN):
    return TestClient(app,base_url=origin,client=(peer,43210))


def test_local_session_no_token_and_csrf_still_required(local_app):
    with browser(local_app) as c:
        assert c.get('/api/protected',headers=HEADERS).status_code==401
        r=c.post('/api/owner-session/local',headers=HEADERS)
        assert r.status_code==200 and r.json()['mode']=='local'
        assert 'HttpOnly' in r.headers['set-cookie'] and 'SameSite=strict' in r.headers['set-cookie']
        assert 'test-owner-token' not in r.text and 'test-worker-token' not in r.text
        assert c.get('/api/protected',headers=HEADERS).status_code==200
        assert c.post('/api/protected',headers=HEADERS).status_code==403
        h=HEADERS|{'X-Owner-CSRF':r.json()['csrf']}
        assert c.post('/api/protected',headers=h).status_code==200
        assert c.get('/api/worker',headers=h).status_code==401
        assert c.get('/api/protected',headers=h|{'Authorization':'Bearer wrong'}).status_code==401
        assert c.get('/api/owner-session',headers=HEADERS).json()['mode']=='local'


@pytest.mark.parametrize('changes',[
    {'Origin':'http://evil.invalid'},{'Origin':'null'},{'X-Owner-Origin':'http://evil.invalid'},
    {'Sec-Fetch-Site':'cross-site'},{'Sec-Fetch-Site':'same-site'},
    {'X-Forwarded-For':'127.0.0.1'},{'Forwarded':'for=127.0.0.1'},
    {'X-Forwarded-Host':'127.0.0.1'},{'X-Real-IP':'127.0.0.1'},
    {'Host':'evil.invalid:8000'},{'Host':'127.0.0.1:9999'},
])
def test_untrusted_requests_cannot_bootstrap(local_app,changes):
    with browser(local_app) as c:
        assert c.post('/api/owner-session/local',headers=HEADERS|changes).status_code==403
        assert not sessions.SESSIONS


@pytest.mark.parametrize('peer',['10.0.0.58','203.0.113.4','::ffff:10.0.0.58'])
def test_remote_peer_cannot_claim_local_host(local_app,peer):
    with browser(local_app,peer=peer) as c:
        assert c.post('/api/owner-session/local',headers=HEADERS).status_code==403


def test_missing_origin_mode_disabled_and_client_boundary(local_app,monkeypatch):
    with browser(local_app) as c:
        assert c.post('/api/owner-session/local').status_code==403
        monkeypatch.delenv('LOCAL_OWNER_ACCESS')
        assert c.post('/api/owner-session/local',headers=HEADERS).status_code==403
    from app.client_main import app
    with TestClient(app) as c:
        assert c.post('/api/owner-session/local',headers=HEADERS).status_code==404


def test_local_cookie_cannot_move_to_remote_peer_or_survive_disabled_mode(local_app,monkeypatch):
    with browser(local_app) as c:
        assert c.post('/api/owner-session/local',headers=HEADERS).status_code==200
        raw=c.cookies.get(sessions.COOKIE)
        with browser(local_app,peer='10.0.0.58') as remote:
            assert remote.get('/api/protected',headers=HEADERS|{'Cookie':sessions.COOKIE+'='+raw}).status_code==403
        monkeypatch.setenv('LOCAL_OWNER_ACCESS','0')
        assert c.get('/api/protected',headers=HEADERS).status_code==403


def test_local_expiry_and_logout_can_reopen_without_a_token(local_app,monkeypatch):
    with browser(local_app) as c:
        r=c.post('/api/owner-session/local',headers=HEADERS)
        assert c.delete('/api/owner-session',headers=HEADERS|{'X-Owner-CSRF':r.json()['csrf']}).status_code==200
        assert c.post('/api/owner-session/local',headers=HEADERS).status_code==200
        monkeypatch.setattr(sessions.time,'time',lambda:10**12)
        assert c.get('/api/protected',headers=HEADERS).status_code==401
        assert c.post('/api/owner-session/local',headers=HEADERS).status_code==200
