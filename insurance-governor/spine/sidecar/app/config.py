from decimal import Decimal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5434/insurancegovernor"
    redis_url: str = "redis://localhost:6381/0"
    ig_internal_tokens: str = "dev-ig-spine-token-change-me"
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
    otel_service_name: str = "insurancegovernor-sidecar"
    guardrails_enabled: bool = True
    rate_limit_per_minute: int = 120
    max_claim_depth: int = 50
    max_account_inflight: int = 10
    circuit_breaker_enabled: bool = True
    circuit_breaker_failure_threshold: int = 5
    circuit_breaker_window_seconds: int = 60
    circuit_breaker_open_seconds: int = 30
    fallback_max_claim_depth: int = 50
    fallback_max_account_inflight: int = 5
    fallback_rate_limit_per_minute: int = 60
    fallback_global_tokens_per_second: float = 20.0
    fallback_token_bucket_capacity: float = 40.0
    oidc_enabled: bool = False
    oidc_issuer_url: str | None = None
    oidc_audience: str | None = None
    oidc_jwks_url: str | None = None
    oidc_algorithms: str = "RS256"
    oidc_allow_internal_token_fallback: bool = True
    oidc_internal_token_is_admin: bool = True
    oidc_viewer_roles: str = "viewer,insurancegovernor-viewer"
    oidc_claims_admin_roles: str = "claims-admin,insurancegovernor-claims-admin"
    claim_anchor_webhook_url: str | None = None
    claim_anchor_s3_bucket: str | None = None
    claim_anchor_s3_prefix: str = "claim-anchors"
    claim_anchor_s3_region: str | None = None
    claim_anchor_s3_endpoint_url: str | None = None
    claim_anchor_s3_object_lock_enabled: bool = False
    claim_anchor_s3_object_lock_mode: str = "GOVERNANCE"
    claim_anchor_s3_retention_days: int = 3650
    platform_registry_enforce: bool = True

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    def oidc_algorithms_list(self) -> list[str]:
        return [p.strip() for p in self.oidc_algorithms.split(",") if p.strip()]

    def oidc_viewer_roles_list(self) -> list[str]:
        return [p.strip().lower() for p in self.oidc_viewer_roles.split(",") if p.strip()]

    def oidc_claims_admin_roles_list(self) -> list[str]:
        return [p.strip().lower() for p in self.oidc_claims_admin_roles.split(",") if p.strip()]


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def override_settings(settings: Settings) -> None:
    global _settings
    _settings = settings
