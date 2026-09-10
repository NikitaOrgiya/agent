"""Evidence linkage for model answers.

Sprint 2 has no web research. A plain LLM answer with no external source is
recorded as ``INFERRED`` -- never ``OBSERVED``. When a real tool/source backs an
answer in a later sprint, that call sites will pass ``SUPPORTED`` / ``OBSERVED``.

Stores a short claim and provider metadata only -- no chain-of-thought.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import TruthStatus
from app.infra.models import Evidence

_CLAIM_MAX = 1000


class EvidenceService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def record_model_answer(
        self,
        *,
        task_id: UUID,
        answer: str,
        provider: str | None,
        model: str | None,
        profile: str | None,
        prompt_version: str | None,
        truth_status: TruthStatus = TruthStatus.INFERRED,
    ) -> Evidence:
        claim = answer.strip()
        if len(claim) > _CLAIM_MAX:
            claim = claim[:_CLAIM_MAX] + "..."
        ev = Evidence(
            task_id=task_id,
            claim=claim,
            truth_status=truth_status,
            source_type="model",
            source_uri=None,
            reliability=0.4,
            extra={
                "provider": provider,
                "model": model,
                "profile": profile,
                "prompt_version": prompt_version,
            },
        )
        self.session.add(ev)
        await self.session.flush()
        return ev
