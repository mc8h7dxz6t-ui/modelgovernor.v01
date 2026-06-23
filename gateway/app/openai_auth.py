"""Authentication for OpenAI-compatible API clients (Bearer API key)."""
from __future__ import annotations

from dataclasses import dataclass

from fastapi import Header, HTTPException, status

from .auth_oidc import GatewayAuthContext, _parse_bearer, _validate_internal_token, _validate_oidc_jwt
from .config import get_settings


@dataclass(frozen=True)
class OpenAICompatAuth:
    subject: str
    method: str


async def require_openai_compat_auth(
    authorization: str | None = Header(default=None),
    x_internal_token: str | None = Header(default=None),
) -> OpenAICompatAuth:
    """Accept OpenAI-style Bearer key, internal token header, or OIDC JWT."""
    settings = get_settings()
    bearer = _parse_bearer(authorization)
    compat_key = settings.openai_compat_api_key or settings.sidecar_internal_token

    if bearer and bearer == compat_key:
        return OpenAICompatAuth(subject="openai-api-key", method="api_key")

    token_ctx = _validate_internal_token(x_internal_token)
    if token_ctx is not None:
        return OpenAICompatAuth(subject=token_ctx.subject, method="internal_token")

    if settings.oidc_enabled and bearer:
        ctx = _validate_oidc_jwt(bearer)
        if not ctx.can_dispatch():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="insufficient OIDC role for chat completions",
            )
        return OpenAICompatAuth(subject=ctx.subject, method="oidc")

    if not settings.oidc_enabled and bearer:
        try:
            ctx = _validate_oidc_jwt(bearer)
            if ctx.can_dispatch():
                return OpenAICompatAuth(subject=ctx.subject, method="oidc")
        except HTTPException:
            pass

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={
            "error": {
                "message": "Incorrect API key provided. Use Authorization: Bearer <gateway-key>.",
                "type": "invalid_request_error",
                "code": "invalid_api_key",
            }
        },
    )
