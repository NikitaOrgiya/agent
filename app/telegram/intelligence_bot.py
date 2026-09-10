"""Intelligence Zone Telegram bot.

Direct owner <-> model conversation. Separate bot token, separate gateway. Does
NOT go through the Courier planner. Same hard security boundaries still apply
(no secrets / device / production / approval powers).
"""

from __future__ import annotations

import logging

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from app.config import Settings
from app.core.router import ModelRouter
from app.infra.db import session_scope
from app.services.intelligence import IntelligenceService
from app.telegram.formatting import chunk
from app.telegram.identity import is_owner, owner_key

logger = logging.getLogger("agentos.telegram.intelligence")

_ACCESS_DENIED = "Access denied."
_HELP = (
    "Agent OS Intelligence Zone — a direct conversation with a model.\n\n"
    "/models - list available model profiles\n"
    "/model - show the current profile\n"
    "/model <profile> - switch profile (economy|standard|strong|critical)\n"
    "/new - clear this conversation\n"
    "/help - this message"
)


def build_intelligence_dispatcher(
    settings: Settings, router: ModelRouter
) -> tuple[Bot, Dispatcher]:
    bot = Bot(token=settings.intelligence_telegram_bot_token.strip())
    dp = Dispatcher()

    def _owner(message: Message) -> str | None:
        user = message.from_user
        if user is None or not is_owner(settings, user.id):
            return None
        return owner_key(user.id)

    def _service(session):
        return IntelligenceService(session, router=router, settings=settings)

    @dp.message(CommandStart())
    async def _start(message: Message) -> None:
        await message.answer(_HELP if _owner(message) else _ACCESS_DENIED)

    @dp.message(Command("help"))
    async def _help(message: Message) -> None:
        await message.answer(_HELP if _owner(message) else _ACCESS_DENIED)

    @dp.message(Command("models"))
    async def _models(message: Message) -> None:
        if _owner(message) is None:
            await message.answer(_ACCESS_DENIED)
            return
        async with session_scope() as session:
            rows = await _service(session).list_models()
        lines = [
            f"- {r['provider']}/{r['model']} (profile: {r['profile']}) — "
            + ("available" if r["available"] else "unavailable")
            for r in rows
        ]
        await message.answer("Model profiles:\n" + "\n".join(lines))

    @dp.message(Command("model"))
    async def _model(message: Message) -> None:
        key = _owner(message)
        if key is None:
            await message.answer(_ACCESS_DENIED)
            return
        parts = (message.text or "").split(maxsplit=1)
        async with session_scope() as session:
            svc = _service(session)
            if len(parts) == 1:
                await message.answer(f"Current profile: {await svc.current_model(key)}")
                return
            _ok, msg = await svc.set_model(key, parts[1])
        await message.answer(msg)

    @dp.message(Command("new"))
    async def _new(message: Message) -> None:
        key = _owner(message)
        if key is None:
            await message.answer(_ACCESS_DENIED)
            return
        async with session_scope() as session:
            await _service(session).reset(key)
        await message.answer("Conversation cleared.")

    @dp.message(F.text)
    async def _text(message: Message) -> None:
        key = _owner(message)
        if key is None:
            await message.answer(_ACCESS_DENIED)
            return
        text = (message.text or "").strip()
        if not text:
            return
        try:
            async with session_scope() as session:
                reply = await _service(session).handle_message(key, text)
            body = reply.text
        except Exception:
            logger.exception("intelligence message handling failed")
            body = "Something went wrong. The failure was logged."
        for part in chunk(body):
            await message.answer(part)

    return bot, dp
