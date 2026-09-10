from app.config import Settings
from app.telegram.identity import is_owner, owner_key


def _settings(ids: str) -> Settings:
    return Settings(_env_file=None, agentos_control_token="x" * 20, owner_telegram_ids=ids)


def test_deny_by_default_empty_allowlist():
    s = _settings("")
    assert is_owner(s, 123) is False
    assert is_owner(s, None) is False


def test_allowlisted_numeric_id_is_owner():
    s = _settings("111, 222 ; 333")
    assert is_owner(s, 222) is True
    assert is_owner(s, 999) is False


def test_owner_key_is_numeric_reference():
    assert owner_key(4242) == "telegram:4242"


def test_bot_token_without_owner_ids_is_rejected():
    import pytest

    with pytest.raises(ValueError):
        Settings(
            _env_file=None,
            agentos_control_token="x" * 20,
            courier_telegram_bot_token="fake-bot-token",
            owner_telegram_ids="",
        )
