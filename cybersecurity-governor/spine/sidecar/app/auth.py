"""Backward-compatible auth entrypoint — delegates to OIDC-aware RBAC."""
from __future__ import annotations

from .auth_oidc import (
    AuthContext,
    require_security_admin,
    require_internal_auth,
    resolve_auth_context,
)

__all__ = [
    "AuthContext",
    "require_security_admin",
    "require_internal_auth",
    "resolve_auth_context",
]
