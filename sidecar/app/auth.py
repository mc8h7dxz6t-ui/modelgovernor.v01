from fastapi import Header, HTTPException, status

from .config import settings


def require_internal_auth(authorization: str | None = Header(default=None)) -> None:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")

    token = authorization.split(" ", 1)[1].strip()
    allowed_tokens = {value.strip() for value in settings.sidecar_internal_tokens.split(",") if value.strip()}
    if token not in allowed_tokens:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid internal token")
