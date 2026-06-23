"""Gateway-edge OIDC JWT validation — terminates corporate SSO before sidecar calls."""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Literal

from fastapi import Header, HTTPException, status

from .config import get_settings

logger = logging.getLogger(__name__)

AuthMethod = Literal["oidc", "internal_token"]


@dataclass(frozen=True)
class GatewayAuthContext:
    method: AuthMethod
    subject: str
    roles: frozenset[str]

    def can_dispatch(self) -> bool:
        settings = get_settings()
        if self.method == "internal_token":
            return True
        dispatch_roles = settings.oidc_dispatch_roles_list()
        if not dispatch_roles:
            return True
        normalized = {role.strip().lower() for role in dispatch_roles}
        return bool(self.roles.intersection(normalized))


def _parse_bearer(authorization: str | None) -> str | None:
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        return None
    return token.strip()


def _extract_roles(claims: dict[str, Any]) -> set[str]:
    roles: set[str] = set()
    realm_access = claims.get("realm_access")
    if isinstance(realm_access, dict):
        realm_roles = realm_access.get("roles")
        if isinstance(realm_roles, list):
            roles.update(str(role) for role in realm_roles)
    for claim_name in ("groups", "roles"):
        value = claims.get(claim_name)
        if isinstance(value, list):
            roles.update(str(role) for role in value)
    return {role.strip().lower() for role in roles if str(role).strip()}


@lru_cache(maxsize=1)
def _jwks_client(jwks_url: str):
    from jwt import PyJWKClient

    return PyJWKClient(jwks_url, cache_keys=True, lifespan=300)


def clear_jwks_client_cache() -> None:
    _jwks_client.cache_clear()


def _validate_oidc_jwt(token: str) -> GatewayAuthContext:
    settings = get_settings()
    if not settings.oidc_issuer_url:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="gateway OIDC issuer is not configured",
        )

    try:
        from jwt import InvalidTokenError, decode
    except ImportError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OIDC support requires PyJWT",
        ) from exc

    jwks_url = settings.oidc_jwks_url or (
        f"{settings.oidc_issuer_url.rstrip('/')}/protocol/openid-connect/certs"
    )
    signing_key = _jwks_client(jwks_url).get_signing_key_from_jwt(token)
    decode_kwargs: dict[str, Any] = {
        "algorithms": settings.oidc_algorithms_list(),
        "issuer": settings.oidc_issuer_url,
        "options": {"require": ["exp", "iss", "sub"]},
    }
    if settings.oidc_audience:
        decode_kwargs["audience"] = settings.oidc_audience

    try:
        claims = decode(token, signing_key.key, **decode_kwargs)
    except InvalidTokenError as exc:
        logger.info("gateway oidc jwt rejected: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid or expired OIDC token",
        ) from exc

    if int(claims.get("exp", 0)) <= int(time.time()):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="expired OIDC token",
        )

    subject = str(claims.get("sub") or claims.get("email") or "unknown")
    return GatewayAuthContext(
        method="oidc",
        subject=subject,
        roles=frozenset(_extract_roles(claims)),
    )


def _validate_internal_token(x_internal_token: str | None) -> GatewayAuthContext | None:
    settings = get_settings()
    if x_internal_token and x_internal_token == settings.sidecar_internal_token:
        return GatewayAuthContext(
            method="internal_token",
            subject="internal-token",
            roles=frozenset({"dispatch"}),
        )
    return None


async def require_dispatch_auth(
    authorization: str | None = Header(default=None),
    x_internal_token: str | None = Header(default=None),
) -> GatewayAuthContext:
    settings = get_settings()
    bearer = _parse_bearer(authorization)

    if settings.oidc_enabled:
        if bearer:
            ctx = _validate_oidc_jwt(bearer)
            if not ctx.can_dispatch():
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="insufficient OIDC role for governed dispatch",
                )
            return ctx
        if settings.oidc_allow_internal_token_fallback:
            token_ctx = _validate_internal_token(x_internal_token)
            if token_ctx is not None:
                return token_ctx
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="missing or invalid OIDC bearer token",
        )

    token_ctx = _validate_internal_token(x_internal_token)
    if token_ctx is not None:
        return token_ctx
    if bearer:
        ctx = _validate_oidc_jwt(bearer)
        if ctx.can_dispatch():
            return ctx
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="missing gateway credentials",
    )
