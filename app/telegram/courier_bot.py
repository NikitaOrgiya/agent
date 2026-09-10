"""Courier Telegram bot.

Thin adapter: authenticate the Telegram user as owner, then hand off to
``CourierService``. No domain logic here. Deterministic commands (/start,
/help, /status) never call a model.
"""

from __future__ import annotations

import logging

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message
from sqlalchemy import desc, select

from app.config import Settings
from app.core.router import ModelRouter
from app.infra.db import session_scope
from app.infra.models import Task
from app.services.courier import CourierService
from app.telegram.formatting import chunk
from app.telegram.identity import is_owner, owner_key

logger = logging.getLogger("agentos.telegram.courier")

_ACCESS_DENIED = "Access denied."
_HELP = (
    "Agent OS Courier.\n\n"
    "Send a plain message describing what you need "
    "(\"research…\", \"explain…\", \"draft…\").\n\n"
    "/status - your most recent task\n"
    "/help - this message"
)


def build_courier_dispatcher(settings: Settings, router: ModelRouter) -> tuple[Bot, Dispatcher]:
    bot = Bot(token=settings.courier_telegram_bot_token.strip())
    dp = Dispatcher()

    def _owner(message: Message) -> str | None:
        user = message.from_user
        if user is None or not is_owner(settings, user.id):
            return None
        return owner_key(user.id)

    @dp.message(CommandStart())
    async def _start(message: Message) -> None:
        if _owner(message) is None:
            await message.answer(_ACCESS_DENIED)
            return
        await message.answer(_HELP)

    @dp.message(Command("help"))
    async def _help(message: Message) -> None:
        if _owner(message) is None:
            await message.answer(_ACCESS_DENIED)
            return
        await message.answer(_HELP)

    @dp.message(Command("status"))
    async def _status(message: Message) -> None:
        key = _owner(message)
        if key is None:
            await message.answer(_ACCESS_DENIED)
            return
        async with session_scope() as session:
            row = (
                await session.execute(
                    select(Task)
                    .where(Task.caller == key)
                    .order_by(desc(Task.created_at))
                    .limit(1)
                )
            ).scalar_one_or_none()
        if row is None:
            await message.answer("No tasks yet.")
            return
        line = f"Task {str(row.id)[:8]} — {row.status}"
        if row.status == "clarifying" and row.pending_question:
            line += f"\nWaiting on: {row.pending_question}"
        elif row.error:
            line += f"\nError: {row.error}"
        await message.answer(line)

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
                reply = await CourierService(
                    session, router=router, settings=settings
                ).handle_owner_message(key, text)
            body = reply.text
        except Exception:
            logger.exception("courier message handling failed")
            body = "Something went wrong handling that. The failure was logged."
        for part in chunk(body):
            await message.answer(part)

    return bot, dp
