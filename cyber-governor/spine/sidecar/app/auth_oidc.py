"""OAuth2/OIDC JWT validation for /internal/* RBAC."""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Literal

from fastapi import Header, HTTPException, status

from .config import get_settings

logger = logging.getLogger(__name__)

AuthMethod = Literal["internal_token", "oidc"]


@dataclass(frozen=True)
class AuthContext:
    method: AuthMethod
    subject: str
    roles: frozenset[str]

    def has_role(self, *role_names: str) -> bool:
        normalized = {role.strip().lower() for role in role_names if role.strip()}
        return bool(self.roles.intersection(normalized))

    def is_security_admin(self) -> bool:
        settings = get_settings()
        if self.method == "internal_token" and settings.oidc_internal_token_is_admin:
            return True
        return self.has_role(*settings.oidc_security_admin_roles_list())

    def is_viewer(self) -> bool:
        if self.is_security_admin():
            return True
        settings = get_settings()
        if self.method == "internal_token":
            return True
        viewer_roles = settings.oidc_viewer_roles_list()
        if not viewer_roles:
            return True
        return self.has_role(*viewer_roles)


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


def _validate_oidc_jwt(token: str) -> AuthContext:
    settings = get_settings()
    if not settings.oidc_issuer_url:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OIDC issuer is not configured",
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
        logger.info("oidc jwt rejected: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid or expired OIDC token",
        ) from exc
    if int(claims.get("exp", 0)) <= int(time.time()):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="expired OIDC token")
    subject = str(claims.get("sub") or claims.get("email") or "unknown")
    return AuthContext(method="oidc", subject=subject, roles=frozenset(_extract_roles(claims)))


def _validate_internal_token(x_internal_token: str | None) -> AuthContext | None:
    settings = get_settings()
    allowed = {t.strip() for t in settings.cg_internal_tokens.split(",") if t.strip()}
    if x_internal_token and x_internal_token in allowed:
        return AuthContext(
            method="internal_token",
            subject="internal-token",
            roles=frozenset({"security-admin", "viewer"}),
        )
    return None


async def resolve_auth_context(
    authorization: str | None = Header(default=None),
    x_internal_token: str | None = Header(default=None, alias="x-internal-token"),
) -> AuthContext:
    settings = get_settings()
    bearer = _parse_bearer(authorization)
    if settings.oidc_enabled:
        if bearer:
            ctx = _validate_oidc_jwt(bearer)
            if not ctx.is_viewer():
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="insufficient OIDC role for internal access",
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
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid internal token")


async def require_internal_auth(
    authorization: str | None = Header(default=None),
    x_internal_token: str | None = Header(default=None, alias="x-internal-token"),
) -> AuthContext:
    return await resolve_auth_context(authorization, x_internal_token)


async def require_security_admin(
    authorization: str | None = Header(default=None),
    x_internal_token: str | None = Header(default=None, alias="x-internal-token"),
) -> AuthContext:
    ctx = await resolve_auth_context(authorization, x_internal_token)
    if not ctx.is_security_admin():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="security admin role required",
        )
    return ctx
