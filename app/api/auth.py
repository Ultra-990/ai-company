from __future__ import annotations

import hmac
import os
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request

from app.api.system import get_audit_repository
from app.services.audit import AuditRepository


AUTHORIZATION_EVENT_TYPE = "api_authorization"


def _record_authorization_event(
    repository: AuditRepository,
    *,
    required_role: str,
    decision: str,
    allowed: bool,
    reason: str,
) -> None:
    """
    Zapisuje minimalne zdarzenie RBAC.

    Nigdy nie przekazujemy tu nagłówka Authorization ani tokenu. Audyt
    autoryzacji nie może wpływać na decyzję bezpieczeństwa ani odpowiedź API.
    """
    try:
        repository.record(
            event_type=AUTHORIZATION_EVENT_TYPE,
            operation=required_role,
            decision=decision,
            allowed=allowed,
            reason=reason,
        )
    except Exception:
        # Uwierzytelnianie musi nadal zwrócić właściwe 401/403, nawet gdy
        # magazyn audytu jest chwilowo niedostępny.
        pass


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=401,
        detail="Brakujący lub nieprawidłowy token API",
        headers={"WWW-Authenticate": "Bearer"},
    )


def _forbidden() -> HTTPException:
    return HTTPException(
        status_code=403,
        detail="Token API nie ma wymaganych uprawnień",
    )


def _misconfigured() -> HTTPException:
    return HTTPException(
        status_code=503,
        detail="Wymagany token API nie jest skonfigurowany",
    )


def _require_role(
    *,
    request: Request,
    authorization: str | None,
    repository: AuditRepository,
    required_role: str,
    required_token_name: str,
    other_token_name: str,
) -> None:
    required_token = os.environ.get(required_token_name)
    other_token = os.environ.get(other_token_name)

    if not required_token:
        raise _misconfigured()

    if other_token and hmac.compare_digest(required_token, other_token):
        raise HTTPException(
            status_code=503,
            detail="Tokeny Owner i Worker muszą być różne",
        )

    if not authorization:
        if authorization is None and required_role == 'owner' and request.cookies.get('ai_company_owner'):
            from app.services.owner_sessions import validate
            validate(request)
            request.state.authenticated_role = required_role
            request.state.audit_repository = repository
            return
        _record_authorization_event(
            repository,
            required_role=required_role,
            decision="denied",
            allowed=False,
            reason="missing_bearer_token",
        )
        raise _unauthorized()

    scheme, _, supplied_token = authorization.partition(" ")

    if scheme.lower() != "bearer" or not supplied_token:
        _record_authorization_event(
            repository,
            required_role=required_role,
            decision="denied",
            allowed=False,
            reason="invalid_authorization_scheme",
        )
        raise _unauthorized()

    if hmac.compare_digest(supplied_token, required_token):
        # Middleware wykorzysta wyłącznie rolę. Nie zapisujemy tokenu ani
        # pełnej wartości nagłówka Authorization.
        request.state.authenticated_role = required_role
        request.state.audit_repository = repository
        return

    if other_token and hmac.compare_digest(supplied_token, other_token):
        _record_authorization_event(
            repository,
            required_role=required_role,
            decision="denied",
            allowed=False,
            reason="insufficient_role",
        )
        raise _forbidden()

    _record_authorization_event(
        repository,
        required_role=required_role,
        decision="denied",
        allowed=False,
        reason="invalid_token",
    )
    raise _unauthorized()


def require_owner(
    request: Request,
    authorization: str | None = Header(default=None),
    repository: Annotated[
        AuditRepository,
        Depends(get_audit_repository),
    ] = None,
) -> None:
    _require_role(
        request=request,
        authorization=authorization,
        repository=repository,
        required_role="owner",
        required_token_name="OWNER_API_TOKEN",
        other_token_name="WORKER_API_TOKEN",
    )


def require_worker(
    request: Request,
    authorization: str | None = Header(default=None),
    repository: Annotated[
        AuditRepository,
        Depends(get_audit_repository),
    ] = None,
) -> None:
    _require_role(
        request=request,
        authorization=authorization,
        repository=repository,
        required_role="worker",
        required_token_name="WORKER_API_TOKEN",
        other_token_name="OWNER_API_TOKEN",
    )
