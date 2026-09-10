from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_DEV_ENVS = {"dev", "test", "local"}
_DEFAULT_DB_MARKERS = ("change-me", "changeme", "password@", ":postgres@")
_WILDCARD_HOSTS = {"0.0.0.0", "::", "[::]"}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    agentos_env: str = "dev"
    # Bind loopback by default; opening to other interfaces must be deliberate.
    agentos_host: str = "127.0.0.1"
    agentos_port: int = 8080
    database_url: str = "postgresql+asyncpg://agentos:change-me@postgres:5432/agentos"
    redis_url: str = "redis://redis:6379/0"
    owner_telegram_ids: str = ""

    @model_validator(mode="after")
    def _enforce_safe_defaults(self) -> "Settings":
        """Fail closed: refuse obviously unsafe configuration outside dev."""
        if self.agentos_env.strip().lower() in _DEV_ENVS:
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
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
