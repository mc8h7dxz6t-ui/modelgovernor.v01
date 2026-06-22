from fastapi import Header, HTTPException, status

from app.config import get_settings


async def require_internal_auth(x_internal_token: str | None = Header(default=None)) -> None:
    settings = get_settings()
    allowed_tokens = {token.strip() for token in settings.sidecar_internal_tokens.split(",") if token.strip()}

    if not x_internal_token or x_internal_token not in allowed_tokens:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="missing or invalid internal token",
        )
