"""Single-process, bounded owner sessions. Restart/credential rotation revokes them."""
from dataclasses import dataclass
from hashlib import sha256
import hmac
import ipaddress
import os
import secrets
import threading
import time

from fastapi import HTTPException, Request

COOKIE = 'ai_company_owner'
TTL = 8 * 60 * 60
LIMIT = 32
LOCK = threading.Lock()


@dataclass(frozen=True)
class Session:
    csrf: str
    origin: str
    fingerprint: str
    expires: float
    local: bool = False


SESSIONS: dict[str, Session] = {}


def digest(value: str) -> str:
    return sha256(value.encode()).hexdigest()


def fingerprint() -> str:
    return digest(os.environ.get('OWNER_API_TOKEN', '')+'\0'+os.environ.get('WORKER_API_TOKEN', ''))


def local_access_check(request: Request):
    """Explicit workstation mode; trust actual ASGI socket addresses, never forwarding headers."""
    if os.environ.get('LOCAL_OWNER_ACCESS') != '1':
        raise HTTPException(403, 'Lokalny dostęp właściciela nie jest włączony.')
    if any(name == 'forwarded' or name.startswith('x-forwarded-') or name == 'x-real-ip'
           for name in request.headers):
        raise HTTPException(403, 'Lokalny dostęp wymaga bezpośredniego połączenia.')
    server = request.scope.get('server')
    try:
        direct = (request.client is not None and server is not None
                  and ipaddress.ip_address(request.client.host).is_loopback
                  and ipaddress.ip_address(server[0]).is_loopback
                  and request.url.hostname in {'localhost','127.0.0.1','::1'}
                  and (request.url.port or (443 if request.url.scheme=='https' else 80)) == server[1])
    except (ValueError, TypeError):
        direct = False
    if not direct:
        raise HTTPException(403, 'Ten tryb działa wyłącznie na komputerze właściciela.')


def origin_check(request: Request, *, mutation=False) -> str:
    origin = str(request.base_url).rstrip('/')
    if request.url.scheme != 'https' and not (
        request.url.scheme == 'http' and request.url.hostname in {'127.0.0.1', 'localhost', '::1'}
    ):
        raise HTTPException(403, 'Logowanie wymaga HTTPS; HTTP jest dostępne tylko lokalnie.')
    supplied = request.headers.get('origin')
    if (supplied is not None and supplied != origin) or (mutation and supplied != origin):
        raise HTTPException(403, 'Nieprawidłowe pochodzenie żądania.')
    if request.headers.get('x-owner-origin') != origin:
        raise HTTPException(403, 'Brak potwierdzenia pochodzenia panelu.')
    if request.headers.get('sec-fetch-site') not in {None, 'same-origin', 'none'}:
        raise HTTPException(403, 'Żądanie spoza panelu właściciela.')
    return origin


def create(request: Request, *, local=False) -> tuple[str, Session]:
    if local:
        local_access_check(request)
    origin = origin_check(request, mutation=True)
    now = time.time()
    session = Session(secrets.token_urlsafe(32), origin, fingerprint(), now+TTL, local)
    raw = secrets.token_urlsafe(32)
    with LOCK:
        for key, item in list(SESSIONS.items()):
            if item.expires <= now or item.fingerprint != session.fingerprint:
                del SESSIONS[key]
        old = digest(request.cookies.get(COOKIE, ''))
        SESSIONS.pop(old, None)
        if len(SESSIONS) >= LIMIT:
            raise HTTPException(429, 'Limit sesji właściciela. Wyloguj nieużywane urządzenie.')
        SESSIONS[digest(raw)] = session
    return raw, session


def validate(request: Request) -> Session:
    origin = origin_check(request, mutation=request.method not in {'GET', 'HEAD', 'OPTIONS'})
    raw = request.cookies.get(COOKIE, '')
    with LOCK:
        item = SESSIONS.get(digest(raw)) if len(raw) == 43 else None
        if not item or item.expires <= time.time() or item.fingerprint != fingerprint():
            if raw: SESSIONS.pop(digest(raw), None)
            raise HTTPException(401, 'Sesja właściciela wygasła. Zaloguj się ponownie.')
    if item.origin != origin:
        raise HTTPException(403, 'Sesja należy do innego adresu panelu.')
    if item.local:
        local_access_check(request)
    if request.method not in {'GET', 'HEAD', 'OPTIONS'} and not hmac.compare_digest(
        request.headers.get('x-owner-csrf', '').encode(), item.csrf.encode()
    ):
        raise HTTPException(403, 'Brak poprawnego potwierdzenia CSRF.')
    return item


def revoke(request: Request):
    validate(request)
    with LOCK:
        SESSIONS.pop(digest(request.cookies.get(COOKIE, '')), None)
