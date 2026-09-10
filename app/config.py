from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_DEV_ENVS = {"dev", "test", "local"}
_DEFAULT_DB_MARKERS = ("change-me", "changeme", "password@", ":postgres@")
_WILDCARD_HOSTS = {"0.0.0.0", "::", "[::]"}
_MIN_TOKEN_LEN = 16

_MODEL_PROVIDERS = {"none", "openai", "openai_compatible", "anthropic"}
_MODEL_PROFILES = {"economy", "standard", "strong", "critical"}


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

    # --- Telegram -----------------------------------------------------------
    # Numeric Telegram user ids allowed to use the bots. Deny by default.
    owner_telegram_ids: str = ""
    # Bot tokens: env only. Never logged, never stored, never in health/debug.
    courier_telegram_bot_token: str = ""
    intelligence_telegram_bot_token: str = ""

    # --- Model provider ---------------------------------------------------
    # "none" keeps the system honest: MODEL_UNAVAILABLE instead of a fake answer.
    model_provider: str = "none"
    model_name: str = ""
    model_base_url: str = ""  # only for provider "openai_compatible"
    openai_api_key: str = ""  # env only
    anthropic_api_key: str = ""  # env only
    default_model_profile: str = "standard"
    model_timeout_seconds: float = 60.0

    # --- Cost / context controls ---------------------------------------
    max_model_calls_per_task: int = 2
    context_max_messages: int = 12
    context_max_chars: int = 12_000

    # --- derived helpers ---------------------------------------------------
    @property
    def is_dev(self) -> bool:
        return self.agentos_env.strip().lower() in _DEV_ENVS

    @property
    def owner_telegram_id_set(self) -> frozenset[int]:
        ids: set[int] = set()
        for chunk in self.owner_telegram_ids.replace(";", ",").split(","):
            chunk = chunk.strip()
            if not chunk:
                continue
            try:
                ids.add(int(chunk))
            except ValueError:
                continue
        return frozenset(ids)

    @model_validator(mode="after")
    def _enforce_safe_defaults(self) -> "Settings":
        """Fail closed: refuse obviously unsafe configuration."""
        provider = self.model_provider.strip().lower()
        if provider not in _MODEL_PROVIDERS:
            raise ValueError(
                f"MODEL_PROVIDER must be one of {sorted(_MODEL_PROVIDERS)}, got {provider!r}."
            )
        if self.default_model_profile.strip().lower() not in _MODEL_PROFILES:
            raise ValueError(
                f"DEFAULT_MODEL_PROFILE must be one of {sorted(_MODEL_PROFILES)}."
            )
        if self.max_model_calls_per_task < 1:
            raise ValueError("MAX_MODEL_CALLS_PER_TASK must be >= 1.")

        # A configured bot with no owner allowlist would be open to the world.
        has_bot = bool(
            self.courier_telegram_bot_token.strip()
            or self.intelligence_telegram_bot_token.strip()
        )
        if has_bot and not self.owner_telegram_id_set:
            raise ValueError(
                "A Telegram bot token is set but OWNER_TELEGRAM_IDS is empty; "
                "refusing to run a bot with no owner allowlist (deny by default)."
            )

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
