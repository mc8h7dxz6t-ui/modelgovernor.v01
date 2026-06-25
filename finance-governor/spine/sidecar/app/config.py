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
    ledger_anchor_s3_bucket: str | None = None
    ledger_anchor_s3_prefix: str = "fg-decision-chain"
    ledger_anchor_s3_region: str | None = None
    ledger_anchor_s3_endpoint_url: str | None = None
    ledger_anchor_s3_object_lock_enabled: bool = False
    ledger_anchor_s3_object_lock_mode: str = "COMPLIANCE"
    ledger_anchor_s3_retention_days: int = 365

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
