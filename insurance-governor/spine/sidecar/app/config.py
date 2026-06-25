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

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def override_settings(settings: Settings) -> None:
    global _settings
    _settings = settings
