from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    service_name: str = "modelgovernor-sidecar"
    service_port: int = 8081
    database_url: str = Field(
        default="postgresql://localhost:5432/modelgovernor",
        alias="DATABASE_URL",
    )
    redis_url: str = Field(default="redis://redis:6379/0", alias="REDIS_URL")
    sidecar_internal_tokens: str = Field(default="dev-internal-token", alias="SIDECAR_INTERNAL_TOKENS")
    default_reservation_ttl_seconds: int = Field(default=300, alias="RESERVATION_TTL_SECONDS")


settings = Settings()
