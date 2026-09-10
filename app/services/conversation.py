"""Minimal per-owner conversation state.

One row per (owner_key, kind). ``turns`` is a bounded JSON list. This is not
long-term memory -- it is just enough to continue a clarification or a short
Intelligence-Zone thread.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.context import Turn
from app.core.enums import ConversationKind
from app.infra.models import Conversation, utcnow

# Hard ceiling on stored turns regardless of context settings.
_MAX_STORED_TURNS = 40


class ConversationService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_or_create(self, owner_key: str, kind: ConversationKind) -> Conversation:
        row = (
            await self.session.execute(
                select(Conversation).where(
                    Conversation.owner_key == owner_key, Conversation.kind == kind
                )
            )
        ).scalar_one_or_none()
        if row is None:
            row = Conversation(owner_key=owner_key, kind=kind, turns=[])
            self.session.add(row)
            await self.session.flush()
        return row

    def turns(self, conv: Conversation) -> list[Turn]:
        return [Turn(role=t["role"], content=t["content"]) for t in (conv.turns or [])]

    async def append_turn(self, conv: Conversation, role: str, content: str) -> None:
        history = list(conv.turns or [])
        history.append({"role": role, "content": content})
        conv.turns = history[-_MAX_STORED_TURNS:]
        conv.updated_at = utcnow()
        await self.session.flush()

    async def set_active_task(self, conv: Conversation, task_id: UUID | None) -> None:
        conv.active_task_id = task_id
        conv.updated_at = utcnow()
        await self.session.flush()

    async def set_profile(self, conv: Conversation, profile: str | None) -> None:
        conv.model_profile = profile
        conv.updated_at = utcnow()
        await self.session.flush()

    async def clear(self, conv: Conversation) -> None:
        conv.turns = []
        conv.active_task_id = None
        conv.updated_at = utcnow()
        await self.session.flush()
