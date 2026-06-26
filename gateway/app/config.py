"""Gateway settings."""
from functools import lru_cache

from decimal import Decimal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    sidecar_url: str = "http://sidecar:8081"
    sidecar_internal_token: str = "dev-token"
    provider_mode: str = "mock"
    mock_dispatch_cost: Decimal = Decimal("1.000000")
    mock_output_tokens: int = 32
    provider_timeout_seconds: float = 30.0
    provider_max_output_tokens: int = 1024
    openai_compat_enabled: bool = True
    openai_compat_api_key: str | None = None
    openai_compat_default_user_id: str = "default-user"
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    vertex_project_id: str | None = None
    vertex_location: str = "us-central1"
    oidc_enabled: bool = False
    oidc_issuer_url: str | None = None
    oidc_audience: str | None = None
    oidc_jwks_url: str | None = None
    oidc_algorithms: str = "RS256"
    oidc_dispatch_roles: str = "dispatch,modelgovernor-dispatch"
    oidc_allow_internal_token_fallback: bool = False
    algofreeze_enabled: bool = False
    algofreeze_url: str = "http://localhost:8094"
    algofreeze_timeout_seconds: float = 2.0
    algofreeze_fail_closed: bool = True
    model_runtime_sha: str | None = None

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    def oidc_algorithms_list(self) -> list[str]:
        return [part.strip() for part in self.oidc_algorithms.split(",") if part.strip()]

    def oidc_dispatch_roles_list(self) -> list[str]:
        return [part.strip().lower() for part in self.oidc_dispatch_roles.split(",") if part.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
