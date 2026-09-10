from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_DEV_ENVS = {"dev", "test", "local"}
_DEFAULT_DB_MARKERS = ("change-me", "changeme", "password@", ":postgres@")
_WILDCARD_HOSTS = {"0.0.0.0", "::", "[::]"}
_MIN_TOKEN_LEN = 16


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    agentos_env: str = "dev"
    # Bind loopback by default; opening to other interfaces must be deliberate.
    agentos_host: str = "127.0.0.1"
    agentos_port: int = 8080
    database_url: str = "postgresql+asyncpg://agentos:change-me@postgres:5432/agentos"
    redis_url: str = "redis://redis:6379/0"

    # Single Control Plane token for /v1/* (env only, never committed). This is
    # NOT a master secret and NOT the future identity/capability system -- it
    # only keeps the local Control Plane from being an open API.
    agentos_control_token: str = ""

    owner_telegram_ids: str = ""

    @property
    def is_dev(self) -> bool:
        return self.agentos_env.strip().lower() in _DEV_ENVS

    @model_validator(mode="after")
    def _enforce_safe_defaults(self) -> "Settings":
        """Fail closed: refuse obviously unsafe configuration outside dev."""
        if self.is_dev:
            return self
        if any(marker in self.database_url for marker in _DEFAULT_DB_MARKERS):
            raise ValueError(
                "Refusing to start: default/placeholder database credentials "
                f"in non-dev environment '{self.agentos_env}'."
            )
        if self.agentos_host.strip() in _WILDCARD_HOSTS:
            raise ValueError(
                "Refusing to bind all interfaces in non-dev environment; set "
                "AGENTOS_HOST to an explicit address."
            )
        if len(self.agentos_control_token.strip()) < _MIN_TOKEN_LEN:
            raise ValueError(
                "Refusing to start: AGENTOS_CONTROL_TOKEN must be set to at "
                f"least {_MIN_TOKEN_LEN} characters in a non-dev environment."
            )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
