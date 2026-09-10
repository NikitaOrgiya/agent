"""Configuration must fail closed: unsafe defaults are rejected outside dev."""

import pytest

from app.config import Settings

_SAFE_DB = "postgresql+asyncpg://agentos:s3cure-and-long@db:5432/agentos"


def _settings(**kwargs) -> Settings:
    base = dict(_env_file=None, database_url=_SAFE_DB, agentos_host="127.0.0.1")
    base.update(kwargs)
    return Settings(**base)


def test_default_host_is_loopback():
    assert _settings().agentos_host == "127.0.0.1"


def test_dev_allows_placeholder_password():
    s = _settings(agentos_env="dev", database_url="postgresql+asyncpg://agentos:change-me@db:5432/agentos")
    assert "change-me" in s.database_url  # tolerated only because env is dev


def test_prod_rejects_placeholder_password():
    with pytest.raises(ValueError):
        _settings(
            agentos_env="production",
            database_url="postgresql+asyncpg://agentos:change-me@db:5432/agentos",
        )


def test_prod_rejects_wildcard_bind():
    with pytest.raises(ValueError):
        _settings(agentos_env="production", agentos_host="0.0.0.0")


def test_prod_accepts_explicit_safe_config():
    s = _settings(agentos_env="production", agentos_host="10.0.0.5")
    assert s.agentos_host == "10.0.0.5"
