"""Owner-only browser authentication; not registered on the client ASGI app."""
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse

from app.api.auth import require_owner
from app.services import owner_sessions as sessions

router = APIRouter(prefix='/api/owner-session', tags=['owner-session'])
HEADERS = {'Cache-Control': 'no-store', 'Referrer-Policy': 'no-referrer'}


def session_response(request, raw, item):
    response = JSONResponse({'authenticated': True, 'csrf': item.csrf,
                             'expires_at': item.expires, 'mode':'local' if item.local else 'token'}, headers=HEADERS)
    response.set_cookie(sessions.COOKIE, raw, max_age=sessions.TTL, path='/api',
                        httponly=True, secure=request.url.scheme == 'https', samesite='strict')
    return response


@router.post('/local')
def local_login(request: Request):
    # Creates an ordinary CSRF-protected session; does not bypass API authorization.
    if request.headers.get('authorization') is not None:
        raise HTTPException(400, 'Lokalny panel nie wymaga tokena.')
    raw, item = sessions.create(request, local=True)
    return session_response(request, raw, item)


@router.post('')
def login(request: Request, _: None = Depends(require_owner)):
    # A cookie cannot extend its own absolute lifetime or mint new sessions.
    if not request.headers.get('authorization'):
        raise HTTPException(401, 'Do logowania wymagany jest token właściciela.')
    raw, item = sessions.create(request)
    return session_response(request, raw, item)


@router.get('')
def status(request: Request, _: None = Depends(require_owner)):
    item = sessions.validate(request)
    return JSONResponse({'authenticated': True, 'csrf': item.csrf,
                         'expires_at': item.expires, 'mode':'local' if item.local else 'token'}, headers=HEADERS)


@router.delete('')
def logout(request: Request, _: None = Depends(require_owner)):
    sessions.revoke(request)
    response = JSONResponse({'authenticated': False}, headers=HEADERS)
    response.delete_cookie(sessions.COOKIE, path='/api', httponly=True,
                           secure=request.url.scheme == 'https', samesite='strict')
    return response
