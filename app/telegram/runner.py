"""Telegram gateway entrypoint (long polling).

    python -m app.telegram.runner

Runs whichever bots have a token configured (Courier and/or Intelligence).
Long polling means no inbound port and no public webhook. Bot tokens are read
from env only and are never logged.
"""

from __future__ import annotations

import asyncio
import logging

from app.adapters import build_router
from app.config import get_settings
from app.telegram.courier_bot import build_courier_dispatcher
from app.telegram.intelligence_bot import build_intelligence_dispatcher

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("agentos.telegram.runner")


async def main() -> None:
    settings = get_settings()
    router = build_router(settings)
    logger.info(
        "model router ready (provider=%s, available=%s)",
        settings.model_provider,
        router.has_available_model(),
    )

    jobs = []
    bots = []
    if settings.courier_telegram_bot_token.strip():
        bot, dp = build_courier_dispatcher(settings, router)
        bots.append(bot)
        jobs.append(dp.start_polling(bot, handle_signals=False))
        logger.info("courier bot: polling")
    if settings.intelligence_telegram_bot_token.strip():
        bot, dp = build_intelligence_dispatcher(settings, router)
        bots.append(bot)
        jobs.append(dp.start_polling(bot, handle_signals=False))
        logger.info("intelligence bot: polling")

    if not jobs:
        logger.error("no Telegram bot tokens configured; nothing to run")
        return

    try:
        await asyncio.gather(*jobs)
    finally:
        for bot in bots:
            await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
