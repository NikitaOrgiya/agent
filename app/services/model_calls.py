"""Persist model-call metadata (cost / latency / tokens) for a future Cost Brain.

Never stores the prompt text or chain-of-thought.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.model import ModelResponse
from app.infra.models import ModelCall


class ModelCallService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def record(
        self, response: ModelResponse, *, task_id: UUID | None, purpose: str
    ) -> ModelCall:
        call = ModelCall(
            task_id=task_id,
            provider=response.provider or "unknown",
            model=response.model or "unknown",
            profile=str(response.profile) if response.profile else "unknown",
            purpose=purpose,
            prompt_version=response.prompt_version,
            status=str(response.status),
            latency_ms=response.latency_ms,
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
            cost_usd=response.cost_usd,
            error=response.error,
        )
        self.session.add(call)
        await self.session.flush()
        return call

    async def count_for_task(self, task_id: UUID) -> int:
        return (
            await self.session.execute(
                select(func.count()).select_from(ModelCall).where(ModelCall.task_id == task_id)
            )
        ).scalar_one()
