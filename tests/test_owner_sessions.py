import time

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.api.auth import require_owner, require_worker
from app.api.owner_session import router
from app.api.system import get_audit_repository
from app.services import owner_sessions as sessions
from tests.conftest import OWNER_HEADERS, WORKER_HEADERS

ORIGIN = 'http://localhost'
ORIGIN_HEADERS = {'Origin': ORIGIN, 'X-Owner-Origin': ORIGIN, 'Sec-Fetch-Site': 'same-origin'}


@pytest.fixture
def browser():
    sessions.SESSIONS.clear()
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_audit_repository] = lambda: None

    @app.get('/api/protected', dependencies=[Depends(require_owner)])
    def protected(): return {'ok': True}

    @app.post('/api/protected', dependencies=[Depends(require_owner)])
    def mutate(): return {'ok': True}

    @app.get('/api/worker', dependencies=[Depends(require_worker)])
    def worker(): return {'ok': True}

    with TestClient(app, base_url=ORIGIN) as client:
        yield client
    sessions.SESSIONS.clear()


def login(browser):
    result = browser.post('/api/owner-session', headers=ORIGIN_HEADERS | OWNER_HEADERS)
    assert result.status_code == 200, result.text
    return result


def test_cookie_session_and_mutation_csrf(browser):
    result = login(browser)
    cookie = result.headers['set-cookie']
    assert 'HttpOnly' in cookie and 'SameSite=strict' in cookie and 'Path=/api' in cookie
    assert 'Domain=' not in cookie
    assert 'test-owner-token' not in cookie and 'test-owner-token' not in result.text
    assert browser.get('/api/owner-session', headers={'X-Owner-Origin': ORIGIN}).status_code == 200
    assert browser.get('/api/protected', headers=ORIGIN_HEADERS).status_code == 200
    assert browser.post('/api/protected', headers=ORIGIN_HEADERS).status_code == 403
    headers = ORIGIN_HEADERS | {'X-Owner-CSRF': result.json()['csrf']}
    assert browser.post('/api/protected', headers=headers).status_code == 200
    assert browser.get('/api/worker', headers=headers).status_code == 401
    assert browser.get('/api/protected', headers=headers | WORKER_HEADERS).status_code == 403
    assert browser.get('/api/protected', headers=headers | {'Authorization':'Bearer wrong'}).status_code == 401
    assert browser.get('/api/protected', headers=headers | {'Authorization':''}).status_code == 401


@pytest.mark.parametrize('changes', [{'Origin':'null'}, {'Origin':'http://evil.invalid'},
                                   {'X-Owner-Origin':'http://evil.invalid'},
                                   {'Sec-Fetch-Site':'cross-site'}, {'Sec-Fetch-Site':'same-site'}])
def test_untrusted_origin_rejected(browser, changes):
    login(browser)
    assert browser.get('/api/owner-session', headers=ORIGIN_HEADERS | changes).status_code == 403
    assert browser.post('/api/owner-session', headers=ORIGIN_HEADERS | OWNER_HEADERS | changes).status_code == 403


def test_login_needs_owner_and_origin(browser):
    assert browser.post('/api/owner-session', headers=ORIGIN_HEADERS).status_code == 401
    assert browser.post('/api/owner-session', headers=ORIGIN_HEADERS | WORKER_HEADERS).status_code == 403
    assert browser.post('/api/owner-session', headers=OWNER_HEADERS).status_code == 403
    result = login(browser)
    assert browser.post('/api/owner-session', headers=ORIGIN_HEADERS | {'X-Owner-CSRF':result.json()['csrf']}).status_code == 401


def test_logout_revokes_copied_cookie(browser):
    result = login(browser)
    raw = browser.cookies.get(sessions.COOKIE)
    headers = ORIGIN_HEADERS | {'X-Owner-CSRF':result.json()['csrf']}
    assert browser.delete('/api/owner-session', headers=ORIGIN_HEADERS).status_code == 403
    assert browser.delete('/api/owner-session', headers=headers).status_code == 200
    assert browser.get('/api/protected', headers=headers | {'Cookie':f'{sessions.COOKIE}={raw}'}).status_code == 401


def test_expiry_rotation_and_restart(browser, monkeypatch):
    login(browser)
    monkeypatch.setattr(sessions.time, 'time', lambda: 10**12)
    assert browser.get('/api/protected', headers=ORIGIN_HEADERS).status_code == 401
    monkeypatch.undo()
    login(browser)
    monkeypatch.setenv('OWNER_API_TOKEN', 'rotated-owner')
    assert browser.get('/api/protected', headers=ORIGIN_HEADERS).status_code == 401
    monkeypatch.undo()
    login(browser)
    sessions.SESSIONS.clear()
    assert browser.get('/api/protected', headers=ORIGIN_HEADERS).status_code == 401


def test_transport_and_limit(browser, monkeypatch):
    browser.base_url='http://remote.invalid'
    h={'Origin':'http://remote.invalid','X-Owner-Origin':'http://remote.invalid'} | OWNER_HEADERS
    assert browser.post('/api/owner-session', headers=h).status_code == 403
    browser.base_url='https://remote.invalid'
    h={'Origin':'https://remote.invalid','X-Owner-Origin':'https://remote.invalid'} | OWNER_HEADERS
    result=browser.post('/api/owner-session', headers=h)
    assert result.status_code == 200 and 'Secure' in result.headers['set-cookie']
    monkeypatch.setattr(sessions,'LIMIT',1)
    browser.cookies.clear()
    assert browser.post('/api/owner-session', headers=h).status_code == 429


def test_client_app_does_not_expose_owner_sessions():
    from app.client_main import app
    with TestClient(app) as client:
        assert client.get('/api/owner-session').status_code == 404
        assert client.get('/static/organization-os/owner-session.js').status_code == 404
