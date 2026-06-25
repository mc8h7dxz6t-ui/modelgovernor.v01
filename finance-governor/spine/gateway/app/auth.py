from __future__ import annotations

from fastapi import Header, HTTPException, status

from .config import get_settings


def require_governed_auth(x_internal_token: str | None = Header(default=None, alias="x-internal-token")) -> None:
    token = get_settings().fg_internal_token.strip()
    if not x_internal_token or x_internal_token != token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid internal token")
