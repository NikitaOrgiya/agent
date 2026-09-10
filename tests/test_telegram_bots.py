"""Dispatcher wiring only -- no real bot token, no network."""

import asyncio

from app.config import Settings
from app.core.router import ModelRouter
from app.telegram.courier_bot import build_courier_dispatcher
from app.telegram.intelligence_bot import build_intelligence_dispatcher

_FAKE_TOKEN = "123456789:AABBCCDDEEFFGGHHIIJJKKLLMMNNOOPPQQRR"


def _settings() -> Settings:
    return Settings(
        _env_file=None,
        agentos_control_token="x" * 20,
        owner_telegram_ids="42",
        courier_telegram_bot_token=_FAKE_TOKEN,
        intelligence_telegram_bot_token=_FAKE_TOKEN,
    )


def test_courier_dispatcher_registers_expected_handlers():
    bot, dp = build_courier_dispatcher(_settings(), ModelRouter())
    try:
        assert len(dp.message.handlers) == 4  # start, help, status, text
    finally:
        asyncio.run(bot.session.close())


def test_intelligence_dispatcher_registers_expected_handlers():
    bot, dp = build_intelligence_dispatcher(_settings(), ModelRouter())
    try:
        assert len(dp.message.handlers) == 6  # start, help, models, model, new, text
    finally:
        asyncio.run(bot.session.close())
