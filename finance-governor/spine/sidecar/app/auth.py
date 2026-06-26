"""Internal auth — delegates to Finance Governor OIDC RBAC layer."""
from .auth_oidc import AuthContext, require_financial_admin, require_internal_auth

__all__ = ["AuthContext", "require_financial_admin", "require_internal_auth"]
