from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    cg_sidecar_url: str = "http://localhost:8121"
    cg_internal_token: str = "dev-cg-spine-token-change-me"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
