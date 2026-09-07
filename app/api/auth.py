from __future__ import annotations

import hmac
import os

from fastapi import Header, HTTPException


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
    authorization: str | None,
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
        raise _unauthorized()

    scheme, _, supplied_token = authorization.partition(" ")

    if scheme.lower() != "bearer" or not supplied_token:
        raise _unauthorized()

    if hmac.compare_digest(supplied_token, required_token):
        return

    if other_token and hmac.compare_digest(supplied_token, other_token):
        raise _forbidden()

    raise _unauthorized()


def require_owner(
    authorization: str | None = Header(default=None),
) -> None:
    _require_role(
        authorization=authorization,
        required_token_name="OWNER_API_TOKEN",
        other_token_name="WORKER_API_TOKEN",
    )


def require_worker(
    authorization: str | None = Header(default=None),
) -> None:
    _require_role(
        authorization=authorization,
        required_token_name="WORKER_API_TOKEN",
        other_token_name="OWNER_API_TOKEN",
    )
