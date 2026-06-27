from functools import lru_cache
from decimal import Decimal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    redis_url: str
    sidecar_internal_tokens: str
    reserve_ttl_seconds: int = 300
    default_trace_cap_amount: Decimal = Decimal("25.000000")
    drift_absolute_tolerance: Decimal = Decimal("0.500000")
    drift_ratio_tolerance: Decimal = Decimal("0.050000")
    default_run_budget_amount: Decimal = Decimal("25.000000")
    default_session_budget_amount: Decimal = Decimal("250.000000")
    default_user_budget_amount: Decimal = Decimal("500.000000")
    default_tenant_budget_amount: Decimal = Decimal("5000.000000")
    manual_approval_cost_threshold: Decimal = Decimal("2.000000")
    max_loop_repeats: int = 3
    db_pool_size: int = 5
    db_max_overflow: int = 2
    db_pool_timeout_seconds: int = 5
    db_pool_recycle_seconds: int = 1800
    app_env: str = "development"
    guardrails_enabled: bool = True
    rate_limit_per_minute: int = 120
    max_trace_depth: int = 50
    max_user_inflight: int = 10
    fallback_max_trace_depth: int = 50
    fallback_max_user_inflight: int = 5
    fallback_rate_limit_per_minute: int = 60
    fallback_global_tokens_per_second: float = 20.0
    fallback_token_bucket_capacity: float = 40.0
    diagnostic_mode_blocks_writes: bool = True
    redis_connect_timeout_seconds: float = 0.5
    redis_socket_timeout_seconds: float = 0.5
    circuit_breaker_enabled: bool = True
    circuit_breaker_failure_threshold: int = 5
    circuit_breaker_window_seconds: int = 60
    circuit_breaker_open_seconds: int = 30
    otel_service_name: str = "modelgovernor-sidecar"
    otel_exporter_endpoint: str | None = None
    oidc_enabled: bool = False
    oidc_issuer_url: str | None = None
    oidc_audience: str | None = None
    oidc_jwks_url: str | None = None
    oidc_algorithms: str = "RS256"
    oidc_allow_internal_token_fallback: bool = True
    oidc_internal_token_is_admin: bool = True
    oidc_viewer_roles: str = "viewer,modelgovernor-viewer"
    oidc_financial_admin_roles: str = "financial-admin,modelgovernor-financial-admin"
    oidc_tenant_claim: str = "tenant_id"
    internal_token_default_tenant: str = "default-tenant"
    rls_enabled: bool = False
    enforcement_mode: str = "SHADOW"
    enforcement_latency_slo_ms: float = 50.0
    enforcement_evaluator_timeout_ms: float = 45.0
    ledger_anchor_webhook_url: str | None = None
    ledger_anchor_s3_bucket: str | None = None
    ledger_anchor_s3_prefix: str = "ledger-anchors"
    ledger_anchor_s3_region: str | None = None
    ledger_anchor_s3_endpoint_url: str | None = None
    ledger_anchor_s3_object_lock_enabled: bool = False
    ledger_anchor_s3_object_lock_mode: str = "GOVERNANCE"
    ledger_anchor_s3_retention_days: int = 3650

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    def oidc_algorithms_list(self) -> list[str]:
        return [part.strip() for part in self.oidc_algorithms.split(",") if part.strip()]

    def oidc_viewer_roles_list(self) -> list[str]:
        return [part.strip().lower() for part in self.oidc_viewer_roles.split(",") if part.strip()]

    def oidc_financial_admin_roles_list(self) -> list[str]:
        return [
            part.strip().lower()
            for part in self.oidc_financial_admin_roles.split(",")
            if part.strip()
        ]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
