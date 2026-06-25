from decimal import Decimal
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5433/financegovernor"
    redis_url: str = "redis://localhost:6380/0"
    fg_internal_tokens: str = "dev-fg-spine-token-change-me"
    commit_ttl_seconds: int = 300
    drift_absolute_tolerance: Decimal = Decimal("0.500000")
    drift_ratio_tolerance: Decimal = Decimal("0.050000")
    db_pool_size: int = 5
    db_max_overflow: int = 2
    db_pool_timeout_seconds: int = 5
    db_pool_recycle_seconds: int = 1800
    diagnostic_mode_blocks_writes: bool = True
    redis_connect_timeout_seconds: float = 0.5
    redis_socket_timeout_seconds: float = 0.5
    otel_service_name: str = "financegovernor-sidecar"

    oidc_enabled: bool = False
    oidc_issuer_url: str = ""
    oidc_jwks_url: str = ""
    oidc_audience: str = ""
    oidc_algorithms: str = "RS256"
    oidc_financial_admin_roles: str = "financial-admin,fg-admin"
    oidc_viewer_roles: str = "viewer,financial-admin,fg-admin"
    oidc_internal_token_is_admin: bool = True
    oidc_allow_internal_token_fallback: bool = True

    decision_anchor_s3_bucket: str = ""
    decision_anchor_s3_prefix: str = "finance-governor/decision-chain"
    decision_anchor_s3_region: str = ""
    decision_anchor_s3_endpoint_url: str = ""
    decision_anchor_s3_object_lock_enabled: bool = False
    decision_anchor_s3_object_lock_mode: str = "GOVERNANCE"
    decision_anchor_s3_retention_days: int = 365

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    def oidc_algorithms_list(self) -> list[str]:
        return [a.strip() for a in self.oidc_algorithms.split(",") if a.strip()]

    def oidc_financial_admin_roles_list(self) -> list[str]:
        return [r.strip().lower() for r in self.oidc_financial_admin_roles.split(",") if r.strip()]

    def oidc_viewer_roles_list(self) -> list[str]:
        return [r.strip().lower() for r in self.oidc_viewer_roles.split(",") if r.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
