"""Auth entrypoints — OIDC RBAC with internal-token fallback."""
from __future__ import annotations

from .auth_oidc import (
    AuthContext,
    require_internal_auth,
    require_security_admin,
    resolve_auth_context,
)

__all__ = [
    "AuthContext",
    "require_internal_auth",
    "require_security_admin",
    "resolve_auth_context",
]
