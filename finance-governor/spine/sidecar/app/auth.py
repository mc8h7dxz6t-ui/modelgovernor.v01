from __future__ import annotations

from fastapi import Header, HTTPException, status

from .config import get_settings


def require_internal_auth(x_internal_token: str | None = Header(default=None, alias="x-internal-token")) -> None:
    tokens = {t.strip() for t in get_settings().fg_internal_tokens.split(",") if t.strip()}
    if not x_internal_token or x_internal_token not in tokens:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid internal token")
