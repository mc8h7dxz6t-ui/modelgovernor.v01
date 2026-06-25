from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5433/financegovernor"
    redis_url: str = "redis://localhost:6380/0"
    reconciler_interval_seconds: int = 5
    reconciler_health_port: int = 8092
    fg_internal_tokens: str = "dev-fg-spine-token-change-me"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
