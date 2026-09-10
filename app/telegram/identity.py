"""Telegram owner identity.

Deny by default. Only numeric Telegram user ids in ``OWNER_TELEGRAM_IDS`` are
recognised. A username is never an identity. The audit reference is
``telegram:<user_id>`` and nothing more personal.
"""

from __future__ import annotations

from app.config import Settings


def is_owner(settings: Settings, telegram_user_id: int | None) -> bool:
    if telegram_user_id is None:
        return False
    return telegram_user_id in settings.owner_telegram_id_set


def owner_key(telegram_user_id: int) -> str:
    return f"telegram:{telegram_user_id}"
